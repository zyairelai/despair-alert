#!/usr/bin/python3

import pandas, requests, time, socket, os, sys
from datetime import datetime
from termcolor import colored

def print_usage():
    print(f"[i] Usage: {os.path.basename(sys.argv[0])} [number]")
    sys.exit(0)

if len(sys.argv) > 1:
    arg = sys.argv[1]
    val = arg[1:] if arg.startswith("-") else arg
    if val.isdigit(): LOOKBACK = int(val)
    else: print_usage()
else: print_usage()

# ----- Configuration -----
SYMBOL = "BTCUSDT"

print("\n[i] The DESPAIR script is running...")
print(f"[i] Comparing with previous {LOOKBACK} candles.\n")

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_WOLVESRISE')
    chat_id = "@futures_wolves_rise"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")

session = requests.Session()
def get_klines(pair, interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in data]
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    candlestick = pandas.DataFrame(result, columns=cols).sort_values("timestamp")
    candlestick["body"] = (candlestick["close"] - candlestick["open"]).abs()
    candlestick["upper_wick"] = candlestick["high"] - candlestick[["open", "close"]].max(axis=1)
    candlestick["lower_wick"] = candlestick[["open", "close"]].min(axis=1) - candlestick["low"]
    return candlestick

def heikin_ashi(klines):
    heikin_ashi_df = pandas.DataFrame(index=klines.index.values, columns=['ha_open', 'ha_high', 'ha_low', 'ha_close'])
    heikin_ashi_df['ha_close'] = (klines['open'] + klines['high'] + klines['low'] + klines['close']) / 4

    for i in range(len(klines)):
        if i == 0: heikin_ashi_df.iat[0, 0] = klines['open'].iloc[0]
        else: heikin_ashi_df.iat[i, 0] = (heikin_ashi_df.iat[i-1, 0] + heikin_ashi_df.iat[i-1, 3]) / 2

    heikin_ashi_df.insert(0,'timestamp', klines['timestamp'])
    heikin_ashi_df['ha_high'] = heikin_ashi_df.loc[:, ['ha_open', 'ha_close']].join(klines['high']).max(axis=1)
    heikin_ashi_df['ha_low']  = heikin_ashi_df.loc[:, ['ha_open', 'ha_close']].join(klines['low']).min(axis=1)
    heikin_ashi_df['volume'] = klines['volume']
    heikin_ashi_df['body'] = (heikin_ashi_df['ha_close'] - heikin_ashi_df['ha_open']).abs()
    heikin_ashi_df['upper_wick'] = heikin_ashi_df['ha_high'] - heikin_ashi_df[['ha_open', 'ha_close']].max(axis=1)
    heikin_ashi_df['lower_wick'] = heikin_ashi_df[['ha_open', 'ha_close']].min(axis=1) - heikin_ashi_df['ha_low']
    heikin_ashi_df['color'] = heikin_ashi_df.apply(lambda row: 'GREEN' if row['ha_close'] >= row['ha_open'] else 'RED', axis=1)
    heikin_ashi_df['20MA'] = klines['close'].rolling(window=20).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', 'body', 'upper_wick', 'lower_wick', '20MA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def short_despair():
    one_hour = heikin_ashi(get_klines(SYMBOL, "1h"))

    if one_hour['ha_low'].iloc[-1] < one_hour['ha_low'].iloc[-(LOOKBACK+1):-1].min():
        telegram_bot_sendtext("💥 1H STRUCTURE BREAK 💥")
        exit()

    if one_hour['color'].iloc[-1] == "GREEN":
        condition_1 = one_hour['body'].iloc[-1] > (one_hour['lower_wick'].iloc[-1] * 2)
        condition_2 = one_hour['upper_wick'].iloc[-1] > (one_hour['body'].iloc[-1] * 2)
        condition_3 = one_hour['upper_wick'].iloc[-1] > (one_hour['lower_wick'].iloc[-1] * 2)
        condition_4 = one_hour['upper_wick'].iloc[-1] > (one_hour['lower_wick'].iloc[-1] + one_hour['body'].iloc[-1])

        if condition_1 and condition_2 and condition_3 and condition_4:
            telegram_bot_sendtext("💥 1H PIN BAR 💥")
            exit()

try:
    while True:
        try:
            short_despair()
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
