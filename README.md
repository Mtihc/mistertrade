
# Mistertrade

Wraps multiple crypto currency exchange APIs in one standardized interface.

# Install

## How to install mistertrade

1. Checkout the repository, for example in your home directory:

       $ cd ~
       $ git clone https://github.com/Mtihc/mistertrade.git
       $ cd ~/mistertrade

1. Run the setup

       $ python setup.py install

# The Basics

1. Get command help

       $ mistertrade --help

    or

       $ python
       >> import mistertrade
       >> mistertrade.main('--help')

1. Fetch a list of exchange names

       $ mistertrade exchange names

    or

        $ python
        >> import mistertrade
        >> mistertrade.exchanges.names()

1. Fetch a list of markets, per exchange

       $ mistertrade exchange binance markets

    or

       $ python
       >> import mistertrade
       >> mistertrade.exchanges.api('binance').markets()

