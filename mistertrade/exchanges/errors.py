class ExchangeError (Exception):
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return type(self).__name__ + ': ' + self.message

class MinimumTradeSizeError(ExchangeError):
  def __init__(self, market_coin, quantity, minimum_trade_size):
    super(MinimumTradeSizeError, self).__init__("Can't trade {quantity:.8f} {market_coin}. Minimum trade size is {minimum_trade_size:.8f} {market_coin}.".format(quantity=quantity, minimum_trade_size=minimum_trade_size, market_coin=market_coin))
    self._market_coin = market_coin
    self._quantity = quantity
    self._minimum_trade_size = minimum_trade_size

  @property
  def market_coin(self):
  	return self._market_coin

  @property
  def quantity(self):
  	return self._quantity

  def minimum_trade_size(self):
  	return self._minimum_trade_size
