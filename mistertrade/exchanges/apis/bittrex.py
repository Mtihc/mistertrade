import time
import math
import requests
import datetime
import logging
import hmac
import hashlib
from urllib.parse import urlparse, urlencode
from urllib.error import HTTPError
import urllib.request
import json
from decimal import *
import random
from ..abc import Exchange, ExchangeAPI, ExchangeCLI, exchange_name
from ..errors import *

LOGGER = logging.getLogger(__name__)

__all__ = ['Bittrex']

@exchange_name('bittrex')
class Bittrex(Exchange):
  def __init__(self):
    super(Bittrex, self).__init__(
      BittrexAPI, 
      BittrexCLI
    )

class BittrexCLI(ExchangeCLI):
  def __init__(self, *args, **kwargs):
    super(BittrexCLI, self).__init__(*args, **kwargs)

class BittrexAPI(ExchangeAPI):

  def __init__(self, *args, **kwargs):
    super(BittrexAPI, self).__init__(*args, **kwargs)
    self._session = requests.Session()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self._session.close()

  def market_url(self, market):
    return "https://bittrex.com/Market/Index?MarketName={}".format(market)
  
  def markets(self):
    result = self.request('https://bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries')
    result = [self.__parse_markets_item(x['Market']) for x in result]
    self.validate_markets(result)
    return result

  def __parse_markets_item(self, item):
    return {
      'exchange': self.name,
      'base_coin': item['BaseCurrency'],
      'market_coin': item['MarketCurrency'],
      'market': item['MarketName'],
      'minimum_trade_size': item['MinTradeSize']
    }

  def fee(self, quantity, base_coin):
    return quantity * 0.0025

  def buy_stop(self, market, quantity, rate, distance):
    return self.buy_or_sell_stop('buy', market, quantity, rate, distance)

  def sell_stop(self, market, quantity, rate, distance):
    return self.buy_or_sell_stop('sell', market, quantity, rate, distance)

  def buy_or_sell_stop(self, buy_or_sell, market, quantity, rate, distance):

    base_coin, market_coin = market.split('-')
    LOGGER.debug("{exchange_name}: Stop-{buy_or_sell} {quantity:.8f} {market_coin} at {rate:.8f} with distance {distance:.8f}...".format(
      buy_or_sell=("Selling" if buy_or_sell == 'sell' else "Buying"),
      exchange_name=self.name,
      quantity=quantity,
      market_coin=market_coin,
      base_coin=base_coin,
      rate=rate,
      distance=distance
    ))
    if buy_or_sell == 'sell':
      return self.__bittrex_ask(
        market=market,
        order_type='LIMIT',
        quantity=quantity,
        rate=rate,
        time_in_effect='GOOD_TIL_CANCELLED',
        condition_type='STOP_LOSS_FIXED',
        target=distance
      )
    elif buy_or_sell == 'buy':
      return self.__bittrex_bid(
        market=market,
        order_type='LIMIT',
        quantity=quantity,
        rate=rate,
        time_in_effect='GOOD_TIL_CANCELLED',
        condition_type='STOP_LOSS_FIXED',
        target=distance
      )
    else:
      raise ValueError("Parameter buy_or_sell should be 'buy' or 'sell'.")

  def ask(self, market, quantity, rate):
    base_coin, market_coin = market.split('-')
    LOGGER.debug("{exchange_name}: {buy_or_sell} {quantity:.8f} {market_coin} at {rate:.8f} ...".format(
      buy_or_sell="Selling",
      exchange_name=self.name,
      quantity=quantity,
      market_coin=market_coin,
      base_coin=base_coin,
      rate=rate
    ))

    return self.__bittrex_ask(
      market=market,
      order_type='LIMIT',
      quantity=quantity,
      rate=rate,
      time_in_effect='GOOD_TIL_CANCELLED',
      condition_type='NONE',
      target=None
    )


  def ask_when_less_than(self, market, quantity, rate, target_rate):
    base_coin, market_coin = market.split('-')
    LOGGER.debug("{exchange_name}: {buy_or_sell} {quantity:.8f} {market_coin} at {rate:.8f} when less than {target_rate:.8f}...".format(
      buy_or_sell="Selling",
      exchange_name=self.name,
      quantity=quantity,
      market_coin=market_coin,
      base_coin=base_coin,
      rate=rate,
      target_rate=target_rate
    ))

    return self.__bittrex_ask(
      market=market,
      order_type='LIMIT',
      quantity=quantity,
      rate=rate,
      time_in_effect='GOOD_TIL_CANCELLED',
      condition_type='LESS_THAN',
      target=target_rate
    )

  def bid(self, market, quantity, rate):
    base_coin, market_coin = market.split('-')

    LOGGER.debug("{exchange_name}: {buy_or_sell} {quantity:.8f} {market_coin} at {rate:.8f} ...".format(
      buy_or_sell="Buying",
      exchange_name=self.name,
      quantity=quantity,
      market_coin=market_coin,
      base_coin=base_coin,
      rate=rate
    ))

    return self.__bittrex_bid(
      market=market,
      order_type='LIMIT',
      quantity=quantity,
      rate=rate,
      time_in_effect='GOOD_TIL_CANCELLED',
      condition_type='NONE',
      target=None)

  def bid_when_greater_than(self, market, quantity, rate, target_rate):
    base_coin, market_coin = market.split('-')

    LOGGER.debug("{exchange_name}: {buy_or_sell} {quantity:.8f} {market_coin} at {rate:.8f} when greater than {target_rate:.8f} ...".format(
      buy_or_sell="Buying",
      exchange_name=self.name,
      quantity=quantity,
      market_coin=market_coin,
      base_coin=base_coin,
      rate=rate,
      target_rate=target_rate
    ))

    return self.__bittrex_bid(
      market=market,
      order_type='LIMIT',
      quantity=quantity,
      rate=rate,
      time_in_effect='GOOD_TIL_CANCELLED',
      condition_type='GREATER_THAN',
      target=target_rate)



  def cancel_order(self, market, order_id):
    LOGGER.debug("{exchange_name}: Cancelling order {order_id}.".format(exchange_name=self.name, order_id=order_id))
    self.request_private('https://bittrex.com/api/v2.0/key/market/tradecancel', method='POST', json={
      'orderId': order_id,
      'MarketName': market
    })
    return



  def candlesticks (self, market=None, interval='hour'):

    result = self.request('https://bittrex.com/api/v2.0/pub/market/GetTicks' + '?' + urlencode({
      'marketName': self.__parse_market_param(market),
      'tickInterval': self.__parse_interval_param(interval)
    }))
    if result is None: return None
    result = list(map(self.__parse_candlestick, result))
    return result

  def candlesticks_since(self, market=None, interval='minute', since=None):

    result = self.request('https://bittrex.com/api/v2.0/pub/market/GetLatestTick' + '?' + urlencode({
      'marketName': market,
      'tickInterval': self.__parse_interval_param(interval),
      '_': since if since is not None else int(time.time())
    }))
    result = list(map(self.__parse_candlestick, result))
    return result

  def __parse_candlestick(self, candlestick):
    candlestick['high'] = candlestick.pop('H')
    candlestick['low'] = candlestick.pop('L')
    candlestick['close'] = candlestick.pop('C')
    candlestick['open'] = candlestick.pop('O')
    candlestick['volume'] = candlestick.pop('V')
    candlestick['time'] = candlestick.pop('T')# TODO parse time properly
    candlestick.pop('BV')
    return candlestick



  def open_orders(self, market):
    result = self.request_private('https://bittrex.com/api/v2.0/key/market/getopenorders' + '?' + urlencode({
      'marketName': market
    }))
    return list(map(self.__parse_open_order, result))

  def __parse_open_order(self, order):
    return self.__parse_order(order)


  def order (self, market, order_id):
    result = self.request_private('https://bittrex.com/api/v2.0/key/orders/getorder' + '?' + urlencode({
      'orderid': order_id,
    }))
    if not result: return None
    return self.__parse_order(result)

  def __parse_order(self, order):
    if order is None: return None

    order_type = order.get('Type', order.get('OrderType'))
    if 'BuyOrSell' in order:
      buy_or_sell = order['BuyOrSell'].lower()
    else:
      buy_or_sell = 'sell' if 'SELL' in order_type else ('buy' if 'BUY' in order_type else None)
    if buy_or_sell is None:
      raise ValueError("Can't parse order. Can't determine if it's a buy or sell order: {}.".format(buy_or_sell))

    order_type = 'limit' if 'LIMIT' in order_type else ('market' if 'MARKET' in order_type else None)
    if order_type is None:
      raise ValueError("Can't parse order. Order type is unknown: {}.".format(order_type))

    order_id = order.get('OrderUuid', order.get('OrderId'))
    quantity = order['Quantity']
    market = order.get('Exchange', order.get('MarketName'))
    base_coin, market_coin = market.split('-')

    if 'PricePerUnit' in order and order['PricePerUnit']:
      rate = order['PricePerUnit']
    elif 'Rate' in order and order['Rate']:
      rate = order['Rate']
    elif 'Limit' in order and order['Limit']:
      rate = order['Limit']
    elif 'Price' in order and order['Price']:
      rate = order['Price'] / order['Quantity']
    else:
      raise ValueError("Can't parse order. Order rate is unknown")

    if 'Price' in order and order['Price'] > 0:
      price = order['Price']
    else:
      fee = self.fee(quantity * rate, base_coin)
      if buy_or_sell == 'sell':
        fee = fee * -1
      price = math.ceil((quantity * rate + fee) * 10000000)/10000000


    result = {
      'order_id': order_id,
      'buy_or_sell': buy_or_sell,
      'order_type': order_type,
      'exchange': self.name,
      'market': market,
      'base_coin': base_coin,
      'market_coin': market_coin,
      'quantity': quantity,
      'quantity_remaining': order.get('QuantityRemaining', quantity),
      'rate': rate,
      'price': price,
      'is_open': order.get('IsOpen', False),
      'time': order.get('TimeStamp', order.get('Opened')),# TODO properly parse time
      'meta': {
        'data': order
      }

    }
    result['is_filled'] = result['quantity_remaining'] == 0
    result['is_partially_filled'] = result['quantity_remaining'] > 0 and result['quantity_remaining'] < result['quantity']

    # result of place bid
    # {
    #   "OrderId": "6efcf720-27c0-4bb1-b8cf-5bccdbb01adc",
    #   "MarketName": "USDT-BTC",
    #   "MarketCurrency": "BTC",
    #   "BuyOrSell": "Buy",
    #   "OrderType": "LIMIT",
    #   "Quantity": 0.00074074,
    #   "Rate": 11000.0
    # }

    # open order:
    # {
    #   "Uuid": "e2152d28-597a-4b43-8868-e30e5d342c8b",
    #   "Id": 4953015642,
    #   "OrderUuid": "97872ac7-a793-4ef1-bd95-72c8d1ddcac6",
    #   "Exchange": "BTC-XMR",
    #   "OrderType": "LIMIT_BUY",
    #   "Quantity": 0.05,
    #   "QuantityRemaining": 0.05,
    #   "Limit": 0.02136587,
    #   "CommissionPaid": 0.0,
    #   "Price": 0.0,
    #   "PricePerUnit": null,
    #   "Opened": "2017-12-25T20:17:59.803",
    #   "Closed": null,
    #   "IsOpen": true,
    #   "CancelInitiated": false,
    #   "ImmediateOrCancel": false,
    #   "IsConditional": false,
    #   "Condition": "NONE",
    #   "ConditionTarget": null,
    #   "Updated": null
    # }
    # order by id:

    # {
    #   "AccountId": null,
    #   "OrderUuid": "14bee319-d509-42c8-9a1f-0bad9cd62dbd",
    #   "Exchange": "BTC-XMR",
    #   "Type": "LIMIT_BUY",
    #   "Quantity": 0.04,
    #   "QuantityRemaining": 0.0,
    #   "Limit": 0.02008424,
    #   "Reserved": 0.00080336,
    #   "ReserveRemaining": 0.00080336,
    #   "CommissionReserved": 2e-06,
    #   "CommissionReserveRemaining": 0.0,
    #   "CommissionPaid": 2e-06,
    #   "Price": 0.00080336,
    #   "PricePerUnit": 0.020084,
    #   "Opened": "2017-12-19T17:33:14.517",
    #   "Closed": "2017-12-19T21:35:47.423",
    #   "IsOpen": false,
    #   "Sentinel": "42d2510d-8192-4c8c-8515-91707e2fbbfd",
    #   "CancelInitiated": false,
    #   "ImmediateOrCancel": false,
    #   "IsConditional": false,
    #   "Condition": "NONE",
    #   "ConditionTarget": null
    # }

    # order history:

    # {
    #   "OrderUuid": "84305ba0-6992-443a-89ef-735017852532",
    #   "Exchange": "BTC-XMR",
    #   "TimeStamp": "2017-12-25T02:50:21.12",
    #   "OrderType": "LIMIT_SELL",
    #   "Limit": 0.0245528,
    #   "Quantity": 0.05,
    #   "QuantityRemaining": 0.0,
    #   "Commission": 3.06e-06,
    #   "Price": 0.00122764,
    #   "PricePerUnit": 0.0245528,
    #   "IsConditional": false,
    #   "Condition": "NONE",
    #   "ConditionTarget": null,
    #   "ImmediateOrCancel": false,
    #   "Closed": "2017-12-25T02:50:35.86"
    # }
    return result


  def order_history(self, market):
    result = self.request_private('https://bittrex.com/api/v2.0/key/orders/getorderhistory' + '?' + urlencode({'marketname': market}))
    #result = self.request_private('/api/v1.1/account/getorderhistory' + '?' + urlencode({'market': market}))
    result = [self.__parse_order(order) for order in result if order['Exchange'] == market]
    return result



  def orderbook (self, market):
    result = self.request('/api/v1.1/public/getorderbook?type=both&market={}'.format(market))
    for item in result['buy']:
      item['quantity']  = item.pop('Quantity')
      item['rate']      = item.pop('Rate')
    for item in result['sell']:
      item['quantity']  = item.pop('Quantity')
      item['rate']      = item.pop('Rate')
    #result['buy'] = result['buy'][::-1]
    #result['sell'] = result['sell'][::-1]
    self.validate_orderbook(result)
    return result



  def price(self, market):
    #result = self.request('/api/v1.1/public/getticker' + '?' + urlencode({'market': market}))
    orderbook = self.orderbook(market)
    return {
      'time': format(time.time()),
      'highest_bid': self.get_highest_bid(orderbook),
      'lowest_ask': self.get_lowest_ask(orderbook)
    }

  def wallet(self, currency=None):
    if currency is None:
      result = self.request_private('https://bittrex.com/api/v2.0/key/balance/getbalances')
      return [self.__parse_wallet_item(x['Balance']) for x in result if x['Balance']['Balance'] > 0]
    else:
      result = self.request_private('https://bittrex.com/api/v2.0/key/balance/getbalance', params={'currencyname': currency})
      return [self.__parse_wallet_item(result)]

  def __parse_wallet_item(self, item):
    return {
      'name': item['Currency'],
      'balance': item['Balance'],
      'pending': item['Pending'],
      'available': item['Available']
    }

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self._session.close()

  def request (self, url, headers=None, method='GET', params=None, json=None):
    response = self._session.request(method, url, params=params, json=json, headers=headers)
    response.raise_for_status()
    json = response.json()
    if not json.get('success'):
      msg = json.get('message', "Unknown {} response error.".format(self.name))
      msg = msg + ' (' + method + ' ' + url + ')'
      LOGGER.error(msg)
      raise ExchangeError(msg)
    return json.get('result')

  def request_private (self, url, headers=None, method='GET', params=None, json=None):
    if not params: params = {}
    params['apikey'] = self.apikey
    params['nonce'] = str(int(time.time() * 1000))
    headers = {
      'apisign': hmac.new(self.apisecret.encode(), url.encode(), hashlib.sha512).hexdigest()
    }
    return self.request(url, headers=headers, method=method, params=params, json=json)


  def __bittrex_ask(self, market, quantity, rate, order_type, time_in_effect, condition_type, target):
    params = self.__bittrex_validate_trade_params(market, quantity, rate, order_type, time_in_effect, condition_type, target)
    url = 'https://bittrex.com/api/v2.0/key/market/tradesell'
    order = self.request_private(url=url, method='POST', json=params)
    order = self.__parse_order(order)
    order['is_open'] = True
    return order

  def __bittrex_bid(self, market, quantity, rate, order_type, time_in_effect, condition_type, target):
    params = self.__bittrex_validate_trade_params(market, quantity, rate, order_type, time_in_effect, condition_type, target)
    url = 'https://bittrex.com/api/v2.0/key/market/tradebuy'
    order = self.request_private(url=url, method='POST', json=params)
    order = self.__parse_order(order)
    order['is_open'] = True
    return order

  def __bittrex_validate_trade_params(self, market, quantity, rate, order_type='LIMIT', time_in_effect='GOOD_TIL_CANCELLED', condition_type=None, target=None):
    market = str(market).upper()
    quantity = float(quantity)
    rate = float(rate)
    self.validate_minimum_trade_size(market, quantity, rate)

    order_type = str(order_type).upper()
    order_type_options = ['LIMIT', 'MARKET']
    if order_type not in order_type_options:
      raise ValueError("Parameter order_type should be one of the following: {}".format(", ".join(order_type_options)))
    time_in_effect = str(time_in_effect).upper()
    time_in_effect_options = ['GOOD_TIL_CANCELLED', 'IMMEDIATE_OR_CANCEL', 'FILL_OR_KILL']
    if time_in_effect not in time_in_effect_options:
      raise ValueError("Parameter time_in_effect should be one of the following: {}".format(", ".join(time_in_effect_options)))

    if condition_type is not None and condition_type != 'NONE':
      condition_type = str(condition_type).upper()
      condition_type_options = ['NONE', 'LESS_THAN', 'GREATER_THAN', 'STOP_LOSS_FIXED', 'STOP_LOSS_PERCENTAGE']
      if condition_type not in condition_type_options:
        raise ValueError("Parameter condition_type should be one of the following: {}".format(", ".join(condition_type_options)))

      if target is None:
        raise ValueError("Parameter target is required when condition_type '{}' is set.".condition_type)
      target = float(target)
      if target <= 0:
        raise ValueError("Parameter target must be greater than zero.")
    else:
      condition_type = 'NONE'
      target = 0

    params = {
      'marketname': market,
      'rate': rate,
      'quantity': quantity,
      'ordertype': order_type,
      'timeInEffect': time_in_effect,
      'conditiontype': condition_type,
      'target': target
    }
    return params

  def __parse_market_param(self, market):
    return str(market).upper()
  def __parse_interval_param(self, interval):
    interval_map = { 'minute': 'oneMin', 'hour': 'hour', 'day': 'Day' }
    return interval_map.get(str(interval).lower())
