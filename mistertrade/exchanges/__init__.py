import sys, argparse
from .constants import *
from .errors import *
from .apis import *

from .abstract import get_exchange_instances
_exchanges = get_exchange_instances(sys.modules[__name__])
_exchange_names = list(_exchanges.keys())
_exchange_names.sort()


def names():
    return _exchange_names


def get(name):
    return _exchanges.get(name)


def api(name, *args, **kwargs):
    return _exchanges.get(name).api(*args, **kwargs)
