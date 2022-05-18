import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler
import prettytable as pt
import json

from apikey import APIKEY


ALERT_STATUS = False
pairs = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "MATICUSDT", "XLMUSDT", "DOTUSDT",
         "ADAUSDT", "BNBUSDT", "BCHUSDT", "LTCUSDT", "ETCUSDT", "SOLUSDT", "LINKUSDT"]
# [{"pair": "BTCUSDT", "from": 2356.52, "to": 2345.23, "alert?": False}]
zones = []

client = httpx.AsyncClient()


async def add_zone(update: Update, context: CallbackContext.DEFAULT_TYPE):
    global zones
    try:
        pair = context.args[0].upper()
        if pair in pairs:
            fromPrice, toPrice = min(
                float(context.args[1]), float(context.args[2])), max(
                float(context.args[1]), float(context.args[2]))
            zones.append(
                {"pair": pair, "from": fromPrice, "to": toPrice, "alert?": False})
            zones = sorted(zones, key=lambda pair: pair['pair'])
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Alert for {pair} [{fromPrice} - {toPrice}] successfully set!")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Pair not found! Correct usage: /add [pair] [first price] [second price]")
    except (ValueError, IndexError):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Correct usage: /add [pair] [first price] [second price]")


async def show_zones(update: Update, context: CallbackContext.DEFAULT_TYPE):
    if zones:
        table = pt.PrettyTable(['ID', 'Pair', 'Range'])
        table.align['ID'] = 'c'
        table.align['Pair'] = 'c'
        table.align['Range'] = 'c'
        for id, zone in enumerate(zones):
            table.add_row(
                [str(id), zone["pair"], f'{zone["from"]:.3f} - {zone["to"]:.3f}'])
        if ALERT_STATUS:
            alert_status = "Enabled"
        else:
            alert_status = "Disabled"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Alert Status: {alert_status} <pre>{table}</pre>", parse_mode="html")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No alert is currently set!")


async def alert(context: CallbackContext.DEFAULT_TYPE):
    global zones
    job = context.job
    # get data from Binance
    r = await client.get("https://api.binance.com/api/v3/ticker/price", params={"symbols": '["BTCUSDT","ETHUSDT","XRPUSDT","MATICUSDT","XLMUSDT","DOTUSDT","ADAUSDT","BNBUSDT","BCHUSDT","LTCUSDT","ETCUSDT","SOLUSDT","LINKUSDT"]'})
    currentPrices = json.loads(r.text)
    for pair in currentPrices:
        for tzone in list(filter(lambda zone: zone['pair'] == pair["symbol"], zones)):
            if float(pair["price"]) >= tzone["from"] and float(pair["price"]) <= tzone["to"] and not tzone["alert?"]:
                tzone["alert?"] = True
                await context.bot.send_message(job.chat_id, text=f"ALERT! Price on {pair['symbol']} has just hit support/resistance! [{tzone['from']} - {tzone['to']}]")
            elif float(pair["price"]) < tzone["from"] and float(pair["price"]) > tzone["to"] and tzone["alert?"]:
                tzone["alert?"] = False
    context.job_queue.run_once(
        alert, 5, chat_id=job.chat_id, name=str(job.chat_id))


async def remove_zone(update: Update, context: CallbackContext.DEFAULT_TYPE):
    global zones
    try:
        zone = zones.pop(int(context.args[0]))
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Alert for {zone['pair']} [{zone['from']} - {zone['to']}] sucessfully removed!")
    except (ValueError, IndexError):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Correct usage: /remove [id]")


async def remove_all(update: Update, context: CallbackContext.DEFAULT_TYPE):
    global zones
    zones.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Sucessfully removed all alerts!")


async def start_alert(update: Update, context: CallbackContext.DEFAULT_TYPE):
    global ALERT_STATUS
    ALERT_STATUS = True
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Alerts have been enabled!")
    context.job_queue.run_once(alert, 10, chat_id=update.effective_message.chat_id, name=str(
        update.effective_message.chat_id))


async def get_info(update: Update, context: CallbackContext.DEFAULT_TYPE):
    table = pt.PrettyTable(['Pair', 'Current Price'])
    table.align['Pair'] = 'c'
    table.align['Current Price'] = 'c'
    r = await client.get("https://api.binance.com/api/v3/ticker/price", params={"symbols": '["BTCUSDT","ETHUSDT","XRPUSDT","MATICUSDT","XLMUSDT","DOTUSDT","ADAUSDT","BNBUSDT","BCHUSDT","LTCUSDT","ETCUSDT","SOLUSDT","LINKUSDT"]'})
    currentPrices = json.loads(r.text)
    for pair in currentPrices:
        price = float(pair["price"])
        table.add_row([pair['symbol'], f'{price:.3f}'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<pre>{table}</pre>", parse_mode="html")


if __name__ == '__main__':
    application = ApplicationBuilder().token(APIKEY).build()
    add_handler = CommandHandler('add', add_zone)
    show_handler = CommandHandler('show', show_zones)
    remove_handler = CommandHandler(['remove', 'delete'], remove_zone)
    removeAll_handler = CommandHandler(['deleteAll', 'removeAll'], remove_all)
    info_handler = CommandHandler('info', get_info)
    start_handler = CommandHandler('start', start_alert)

    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(add_handler)
    application.add_handler(show_handler)
    application.add_handler(remove_handler)
    application.add_handler(removeAll_handler)

    application.run_polling(stop_signals=None)
