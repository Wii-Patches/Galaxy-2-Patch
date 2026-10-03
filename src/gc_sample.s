# hook: KPAD sampling callback, the `addi r0,r27,1` that advances the ring buffer write index
# (r28 = channel, r29 = sample in KPAD's ring buffer, r30 = channel KPAD struct).
#
# If a GameCube pad is responding on the matching port, merge its inputs into the
# sample so player 1 can be driven by either pad or remote.
    addi    0, 27, 1                    # displaced instruction
    .set    CHAN, 28
    .set    SMP, 29
#include gc_convert.s
