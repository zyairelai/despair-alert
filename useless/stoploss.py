#!/usr/bin/python3

import time, socket, os
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")
print("The STOPLOSS script is running...\n")

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
    heikin_ashi_df['body'] = (heikin_ashi_df['ha_close'] - heikin_ashi_df['ha_open']).abs()
    heikin_ashi_df['volume'] = klines['volume']
    heikin_ashi_df['color'] = heikin_ashi_df.apply(lambda row: 'GREEN' if row['ha_close'] >= row['ha_open'] else 'RED', axis=1)
    heikin_ashi_df['25MA'] = klines['close'].rolling(window=25).mean()
    heikin_ashi_df['100EMA'] = klines['close'].ewm(span=100, adjust=False).mean()
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', 'body', '25MA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def hanging_man(pair, interval):
    timeframe = get_klines(pair, interval)
    is_hanging_man = (
        timeframe['close'].iloc[-1] > timeframe['open'].iloc[-1] and
        timeframe['close'].iloc[-1] <= timeframe['low'].iloc[-5:].min() and
        timeframe['lower_wick'].iloc[-1] > (timeframe['body'].iloc[-1] * 2) + timeframe['upper_wick'].iloc[-1])
    return is_hanging_man

def getting_smaller_1h(pair, interval):
    timeframe = heikin_ashi(get_klines(pair, interval))
    if timeframe['body'].iloc[-2] > timeframe['body'].iloc[-1]:
        return True
    return False

def stoploss_alert(pair):
    if getting_smaller_1h(pair, "1h"):
        telegram_bot_sendtext("🤏 1H GETTING SMALLER 🤏")
        exit()

    # Hanging Man Check (Higher Timeframes Reversal)
    if hanging_man(pair, "2h"):
        telegram_bot_sendtext("🪂 2H HANGING MAN 🪂")
        exit()
    if hanging_man(pair, "1h"):
        telegram_bot_sendtext("🪂 1H HANGING MAN 🪂")
        exit()
    if hanging_man(pair, "15m"):
        telegram_bot_sendtext("🪂 15M HANGING MAN 🪂")
        exit()
    if hanging_man(pair, "5m"):
        telegram_bot_sendtext("🪂 5M HANGING MAN 🪂")
        exit()

try:
    while True:
        try:
            stoploss_alert("BTCUSDT")
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.")
