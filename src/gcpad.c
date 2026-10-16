/* Super Mario Galaxy 2: GameCube controller (port 1) -> Classic Controller bridge.
 *
 * Three hooks, one routine each (hooks.S holds the register-saving entry stubs):
 *
 *   FRAME   the game's per-frame controller update (the loop that calls KPADRead
 *           for every channel).  Drives the Serial Interface's auto-polling --
 *           the game links SI but not PAD, so nothing else ever polls the pads --
 *           and, while no Wii Remote owns channel 0, fires the connect and
 *           extension callbacks WPAD would have fired, so the game's controller
 *           manager marks player 1 as present with a Classic Controller attached.
 *   SAMPLE  KPADiRead's "any samples queued?" check.  Writes the pad's state as
 *           Classic Controller samples into KPAD's ring buffer.
 *   PROBE   WPADProbe.  Reports a Classic Controller on channel 0 while a pad
 *           answers, so KPADiRead does not bail out with "no controller".
 *
 * From there the Classic Controller feature (cc_code.s) maps the sample onto
 * the Wii Remote + Nunchuk controls exactly as for a real Classic Controller.
 *
 * Addresses come in as -D macros (see gen_gc.py), resolved per release.
 */
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned short u16;
typedef signed short s16;
typedef unsigned char u8;

#define R32(a) (*(volatile u32 *)(a))
#define SI_OUT0   (0xCD006400u)         /* the Wii's SI, not the GameCube's 0xCC006400 */
#define SI_IN0H   (0xCD006404u)
#define SI_IN0L   (0xCD006408u)
#define SI_POLL   (0xCD006430u)
#define SI_COMCSR (0xCD006434u)
#define SI_SR     (0xCD006438u)

/* WPAD per-channel control block */
#define WPAD_EXT_CB     0x8E4           /* extension callback (the game's own) */
#define WPAD_CONNECT_CB 0x8E8           /* connect callback (KPAD's, which calls the game's) */
#define WPAD_STATUS     0x900           /* -1: no Wii Remote */
#define WPAD_DEV_TYPE   0x905           /* extension type */

struct st {
    u32 probe_tb;       /* last SIGetType */
    u32 busy_tb;        /* when si:: was first seen busy (0 = idle) */
    u32 prev_btn;       /* the Classic Controller buttons of the previous frame */
    u32 last_h, last_l; /* the last pad response the sample hook used */
    u32 n_frame;        /* hook counters, read by the Dolphin test harness */
    u32 n_sample;
    u32 n_sample_ok;
    u32 n_probe;
    u8 norep;           /* consecutive frames with NOREP on port 1 */
    u8 ours;            /* the last KPAD sample on channel 0 was ours */
    u8 connected;       /* we told the game a controller is on channel 0 */
};
#define ST ((volatile struct st *)STATE)

static inline u32 tb(void)
{
    u32 t;
    __asm__ volatile("mftb %0" : "=r"(t));
    return t;
}

/* a valid, error-free standard-pad response on port 1 */
static inline int gc_in(u32 *h, u32 *l)
{
#ifdef DEBUG_FEED
    /* test builds: the response is written to STATE+0x38/0x3C by a debugger */
    if (!R32(STATE + 0x38))
        return 0;
    *h = R32(STATE + 0x38);
    *l = R32(STATE + 0x3C);
    return 1;
#endif
    u32 v = R32(SI_IN0H);
    if ((v & 0x80000000u) || !(v & 0x00800000u))   /* ERRSTAT, or no PAD_USE_ORIGIN bit */
        return 0;
    *h = v;
    *l = R32(SI_IN0L);
    return 1;
}

#if defined(HOOK_FRAME)
static inline int is_pad(u32 type)
{
    return !(type & 0x80) && (type & 0x18000000u) == 0x08000000u;
}

/* What PADRead would do, for port 1 only. */
static void gc_poll(void)
{
    volatile u32 *types = (volatile u32 *)SI_TYPES;
    u32 sisr, mask, poll;
    s32 busy;

    /* probe the port until a standard pad answers, at most every 0.25 s:
     * probing every frame collides with the pad's own polling on hardware */
    if (!is_pad(types[0])) {
        u32 now = tb();
        if (now - ST->probe_tb >= 15187500u) {
            ST->probe_tb = now;
            ((u32 (*)(s32))FN_SIGETTYPE)(0);
        }
    }

    /* an unplugged pad latches NOREP, which si:: never reads (no PAD library);
     * copy a persistent one into the type cache so SIGetType probes again */
    sisr = R32(SI_SR);
    if (sisr & 0x08000000u) {
        if (ST->norep < 10)
            ST->norep++;
        else
            types[0] = 8;
    } else {
        ST->norep = 0;
    }

    /* poll command, then acknowledge the error bits and latch OUTBUF (WR):
     * without WR the hardware keeps whatever command was latched at boot */
    R32(SI_OUT0) = 0x00400300u;
    R32(SI_SR) = (sisr & 0x0F0F0F0Fu) | 0x80000000u;

    /* enable polling + copy-on-vblank for port 1 once a pad is confirmed
     * (a port can only be probed while it is not being polled) */
    mask = is_pad(types[0]) ? 0x88u : 0;
    poll = R32(SI_POLL) & ~0xFFu;
    if (!(poll & 0xFF00u))
        poll |= 0x0100u;                /* Y: at least one poll per frame */
    R32(SI_POLL) = poll | mask;
    /* si:: rewrites SIPOLL from its shadow copy on every retrace */
    R32(SI_SHADOW) = (R32(SI_SHADOW) & ~0xFFu) | mask;

    /* a pad unplugged mid-transfer can wedge si::'s busy flag forever;
     * force it idle after a second */
    busy = (s32)R32(SI_BUSY);
    if (busy == -1) {
        ST->busy_tb = 0;
    } else {
        u32 now = tb();
        if (ST->busy_tb == 0) {
            ST->busy_tb = now | 1;
        } else if (now - ST->busy_tb >= 60750000u) {
            u32 lvl = ((u32 (*)(void))FN_OSDISABLE)();
            R32(SI_BUSY) = (u32)-1;
            R32(SI_COMCSR) = 0x80000000u;
            ((void (*)(u32))FN_OSRESTORE)(lvl);
            ST->busy_tb = 0;
        }
    }
}

/* The game only treats a player as present once WPAD's connect callback has
 * fired for its channel, and its "attachment ok" flag comes from the extension
 * callback.  With no Wii Remote neither ever happens, so do it here when a pad
 * appears on port 1 (and the reverse when it goes), as long as no real Wii
 * Remote owns channel 0. */
void gc_frame(void)
{
    u32 h, l;
    u8 *blk;
    s32 status;
    void (*cb)(s32, s32);

    ST->n_frame++;
    gc_poll();
    blk = *(u8 **)WPAD_TBL;
    if (!blk)
        return;
    status = *(s32 *)(blk + WPAD_STATUS);
#ifdef NO_CALLBACKS
    return;
#endif
    if (gc_in(&h, &l)) {
        if (!ST->connected && status == -1) {
            ST->connected = 1;
            cb = *(void (**)(s32, s32))(blk + WPAD_CONNECT_CB);
            if (cb)
                cb(0, 0);
            cb = *(void (**)(s32, s32))(blk + WPAD_EXT_CB);
            if (cb)
                cb(0, 2);               /* Classic Controller attached */
        }
    } else if (ST->connected) {
        ST->connected = 0;
        if (status == -1) {
            cb = *(void (**)(s32, s32))(blk + WPAD_CONNECT_CB);
            if (cb)
                cb(0, -1);
        }
    }
}
#endif

#if defined(HOOK_SAMPLE)
/* Classic Controller buttons as WPAD reports them */
#define CL_UP    0x0001
#define CL_LEFT  0x0002
#define CL_ZR    0x0004
#define CL_X     0x0008
#define CL_A     0x0010
#define CL_Y     0x0020
#define CL_B     0x0040
#define CL_ZL    0x0080
#define CL_R     0x0200
#define CL_PLUS  0x0400
#define CL_HOME  0x0800
#define CL_MINUS 0x1000
#define CL_L     0x2000
#define CL_DOWN  0x4000
#define CL_RIGHT 0x8000

/* GameCube pad response, first word */
#define GC_LEFT  0x00010000u
#define GC_RIGHT 0x00020000u
#define GC_DOWN  0x00040000u
#define GC_UP    0x00080000u
#define GC_Z     0x00100000u
#define GC_R     0x00200000u
#define GC_L     0x00400000u
#define GC_A     0x01000000u
#define GC_B     0x02000000u
#define GC_X     0x04000000u
#define GC_Y     0x08000000u
#define GC_START 0x10000000u

#define SMP      0x42           /* bytes per KPAD ring sample */
#define TRIGGER  0xA0           /* analog L/R past this counts as a press */

/* pad stick byte (centre 128, about +-100) -> Classic Controller stick;
 * KPAD maps 60..308 onto 0..1, so a pad's deadzone is about +-20 */
static inline s16 stick(u32 raw)
{
    s32 v = ((s32)(raw & 0xFF) - 128) * 3;
    if (v > 308)
        v = 308;
    if (v < -308)
        v = -308;
    return (s16)v;
}

/* GameCube -> Classic Controller, so that the Classic Controller feature gives:
 * A jump, B back/dive, X/Y spin, Z crouch, L reset camera, R shoot star bits,
 * Start pause, D-pad camera, Start+Z the HOME Menu. */
static __attribute__((noinline)) u32 cc_buttons(u32 h, u32 l)
{
    u32 b = 0;

    if ((l >> 8 & 0xFF) >= TRIGGER) h |= GC_L;
    if ((l & 0xFF) >= TRIGGER) h |= GC_R;

    if (h & GC_A) b |= CL_A;
    if (h & GC_B) b |= CL_B;
    if (h & (GC_X | GC_Y)) b |= CL_X;
    if (h & GC_Z) b |= CL_ZL;
    if (h & GC_L) b |= CL_L;
    if (h & GC_R) b |= CL_R;
    if (h & GC_START) b |= CL_PLUS;
    if (h & GC_UP) b |= CL_UP;
    if (h & GC_DOWN) b |= CL_DOWN;
    if (h & GC_LEFT) b |= CL_LEFT;
    if (h & GC_RIGHT) b |= CL_RIGHT;
    if ((h & (GC_START | GC_Z)) == (GC_START | GC_Z))
        b = (b & ~(CL_PLUS | CL_ZL)) | CL_HOME;
    return b;
}

static __attribute__((noinline)) void fill_cc(u8 *s, u32 h, u32 l, u32 b)
{
    *(u16 *)(s + 0x2A) = (u16)b;
    *(s16 *)(s + 0x2C) = stick(h >> 8);      /* control stick x */
    *(s16 *)(s + 0x2E) = stick(h);           /* control stick y */
    *(s16 *)(s + 0x30) = stick(l >> 24);     /* C-stick x */
    *(s16 *)(s + 0x32) = stick(l >> 16);     /* C-stick y */
    s[0x34] = (b & CL_L) ? 0xF8 : 0;         /* analog L / R follow the buttons */
    s[0x35] = (b & CL_R) ? 0xF8 : 0;
    s[0x28] = 2;                             /* extension: Classic Controller */
    s[0x29] = 0;                             /* no extension error */
    s[0x40] = 8;                             /* data format: classic + accel + pointer */
}

/* ring slot `i` (16 entries in the block, then an optional extension buffer) */
static __attribute__((noinline)) u8 *slot(u8 *k, u32 i)
{
    if (i >= 0x10)
        return *(u8 **)(k + 0x5A0) + (i - 0x10) * SMP;
    return k + 0x180 + i * SMP;
}

static __attribute__((noinline)) void put_sample(u8 *k, u32 idx, u32 h, u32 l, u32 b)
{
    u8 *p = slot(k, idx);
    u32 i;

    for (i = 0; i < SMP; i++)
        p[i] = 0;
    fill_cc(p, h, l, b);
}

/* KPADiRead(chan) found its ring empty, or not: k = KPAD block of chan.
 * Two samples per frame, as a Wii Remote delivers: the older carries the
 * previous frame's buttons, so press and release edges land in the newest. */
void gc_sample(u8 *k, u32 chan)
{
    u32 h, l, b, i, idx, cnt, n;

    ST->n_sample++;
#ifdef NO_SAMPLE
    return;
#endif
    if (chan || !gc_in(&h, &l))
        return;
    ST->n_sample_ok++;
    ST->last_h = h;
    ST->last_l = l;

    b = cc_buttons(h, l);
    n = 0x10 + *(u32 *)(k + 0x5A4);          /* ring size */
    idx = k[0x17A];                          /* next slot to write */
    if (idx >= n)
        idx = 0;
    cnt = k[0x17B];
    if (cnt == 0) {
        /* nothing queued: no Wii Remote (extension 0xFD), a bare one that has
         * not delivered yet, or our own sample showing through */
        u8 dev = k[0x5C];
        if (!(dev == 0 || dev == 0xFD || ST->ours))
            return;
        put_sample(k, idx, h, l, ST->prev_btn);
        put_sample(k, (idx + 1) % n, h, l, b);
        k[0x17A] = (idx + 2) % n;
        k[0x17B] = 2;
        ST->prev_btn = b;
        ST->ours = 1;
        return;
    }

    /* real samples queued: a bare Wii Remote gets the pad as its extension;
     * a real Nunchuk or Classic Controller is never touched */
    ST->ours = 0;
    ST->prev_btn = b;
    if (cnt > n)
        cnt = n;
    for (i = 0; i < cnt; i++) {
        u8 *s = slot(k, (idx + n - cnt + i) % n);
        if (s[0x28] == 0 || s[0x28] == 0xFD)
            fill_cc(s, h, l, b);
    }
}
#endif

#if defined(HOOK_PROBE)
/* WPADProbe(chan, &type): a Classic Controller on channel 0 while a pad
 * answers, unless a real Wii Remote with a real extension is there */
u32 gc_probe(u32 chan, u32 *type)
{
    u32 h, l;
    u8 *blk;
    u32 t;
    s32 status;

    ST->n_probe++;
#ifdef NO_PROBE
    return 0;
#endif
    if (chan || !gc_in(&h, &l))
        return 0;
    blk = *(u8 **)(WPAD_TBL + chan * 4);
    t = blk[WPAD_DEV_TYPE];
    status = *(s32 *)(blk + WPAD_STATUS);
    if (status != -1 && (t == 1 || t == 2))
        return 0;
    if (type)
        *type = 2;
    return 1;
}
#endif
