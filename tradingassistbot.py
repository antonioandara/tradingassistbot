import logging
import Bittrexlite as bittrex
import Binancelite as bb
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram
import os


#if the API id data is stored as enviroment variable (recommended method)
# BOTKEY = os.environ.get('TELEGRAM_BOT_API')

# if you want to hard code the API key directly (not recommended)
BOTKEY = "YOUR_BOT_KEY_HERE"


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
exchange = 'bittrex'
alarms = {}


def start(update, context):
    """Sends a greeting message"""
    update.message.reply_text("Hi I'm the LOL bot and I'm here to help you keep track of your crypto investments.\n"
                              "I'm only an experimental tool so use me with care.")
    update.message.reply_text("To see a list of available commands text:\n/help")
    print(f'Trading Assistant Bot has started a conversation')

    
def check(update, context):
    """checks the price of any coin on the available exchanges.
        to do this it takes the first string after the command and matches
        it to any available pair from th exchanges
    """
    print(f'--- Check ---')
    data = update.message.text.split()

    if data.__len__() >= 2:

        symbol = data[1].upper()
        # this prevents a request that would otherwise return a message that's too long to display
        if len(symbol) < 3:
            msg = f'Error. ticker {symbol} is too short and produces too many matches'
            print(msg)
            update.message.reply_text(msg)
            return
        elif symbol == 'BTC' or symbol == 'ETH' or symbol == 'BNB' or symbol == 'USDT' or symbol == 'USD':
            msg = f'Error. ticker: {symbol} has too many matches, try again.'
            print(msg)
            update.message.reply_text(msg)
            return

        bittrexcoins = bittrex.tickers()
        # strip the character "-" from the ticker symbols form original Bittrex request
        bittrexcoins = [{'symbol': el['symbol'].replace('-', ''),
                         'lastTradeRate': el['lastTradeRate']} for el in bittrexcoins]
        msg = f'Matches for {symbol} on Bittrex:\n'
        symbol = symbol.replace('-', '')

        for coin in bittrexcoins:
            if symbol in coin['symbol']:
                price = float(coin['lastTradeRate'])
                # this takes care of the formatting and making sure telegram doesn't display number as hyperlinks
                price = f'{price:.8f}' if price < 1 else f'{price}'
                msg += f'{coin["symbol"]} price: `{price}`\n'
        print(msg)
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)

        binancecoins = bb.price()
        msg = f'Matches for {symbol} on Binance:\n'
        for coin in binancecoins:
            if symbol in coin['symbol']:
                price = float(coin['price'])
                price = f'{price:.8f}' if price < 1 else f'{price}'
                msg += f'{coin["symbol"]} price: `{price}`\n'
        print(msg)
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)
        return
    # in case no word is received after the command
    else:
        msg = f'The command /price will try to match any trading pairs with the symbol sent after the command.' \
              f'\ni.e to get all the prices for the ticker ANT send:\n\n' \
              f'/price ant\n\n'
        print(msg)
        update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)
        return


def changeexchange(update, context):
    """Changes the active exchange for storing alarms"""
    global exchange
    data = update.message.text.split()
    data = data[0][1:]
    exchange = data
    msg = f'Using {exchange}'
    print(msg)
    update.message.reply_text(msg)
    return


def alarm(update, context):
    """stores pair and price info received to keep track of alarms"""
    global exchange
    print(f'--- Alarm ---')
    data = update.message.text.split()
    if data.__len__() >= 3:

        symbol = data[1].upper()

        try:
            alarmprice = float(data[2])
            alarmprice = f'{alarmprice:.8f}' if alarmprice < 1 else f'{alarmprice}'

        except ValueError as e:
            print(f'error for alarm price: {e}')
            update.message.reply_text(f'value error for alarm price: {e}')
            return

        if exchange == 'bittrex':
            coin = bittrex.tickers(symbol)

            if 'code' in coin.keys():
                symboldash = list(symbol)
                symboldash.insert(-3, '-')
                symboldash = ''.join(symboldash)

                try:
                    coin = bittrex.tickers(symboldash)
                    price = float(coin['lastTradeRate'])
                    msg = f'Last price of {symboldash}: `{price}`'
                    symbol = symboldash

                except Exception as e:
                    print(f'error: {e}')
                    symboldash = list(symbol)
                    symboldash.insert(-4, '-')
                    symboldash = ''.join(symboldash)

                    try:
                        coin = bittrex.tickers(symboldash)
                        price = float(coin['lastTradeRate'])
                        msg = f'Last price of {symboldash}: `{price}`'
                        symbol = symboldash

                    except Exception as e:
                        print(f'error: {e}')
                        msg = f'{symbol} market does not exist. code: {coin["code"]}'
                        print(msg)
                        update.message.reply_text(msg)
                        return
            else:
                price = float(coin['lastTradeRate'])
                msg = f'Last price of {symbol} is `{price}`'

        elif exchange == 'binance':
            symbol = symbol.replace('-', '')
            coin = bb.price(symbol)

            if 'code' in coin.keys():
                msg = f'code: {coin["code"]}\nsymbol "{symbol}" not recognized\ntry a pair of the form: BTCUSDT'
                print(msg)
                update.message.reply_text(msg)
                return
            price = float(coin['price'])
            msg = f'Last price of {symbol} is `{price}`'

    else:
        msg = f'The /alarm command receives 2 parameters:\n\nsymbol -> alarm price\n\n' \
              f'Example:\nto set an alarm for usd-btc at a price of 11000 send the command:' \
              f'\n\n/alarm usd-btc 11000'

    print(msg)
    update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)

    createAlarm(exchange, symbol, alarmprice)
    msg = f'Alarm created:\n{exchange} {symbol} at {alarmprice}'

    print(msg)
    update.message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN)


def createAlarm(exchange, symbol, price):
    global alarms
    price = float(price)
    print(f'in create alarms: {symbol}')
    if price > 0:
        if exchange not in alarms.keys():
            alarms[exchange] = {}

        if exchange == 'bittrex':
            coin = bittrex.tickers(symbol)
            coin = float(coin['lastTradeRate'])

        elif exchange == 'binance':
            coin = bb.price(symbol)
            coin = float(coin['price'])
        else:
            print(f'error in exchange')
            coin = None

        condition = '>' if coin < price else '<'
        data = (price, condition)

        if symbol in alarms[exchange].keys():
            alarms[exchange][symbol].append(data)
        else:
            alarms[exchange][symbol] = []
            alarms[exchange][symbol].insert(0, data)


        print(f"alarms: {alarms}")
    else:
        print(f"price cannot be negative: {price}")
    return


def help_command(update, context):
    """Sends a a list of available commands"""
    update.message.reply_text(f'Available commands:\n/start --> greeting\n/price --> check ticker price\n'
                              f'/alarm --> set an alarm\n/bittrex --> activate Bittrex\n'
                              f'/binance --> activate Binance\n/help'
                              f'\ntouch any for more info.')


def echo(update, context):
    """when user sends a non command message"""
    update.message.reply_text(f'I do not understand that, try sending a command, or send /help for a list of commands')

def main():
    """Start bot"""
    updater = Updater(BOTKEY, use_context=True)
    dp = updater.dispatcher

    # commandHandlers for the appropriate functions
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("bittrex", changeexchange))
    dp.add_handler(CommandHandler("binance", changeexchange))
    dp.add_handler(CommandHandler("price", check))
    dp.add_handler(CommandHandler("alarm", alarm))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
