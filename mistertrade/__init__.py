import sys, argparse
from . import cli
from . import exchanges

__all__ = ['exchanges']

def main():
  MistertradeCLI(*sys.argv[1:])

# ===============
# command classes
# ===============

class MistertradeCLI(object):
  def __init__(self, *argv):
    super(MistertradeCLI, self).__init__()

    cmds = cli.getcommands(self.__class__)

    parser = argparse.ArgumentParser(
      usage='%(prog)s COMMAND [--help]')
    subparsers = parser.add_subparsers(title='COMMAND', dest='command')
    subparsers.required = True

    # add subcommand for each method with @cli.command decorator
    for cmd in cmds:
      subparser = subparsers.add_parser(cmd.name, **cmd.kwargs)
      for argument in cmd.arguments:
        subparser.add_argument(*argument[0], **argument[1])
      subparser.set_defaults(command=cmd)

    if len(argv) == 0:
      parser.print_help()
      exit()

    args, rest = parser.parse_known_args(argv[:1])
    args.command(self, *argv[1:])

  @cli.command()
  def exchange(self, *argv):
    ExchangesCLI(*argv)

class ExchangesCLI(object):
  def __init__(self, *argv):
    super(ExchangesCLI, self).__init__()

    cmds = cli.getcommands(self.__class__)

    parser = argparse.ArgumentParser(
      prog='%(prog)s exchange',
      #usage='%(prog)s COMMAND [--help]',
      description='''Mistertrade exchange commands:
  {commands}
    '''.format(commands="\n  ".join(["mistertrade exchange {:<10} [--help]".format(item) for item in [cmd.name for cmd in cmds] + ['NAME']])),
      formatter_class=argparse.RawTextHelpFormatter)

    subparsers = parser.add_subparsers(title='COMMAND', dest='command')
    subparsers.required = True

    # add subcommand for each method with @cli.command decorator
    for cmd in cmds:
      subparser = subparsers.add_parser(cmd.name, **cmd.kwargs)
      for argument in cmd.arguments:
        subparser.add_argument(*argument[0], **argument[1])
      subparser.set_defaults(command=cmd)

    # add subcommand for each exchange name
    exchange_names = exchanges.names()
    for exchange in exchange_names:
      subparser = subparsers.add_parser(exchange, description="{} commands".format(exchange))
      subparser.set_defaults(command=self._exchange_command(exchange))

    if len(argv) == 0:
      parser.print_help()
      exit()
    else:
      if argv[0] in exchanges.names():
        args, rest = parser.parse_known_args(argv[:1])
        args.command(self, *argv[1:])
      else:
        args = vars(parser.parse_args(argv))
        command = args.pop('command')
        command(self, **args)

  def _exchange_command(self, name):
    def _run(self, *argv):
      exchanges.get(name).cli(*argv)
    return _run

  @cli.command(description='Show list of exchange names.')
  def list(self):
    print("Exchange names: "  + ", ".join(names()))

  @cli.command(
    cli.argument('--exchanges', nargs='*', help='Select exchanges', metavar='EXCHANGE', dest='exchange_names'),
    cli.argument('--markets', nargs='*', help='Select markets', metavar='MARKET'),
    description='Show list of markets. Filter by exchange or market name.')
  def markets(self, exchange_names, markets):
    
    # get markets of all exchanges
    if exchange_names:
      _names = exchange_names
    else:
      _names = exchanges.names()
    if not _names:
      print("No exchanges found.")
      exit()

    _result = []
    for name in _names:
      
      _exchange_markets = exchanges.api(name).markets()
      if markets:
        _exchange_markets = [item for item in _exchange_markets if any((market.upper() in item['market']) for market in markets)]
      _result += _exchange_markets

    if not _result:
      # no results
      print("No markets found.")
    else:
      # print results
      print(cli.helpers.table_str(_result,
        columns={
          'exchange':           { 'align': '<', 'title': 'Exchange' },
          'market':             { 'align': '<', 'title': 'Market' }
        }
      ))