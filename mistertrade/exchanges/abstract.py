import argparse
import functools
import abc
import logging
import time
import requests
import collections
import re

from . import constants

from .. import cli

from .errors import *

__all__ = ['exchange_name', 'get_exchange_name', 'is_exchange_class', 'get_exchange_classes', 'get_exchange_instances', 'Exchange', 'ExchangeAPI', 'ExchangeCLI']

_exchange_name_pattern = re.compile("^[a-z0-9-]{3,}$")

# ==========
# decorators
# ==========

def exchange_name(name):
    """Add this decorator to subclasses of Exchange.

    >>> @exchange_name('my-exchange')
    >>> class MyExchange(Exchange):
    >>>   pass
    >>> 
    >>> is_exchange_class(MyExchange)
    True
    >>> MyExchange.exchange_name()
    my-exchange

    """

    # validate parameter 'name'
    if not isinstance(name, str):
        raise TypeError(
            "Parameter 'name' should be a string instead of {got_type}.".format(
                got_type=type(name).__name__))

    if not _exchange_name_pattern.match(name):
        raise ValueError(
            "Parameter 'name' can't be '{name}'. "
            "It should match the following pattern: {pattern}".format(
                name=name, 
                pattern=_exchange_name_pattern.pattern))

    def decorator(klass):
        """ This is the actual decorator function. It will store the exchange name on the class."""
        
        # validate parameter 'klass'
        if not isinstance(klass, type):
            raise TypeError(
                "The @{decorator} decorator should be applied to a class "
                "instead of {got_type}.".format(
                    decorator=exchange_name.__name__, 
                    got_type=type(klass).__name__))

        # store the name
        klass.__exchange_name__ = name

        return klass

    return decorator

# =========================
# decrator helper functions
# =========================

def get_exchange_name(cls):
    """Returns the exchange name of the given class, or None"""
    return getattr(cls, '__exchange_name__', None)

def is_exchange_class(cls):
    """Returns true when parameter klass is a subclass of Exchange and is marked with the @exchange decorator, False otherwise."""
    return isinstance(cls, type) and issubclass(cls, Exchange) and get_exchange_name(cls) is not None

def get_exchange_classes(module):
    """Returns a dict of exchange classes that are imported in the given module."""
    return { get_exchange_name(klass): klass for klass in (getattr(module, key) for key in dir(module)) if is_exchange_class(klass) }

def get_exchange_instances(module):
    return {name: klass() for name, klass in get_exchange_classes(module).items()}

# ================
# abstract classes
# ================

class Exchange():
    __metaclass__ = abc.ABCMeta

    def __init__(self, api, cli):
        super(Exchange, self).__init__()
        self._api = exchange_name(self.name)(api)
        self._cli = exchange_name(self.name)(cli)

    @classmethod
    def exchange_name(cls):
        return get_exchange_name(cls)

    @property
    def name (self):
        return get_exchange_name(self.__class__)

    def api(self, *args, **kwargs):
        return self._api(*args, **kwargs)

    def cli(self, *argv):
        return self._cli(self, *argv)

class ExchangeAPI():
    __metaclass__ = abc.ABCMeta

    def __init__(self, apikey=None, apisecret=None):
        super(ExchangeAPI, self).__init__()
        self._apikey = apikey
        self._apisecret = apisecret

    @property
    def name (self):
        return get_exchange_name(self.__class__)

    @property
    def apikey(self):
        return self._apikey

    @property
    def apisecret(self):
        return self._apisecret

    @abc.abstractmethod
    def market_url(self, market):
        """Returns the URL for the given market"""
        raise NotImplementedError()

    @abc.abstractmethod
    def fee(self, price, base_coin):
        """Returns the fee applied for a given amount of a given coin"""
        raise NotImplementedError()

    def price_with_fee(self, buy_or_sell, price, base_coin, precision=8):
        """Returns the price incl. fee. Rounds up/down against your favor."""
        if buy_or_sell not in ['buy', 'sell']:
            raise ValueError(
                "Parameter buy_or_sell must be 'buy' or 'sell' "
                "instead of '{}'.".format(buy_or_sell))

        fee = abs(self.fee(price, base_coin))
        price = abs(price)
        
        if buy_or_sell == 'sell':
            fee = fee * -1
            floor_or_ceil = math.floor
        elif buy_or_sell == 'buy':
            floor_or_ceil = math.ceil

        precision = pow(10, precision)
        return floor_or_ceil((price + fee) * precision)/precision

    def minimum_trade_size (self, market):
        """Returns the minimum trade size for the given market."""
        try:
            return self.__minimum_trade_sizes[market]
        except AttributeError as e:
            self.__minimum_trade_sizes = dict([(market['market'], market['minimum_trade_size']) for market in self.markets()])
            return self.__minimum_trade_sizes[market]

    def validate_minimum_trade_size(self, market, quantity, rate):
        """Call this method before placing an order to check if your order conforms to the minimum trade size."""
        minimum_trade_size = self.minimum_trade_size(market)
        if quantity < minimum_trade_size:
            raise MinimumTradeSizeError(
                market_coin=market_coin, 
                quantity=quantity, 
                minimum_trade_size=minimum_trade_size)

    @abc.abstractmethod
    def candlesticks (self, market, interval):
        raise NotImplementedError()

    @abc.abstractmethod
    def markets(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def order (self, market, order_id):
        raise NotImplementedError()

    @abc.abstractmethod
    def order_history(self, market):
        raise NotImplementedError()

    @abc.abstractmethod
    def open_orders(self, market):
        raise NotImplementedError()

    @abc.abstractmethod
    def orderbook(self, market):
        raise NotImplementedError()
    
    def validate_orderbook(self, orderbook, minimum_length=10):
        if orderbook is None:
            raise ValueError("Orderbook can't be None.")
        if 'buy' not in orderbook or 'sell' not in orderbook:
            raise KeyError("Orderbook is missing properties 'buy' and/or 'sell'.")
        if len(orderbook['buy']) < minimum_length or len(orderbook['sell']) < minimum_length:
            raise ValueError("There should be at least {} orders in the orderbook.".format(minimum_length))
        if any('quantity' not in item or 'rate' not in item for item in orderbook['buy']):
            raise KeyError("One or more {buy_or_sell} orders in the order book are missing the 'quantity' and/or 'rate' property.".format("buy"))
        if any('quantity' not in item or 'rate' not in item for item in orderbook['sell']):
            raise KeyError("One or more {buy_or_sell} orders in the order book are missing the 'quantity' and/or 'rate' property.".format("sell"))
        if orderbook['buy'][0]['rate'] < orderbook['buy'][-1]['rate']:
            raise ValueError("The buy orders in the order book should go from high to low.")
        if orderbook['sell'][0]['rate'] > orderbook['sell'][-1]['rate']:
            raise ValueError("The sell orders in the order book should go from low to high.")

    def validate_markets(self, markets):
        self.validate_dict_collection(markets, required_keys=['exchange', 'base_coin', 'market_coin', 'market', 'minimum_trade_size'], collection_name='markets')

    def validate_dict_collection(self, collection, required_keys=[], collection_name='The collection'):
        if collection is None:
            raise ValueError("{} can't be None.".format(collection_name))
        if not isinstance(collection, list):
            raise TypeError("{} should be a list.".format(collection_name))
        if any(not isinstance(item, dict) for item in collection):
            raise TypeError("{} should only contain dict elements.".format(collection_name))
        if any(required_key not in item for item in collection for required_key in required_keys):
            raise KeyError("{} contains elements that don't have all the required keys: {}".format(collection_name, ', '.join(required_keys)))

    def validate_wallet(self, wallet):
        self.validate_dict_collection(wallet, required_keys=['name', 'balance', 'pending', 'available'], collection_name='wallet')

    @abc.abstractmethod
    def price (self, market):
        raise NotImplementedError()

    @abc.abstractmethod
    def cancel_order (self, order_id):
        raise NotImplementedError()

    @abc.abstractmethod
    def wallet(self, currency=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def ask (self, market, quantity, rate):
        raise NotImplementedError()
    
    @abc.abstractmethod
    def ask_when_less_than(self, market, quantity, rate, target_rate):
        raise NotImplementedError()

    @abc.abstractmethod
    def bid(self, market, quantity, rate):
        raise NotImplementedError()

    @abc.abstractmethod
    def bid_when_greater_than(self, market, quantity, rate, target_rate):
        raise NotImplementedError()

class ExchangeCLI():
    __metaclass__ = abc.ABCMeta

    def __init__(self, exchange, *argv):
        super(ExchangeCLI, self).__init__()

        cmds = cli.getcommands(self.__class__)
        command_names = [cmd.name for cmd in cmds]
        command_desc = "    mistertrade {name} {} -h\n" * len(command_names)
        command_desc = command_desc.format(name=self.name, *command_names)
        parser = argparse.ArgumentParser(
            prog='mistertrade exchange ' + self.name,
            description='''Mistertrade {name} commands:

{subcommands}

        '''.format(name=self.name, subcommands=command_desc),
            formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument('--config', type=argparse.FileType('r'), metavar='config/exchanges.yml', default='config/exchanges.yml')

        subparsers = parser.add_subparsers(title='COMMAND')
        subparsers.required = True
        for cmd in cmds:
            subparser = subparsers.add_parser(cmd.name, **cmd.kwargs)
            print(repr(cmd.arguments))
            for args, kwargs in cmd.arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(command=cmd)

        if len(argv) == 0:
            parser.print_help()
            exit()

        args = parser.parse_args(argv)

        cmd = args.command
        del args.command

        config = args.config
        del args.config

        if config:
            with config as stream:
                config = yaml.load(stream)['exchanges'][self.name]
                apikey = config.get('apikey')
                apisecret = config.get('apisecret')
        else:
            apikey = None
            apisecret = None

        self.api = exchange.api(apikey=apikey, apisecret=apisecret)
        
        try:
            cmd(self, **vars(args))
        except ExchangeError as e:
            print(e)
            exit(1)

    @property
    def name (self):
        return get_exchange_name(self.__class__)

    @cli.command()
    def markets(self, *args, **kwargs):
        """Fetches all markets of this exchange."""
        print(cli.helpers.table_str(self.api.markets(*args, **kwargs),
            columns={
                'exchange':           { 'align': '<', 'title': 'Exchange' },
                'market':             { 'align': '<', 'title': 'Market' },
                'minimum_trade_size': { 'align': '>', 'title': 'Min. trade size', 'format': '.8f' }
            }
        ))

    @cli.command(
        cli.argument('market', type=str.upper),
        cli.argument('interval', choices=constants.INTERVALS))
    def candlesticks (self, *args, **kwargs):
        """Fetches the candlesticks for the given market and interval."""
        print(cli.helpers.table_str(self.api.candlesticks(*args, **kwargs), 
            columns={
                'high':     {'align': '>', 'format': '.8f'},
                'open':     {'align': '>', 'format': '.8f'},
                'close':    {'align': '>', 'format': '.8f'},
                'low':      {'align': '>', 'format': '.8f'},
                'volume':   {'align': '>', 'format': '.8f'}
            }
        ))

    @cli.command(
        cli.argument('market', type=str.upper),
        cli.argument('order_id', type=str))
    def order (self, *args, **kwargs):
        """Fetches an order by market and order_id"""
        print(cli.helpers.table_str(self.api.order(*args, **kwargs)))

    @cli.command(
        cli.argument('market', type=str.upper))
    def order_history(self, *args, **kwargs):
        """Fetches order history for the given market"""
        print(cli.helpers.table_str(self.api.order_history(*args, **kwargs)))

    @cli.command(
        cli.argument('market', type=str.upper))
    def open_orders(self, *args, **kwargs):
        """Fetches all open orders for the given market."""
        print(cli.helpers.table_str(self.api.open_orders(*args, **kwargs)))

    @cli.command(
        cli.argument('market', type=str.upper))
    def orderbook(self, *args, **kwargs):
        """Fetches the current state of the orderbook for the given market."""
        print(cli.helpers.table_str(self.api.orderbook(*args, **kwargs)))


    @cli.command(
        cli.argument('market', type=str.upper))
    def price (self, *args, **kwargs):
        """Fetches the current price for the given market."""
        print(cli.helpers.table_str(self.api.price(*args, **kwargs)))

    @cli.command(
        cli.argument('order_id', type=str))
    def cancel_order (self, *args, **kwargs):
        """Cancels an order by order_id"""
        print(cli.helpers.table_str(self.api.cancel_order(*args, **kwargs)))

    @cli.command(cli.argument('-c', '-coin', '-currency', type=str.upper, dest='currency'))
    def wallet(self, *args, **kwargs):
        """Fetches the current state of the wallet. 

        Returns all balances when no currency is specified."""
        print(cli.helpers.table_str(self.api.wallet(*args, **kwargs)))

    @cli.command(
        cli.argument('market', type=str.upper),
        cli.argument('quantity', type=float),
        cli.argument('rate', type=float))
    def ask(self, *args, **kwargs):
        """Place a sell order."""
        print(cli.helpers.table_str(self.api.ask(*args, **kwargs)))

    @cli.command(
        cli.argument('market', type=str.upper),
        cli.argument('quantity', type=float),
        cli.argument('rate', type=float))
    def bid(self, *args, **kwargs):
        """Place a buy order."""
        print(cli.helpers.table_str(self.api.bid(*args, **kwargs)))
