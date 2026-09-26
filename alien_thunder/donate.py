"""Where donations go. The README and the panel widget's Support page list the same wallets."""
from .i18n import N_

WALLETS = [
    {"name": N_("Bitcoin"), "address": "bc1q2nqp9d8lc0u6z7v9ag4u52sv9g9afepgyyrwu4",
     "qr": "donate-btc.png", "networks": ""},
    # One address takes donations on every EVM network Vurto Swap supports.
    {"name": N_("EVM networks"), "address": "0x930CD3e9de6F2dB03709667C9799d073b34FEaCc",
     "qr": "donate-evm.png", "networks": "Ethereum · Optimism · BNB Chain · Gnosis · Polygon · Base · Arbitrum One · Avalanche · Unichain"},
]
