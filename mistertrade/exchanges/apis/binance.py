import time
import math
import datetime
import logging
import hmac
import hashlib
import json

try:
  from urllib.parse import urlparse, urlencode
except ImportError:
  from urllib import urlencode
  from urlparse import urlparse
from decimal import *
import random
import requests
from ..abstract import Exchange, ExchangeAPI, ExchangeCLI, exchange_name
from ..errors import *

LOGGER = logging.getLogger(__name__)

__all__ = ['Binance']

@exchange_name('binance')
class Binance(Exchange):
  def __init__(self):
    super(Binance, self).__init__(
      BinanceAPI, 
      BinanceCLI
    )

class BinanceCLI(ExchangeCLI):
  def __init__(self, *args, **kwargs):
    super(BinanceCLI, self).__init__(*args, **kwargs)

class BinanceAPI(ExchangeAPI):

  def __init__(self, *args, **kwargs):
    super(BinanceAPI, self).__init__(*args, **kwargs)
    self._session = requests.Session()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self._session.close()

  def market_url(self, market):
    return "https://www.binance.com/tradeDetail.html?symbol={}".format(market.replace('-','_'))

  def markets(self):
    response = self.request('/api/v1/exchangeInfo')
    result = list()
    for item in response['symbols']:
      minimum_trade_size = next(float(x['minPrice']) for x in item['filters'] if x['filterType'] == 'PRICE_FILTER')
      result.append({
        'exchange': self.name,
        'base_coin': item['quoteAsset'],
        'market_coin': item['baseAsset'],
        'market': item['quoteAsset'] + '-' + item['baseAsset'],
        'minimum_trade_size': minimum_trade_size
      })
    return result

  def fee(self, quantity, base_coin):
    return quantity * 0.0025# TODO not accurate, we should fetch this

  def ask(self, market, quantity, limit):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/order?symbol={symbol}&side=SELL&type=LIMIT&timeInForce=GTC&quantity={quantity:.8f}&price={limit:.8f}'.format(symbol=symbol,quantity=quantity,limit=limit))
    return self.__parse_order(response)

  def ask_when_less_than(self, market, quantity, limit, target_rate):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/order?symbol={symbol}&side=SELL&type=STOP_LOSS_LIMIT&timeInForce=GTC&quantity={quantity:.8f}&price={limit:.8f}&stopPrice={target_rate:.8f}'.format(symbol=symbol,quantity=quantity,limit=limit,target_rate=target_rate))
    return self.__parse_order(response)

  def bid(self, market, quantity, limit):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/order?symbol={symbol}&side=BUY&type=LIMIT&timeInForce=GTC&quantity={quantity:.8f}&price={limit:.8f}'.format(symbol=symbol,quantity=quantity,limit=limit))
    return self.__parse_order(response)

  def bid_when_greater_than(self, market, quantity, limit, target_rate):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/order?symbol={symbol}&side=BUY&type=TAKE_PROFIT_LIMIT&timeInForce=GTC&quantity={quantity:.8f}&price={limit:.8f}&stopPrice={target_rate:.8f}'.format(symbol=symbol,quantity=quantity,limit=limit,target_rate=target_rate))
    return self.__parse_order(response)

  def cancel_order(self, market, order_id):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/order?symbol={}&orderId={}'.format(symbol, order_id), method='DELETE')
    return

  def candlesticks(self, market, interval):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    interval = self.__parse_interval_param(interval)
    response = self.request('/api/v1/klines?symbol={}&interval={}'.format(symbol, interval))
    result = list()
    for item in response:
      result.append({
        'open': float(item[1]),
        'high': float(item[2]),
        'low': float(item[3]),
        'close': float(item[4]),
        'volume': float(item[5]),
        'time': float(item[0])# TODO parse time properly
      })
    return result

  def __parse_interval_param(self, interval):
    interval_map = { 'minute': '1m', 'hour': '1h', 'day': '1d' }
    return interval_map.get(str(interval).lower())

  def open_orders(self, market):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/openOrders?symbol='.fomrat(symbol))
    result = [self.__parse_order(market, item) for item in response]
    return result

  def order(self, market, order_id):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/allOrders?limit=1&symbol={}&orderId={}'.format(symbol, order_id))
    result = self.__parse_order(market, response[0])
    return result

  def order_history(self, market):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request_private('/api/v3/allOrders?symbol={}'.format(symbol))
    result = [self.__parse_order(market, item) for item in response if item['status'] not in ['NEW', 'PARTIALLY_FILLED']]
    return result

  def __parse_order(self, market, order):
    base_coin, market_coin = market.split('-')

    buy_or_sell = order['side']
    buy_or_sell = 'sell' if 'SELL' in buy_or_sell else ('buy' if 'BUY' in buy_or_sell else None)
    if buy_or_sell is None:
      raise ValueError("Can't parse order. Can't determine if it's a buy or sell order: {}.".format(buy_or_sell))
    
    order_type = order['type']
    order_type = 'limit' if 'LIMIT' in order_type else ('market' if 'MARKET' in order_type else None)
    if order_type is None:
      raise ValueError("Can't parse order. Order type is unknown: {}.".format(order_type))
    order_id = order['orderId']
    quantity = float(order['origQty'])
    quantity_remaining = quantity - float(order['executedQty'])
    rate = float(order['price'])
    price = quantity * rate
    price = self.price_with_fee(buy_or_sell, price, base_coin)

    if order['status'] in ['NEW', 'PARTIALLY_FILLED']:
      is_open = True
    else:
      is_open = False

    result = {
      'order_id': order_id,
      'buy_or_sell': buy_or_sell,
      'order_type': order_type,
      'exchange': self.name,
      'market': market,
      'base_coin': base_coin,
      'market_coin': market_coin,
      'quantity': quantity,
      'quantity_remaining': quantity_remaining,
      'rate': rate,
      'price': price,
      'is_open': is_open,
      'time': order['time'],# TODO properly parse time
      'meta': {
        'data': order
      }

    }
    result['is_filled'] = result['quantity_remaining'] == 0
    result['is_partially_filled'] = result['quantity_remaining'] > 0 and result['quantity_remaining'] < result['quantity']
    return result

  def orderbook(self, market):
    base_coin, market_coin = market.split('-')
    symbol = market_coin + base_coin
    response = self.request('/api/v1/depth?limit=50&symbol={}'.format(symbol))
    result = {
      'buy': list(),
      'sell': list()
    }
    for item in response['bids']:
      result['buy'].append({
        'quantity': float(item[1]),
        'rate': float(item[0])
      })
    for item in response['asks']:
      result['sell'].append({
        'quantity': float(item[1]),
        'rate': float(item[0])
      })
    self.validate_orderbook(result)
    return result

  def price(self, market):
    orderbook = self.orderbook(market)
    return {
      'time': format(time.time()),
      'highest_bid': self.get_highest_bid(orderbook),
      'lowest_ask': self.get_lowest_ask(orderbook)
    }


  def wallet(self, currency=None):
    response = self.request_private('/api/v3/account')
    if currency is not None:
      item = next(item for item in response['balances'] if item['asset'] == currency)
      return self.__parse_wallet_item(item)
    else:
      return [self.__parse_wallet_item(item) for item in response['balances'] if (float(item['locked']) + float(item['free']) > 0)]

  def __parse_wallet_item(self, item):
    item = {
      'name': item['asset'],
      'pending': float(item['locked']),
      'available': float(item['free'])
    }
    item['balance'] = item['pending'] + item['available']
    return item


  def request (self, url, headers=None, method='GET', params=None, json=None):
    url = 'https://api.binance.com' + url
    response = self._session.request(method, url, params=params, json=json, headers=headers)
    response.raise_for_status()
    return response.json()

  def request_private (self, url, headers=None, method='GET', params=None, json=None):
    url += ('&' if urlparse(url).query else '?') + urlencode({
      'timestamp': str(int(time.time() * 1000))
    })
    signature = hmac.new(self.apisecret.encode('utf-8'), urlparse(url).query.encode('utf-8'), hashlib.sha256).hexdigest()
    url += '&' + urlencode({
      'signature': signature
    })
    headers = headers.copy() if headers else dict()
    headers.update({
      'X-MBX-APIKEY': self.apikey
    })
    return self.request(url, headers=headers, method=method, json=json)
