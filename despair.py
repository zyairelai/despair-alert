#!/usr/bin/python3

import time, socket, os
from datetime import datetime, timedelta
try: import pandas, requests
except ImportError:
    print("Library not found, run:\npip3 install pandas requests --break-system-packages")
    exit(1)

def sleep_until_next_hour():
    now = datetime.now()
    # even_hour = 2 - (now.hour % 2)
    next_hour = (now.replace(minute=0, second=10, microsecond=0) + timedelta(hours=1))
    sleep_seconds = (next_hour - now).total_seconds()
    if sleep_seconds > 0: time.sleep(sleep_seconds)

def telegram_bot_sendtext(bot_message):
    print(bot_message + "\nTriggered at: " + str(datetime.today().strftime("%d-%m-%Y @ %H:%M:%S\n")))
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")
print("The DESPAIR script is running...\n")

session = requests.Session()
def get_klines(pair, interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": pair, "interval": interval, "limit": 100}
    r = session.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()
    result = []
    for x in data: result.append([x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])])
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
    result_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume', 'color', '25MA', '100EMA']
    for col in result_cols: heikin_ashi_df[col] = heikin_ashi_df[col].apply(lambda v: round(v) if isinstance(v, float) and not pandas.isna(v) else v)
    return heikin_ashi_df[result_cols]

def condition_1h(pair):
    one_hour = heikin_ashi(get_klines(pair, "1h"))
    low_condition = one_hour['ha_low'].iloc[-1] < one_hour['ha_low'].iloc[-4:-1].min()
    return low_condition # -4:1 = previous 3 candles

def condition_15m(pair):
    minute_15m = get_klines(pair, "15m")
    low_condition = minute_15m['low'].iloc[-1] < minute_15m['low'].iloc[-5:-1].min()
    volume_condition = minute_15m['volume'].iloc[-1] > minute_15m['volume'].iloc[-5:-1].mean() * 2
    return low_condition and volume_condition

def condition_15m_raw(pair):
    minute_15m = get_klines(pair, "15m")
    body_size = minute_15m['body'].iloc[-1] > minute_15m['body'].iloc[-3:-1].sum()
    lower_low = minute_15m['close'].iloc[-1] < minute_15m['low'].iloc[-3:-1].min()
    volume_condition = minute_15m['volume'].iloc[-1] > minute_15m['volume'].iloc[-3:-1].mean() * 1.5
    return body_size and lower_low and volume_condition

def short_despair():
    if condition_1h("BTCUSDT"):
        telegram_bot_sendtext("💥 1H STRUCTURE BREAK 💥")
        sleep_until_next_hour()
    if condition_15m("BTCUSDT"):
        telegram_bot_sendtext("💥 15m HEIKIN ASHI VOLUME FLUSH 💥")
        sleep_until_next_hour()
    if condition_15m_raw("BTCUSDT"):
        telegram_bot_sendtext("💥 15m RAW CANDLE STRUCTURE BREAK 💥")
        sleep_until_next_hour()

try:
    while True:
        try:
            short_despair()
            time.sleep(5)
        except (ConnectionResetError, socket.timeout, requests.exceptions.RequestException) as e:
            print(f"Network error: {e}")
            time.sleep(10)
            continue
except KeyboardInterrupt: print("\n\nAborted.\n")
