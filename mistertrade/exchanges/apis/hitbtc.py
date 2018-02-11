import time
import math
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
import requests

from ..abc import Exchange, ExchangeAPI, ExchangeCLI, exchange_name
from ..errors import *

LOGGER = logging.getLogger(__name__)

__all__ = ['Hitbtc']

@exchange_name('hitbtc')
class Hitbtc(Exchange):
  def __init__(self):
    super(Hitbtc, self).__init__(
      HitbtcAPI, 
      HitbtcCLI
    )

class HitbtcCLI(ExchangeCLI):
  def __init__(self, *args, **kwargs):
    super(HitbtcCLI, self).__init__(*args, **kwargs)

class HitbtcAPI(ExchangeAPI):

  def __init__(self, *args, **kwargs):
    super(HitbtcAPI, self).__init__(*args, **kwargs)
    self._session = requests.Session()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self._session.close()

  def market_url(self, market):
    base_coin, market_coin = market.split('-')
    return "https://hitbtc.com/exchange/{market_coin}-to-{base_coin}".format(market_coin=market_coin,base_coin=base_coin)

  def markets(self):
    response = self.request('/api/2/public/symbol')
    result = list()
    for item in response:
      result.append({
        'exchange': self.name,
        'base_coin': item['quoteCurrency'],
        'market_coin': item['baseCurrency'],
        'market': item['quoteCurrency'] + '-' + item['baseCurrency'],
        'minimum_trade_size': float(item['quantityIncrement'])
      })
    return result

  def fee(self, quantity, base_coin):
    return quantity * 0.0025# TODO not accurate, we should fetch this

  def ask(self, market, quantity, limit):
    raise NotImplementedError()

  def ask_when_less_than(self, market, quantity, limit, target_rate):
    raise NotImplementedError()

  def bid(self, market, quantity, limit):
    raise NotImplementedError()

  def bid_when_greater_than(self, market, quantity, limit, target_rate):
    raise NotImplementedError()

  def cancel_order(self, market, order_id):
    raise NotImplementedError()

  def candlesticks(self, market, interval):
    raise NotImplementedError()

  def __parse_interval_param(self, interval):
    raise NotImplementedError()

  def open_orders(self, market):
    raise NotImplementedError()

  def order(self, market, order_id):
    raise NotImplementedError()

  def order_history(self, market):
    raise NotImplementedError()

  def __parse_order(self, market, order):
    raise NotImplementedError()

  def orderbook(self, market):
    raise NotImplementedError()

  def price(self, market):
    raise NotImplementedError()


  def wallet(self, currency=None):
    raise NotImplementedError()

  def __parse_wallet_item(self, item):
    raise NotImplementedError()


  def request (self, url, headers=None, method='GET', params=None, json=None):
    url = 'https://api.hitbtc.com' + url
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
