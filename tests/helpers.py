import os
import sys
import warnings

warnings.simplefilter("ignore", ResourceWarning)  # ledgers em memoria nos testes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from coldchain import crypto  # noqa: E402
from coldchain.gateway import Gateway  # noqa: E402
from coldchain.ledger import Ledger  # noqa: E402
from coldchain.node_sim import SimNode  # noqa: E402


def make_setup(**gw_kwargs):
    """No 1 com chave nova, ledger em memoria e gateway que confia no no."""
    key = crypto.generate_keypair()
    node = SimNode(1, key, seed=1)
    ledger = Ledger()
    gw = Gateway(ledger, {1: key.public_key()}, **gw_kwargs)
    return key, node, ledger, gw
