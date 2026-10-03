"""The retail releases of Super Mario Galaxy 2 and their disc versions.
"""
REGIONS = {
    'SB4E01': dict(label='Super Mario Galaxy 2 (USA)', short='USA', version=0),
    'SB4P01': dict(label='Super Mario Galaxy 2 (Europe/Australia)', short='Europe', version=0),
    'SB4J01': dict(label='Super Mario Galaxy 2 (Japan)', short='Japan', version=0),
    'SB4K01': dict(label='Super Mario Galaxy 2 (Korea)', short='Korea', version=0),
    'SB4W01': dict(label='Super Mario Galaxy 2 (Taiwan/Asia)', short='Asia', version=0),
}

# Retail DOL sizes to guard against corrupt or already-modified dumps
DOL_SIZES = {
    'SB4E01': 7546080,
    'SB4P01': 7568352,
    'SB4J01': 7544000,
    'SB4W01': 7546784,
    'SB4K01': 7581952,
}
