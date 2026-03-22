#!/usr/bin/python3

import subprocess, atexit, signal, sys
import time, socket, os, pandas
import requests, threading
from flask import Flask, request

app = Flask(__name__)
session = requests.Session()
ngrok_process = None
despair_running = False
despair_lock = threading.Lock()

def start_ngrok():
    global ngrok_process
    print("Starting ngrok...")
    ngrok_process = subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3) # Wait for ngrok to initialize

    url = get_ngrok_url()
    if url:
        print(f"\nNGROK URL: {url}")
        set_telegram_webhook(url)
    else:
        print("\nFailed to get ngrok URL. Is it running?")

def get_ngrok_url():
    try:
        res = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        res.raise_for_status()
        tunnels = res.json().get("tunnels", [])
        for tunnel in tunnels:
            if tunnel.get("proto") == "https":
                return tunnel.get("public_url")
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
    return None

def set_telegram_webhook(url):
    bot_token = "threeminuteslivermorebot_API_TOKEN_HERE"
    webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={url}"
    try:
        res = requests.get(webhook_url, timeout=10)
        print(f"Telegram Webhook: {res.json().get('description', 'Status unknown')}")
    except Exception as e:
        print(f"Error setting webhook: {e}")

def stop_ngrok():
    global ngrok_process
    if ngrok_process:
        ngrok_process.terminate()
        ngrok_process.wait()

def telegram_bot_sendtext(bot_message):
    print(bot_message)
    bot_token = os.environ.get('TELEGRAM_LIVERMORE')
    chat_id = "@swinglivermore"
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + chat_id + '&parse_mode=html&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

# telegram_bot_sendtext("Telegram works!")
print("The DESPAIR script is running...\n")

session = requests.Session()
def get_klines(interval):
    spot_url = "https://api.binance.com/api/v1/klines"
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": 100}
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

def condition_1h():
    one_hour = heikin_ashi(get_klines("1h"))
    return one_hour['ha_low'].iloc[-1] < one_hour['ha_low'].iloc[-3:-1].min() and \
           one_hour['ha_close'].iloc[-1] < one_hour['ha_close'].iloc[-3:-1].min()

def condition_15m():
    minute_15m = heikin_ashi(get_klines("15m"))
    return minute_15m['ha_close'].iloc[-2] > minute_15m['ha_close'].iloc[-1] and \
           minute_15m['ha_low'].iloc[-1] < minute_15m['ha_low'].iloc[-5:-1].min() and \
           minute_15m['volume'].iloc[-1] > minute_15m['volume'].iloc[-5:-1].mean()

def condition_3m():
    minute_3m = heikin_ashi(get_klines("3m"))
    return all(minute_3m["100EMA"].iloc[-3:] > minute_3m["ha_high"].iloc[-3:])

def short_despair():
    if condition_1h() and condition_15m():
        telegram_bot_sendtext("💥 2H + 15M BOTH MATCHED 💥")
        return True
    if condition_1h():
        telegram_bot_sendtext("💥 2H STRUCTURE BREAK 💥")
        return True
    if condition_15m():
        telegram_bot_sendtext("💥 15m VOLUME FLUSH 💥")
        return True
    return False

def despair_loop():
    global despair_running
    telegram_bot_sendtext("🚀 DESPAIR started 🚀")
    try:
        while despair_running:
            try:
                if short_despair():
                    despair_running = False
                    break
                time.sleep(5)
            except (requests.exceptions.RequestException,
                    socket.timeout,
                    ConnectionResetError) as e:
                telegram_bot_sendtext(f"❌ Network error: {e}")
                time.sleep(10)
    finally: despair_running = False

@app.route("/", methods=["GET", "POST", "HEAD"])
def webhook():
    global despair_running

    if request.method in ["GET", "HEAD"]:
        return "✅ DESPAIR is running", 200

    data = request.get_json(silent=True)
    if not data or "message" not in data: return "ignored", 200

    text = data["message"].get("text", "")
    if text == "/despair":
        with despair_lock:
            if despair_running:
                telegram_bot_sendtext("⚠️ DESPAIR already running")
            else:
                despair_running = True
                threading.Thread(target=despair_loop, daemon=True).start()
    return "ok", 200

atexit.register(stop_ngrok)
def handle_exit():
    stop_ngrok()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    start_ngrok()
    app.run(host="0.0.0.0", port=5000)
