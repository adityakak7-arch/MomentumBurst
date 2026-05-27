import os
import time
import threading
import requests
import re
import urllib.parse
from supabase import create_client, Client
from flask import Flask

# --- 1. WEB SERVER SETUP (The Trojan Horse) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🦅 MomentumBurst Cloud Engine is LIVE and scanning."

# --- 2. CREDENTIALS & INITIALIZATION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("⚠️ CRITICAL: Supabase credentials missing from environment.")

# --- 3. TELEGRAM ALERT FUNCTION (HTML Parser) ---
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Mock Alert: \n{message}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"🚨 Telegram API Rejection: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Telegram Request Error: {e}")

# --- 4. THE MULTI-NODE SCRAPER (Bypasses Cloudflare & IP Bans) ---
def fetch_price_stealth(ticker):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    # Strategy A: Yahoo V7 Spark API (Undocumented, lower security)
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={ticker}&range=1d&interval=1m"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            price = data.get("spark", {}).get("result", [{}])[0].get("response", [{}])[0].get("meta", {}).get("regularMarketPrice")
            if price: return float(price)
    except Exception:
        pass

    # Strategy B: Route through AllOrigins Proxy (Bypasses Render IP Ban entirely)
    try:
        target_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        proxy_url = f"https://api.allorigins.win/raw?url={urllib.parse.quote(target_url)}"
        res = requests.get(proxy_url, timeout=7)
        if res.status_code == 200:
            data = res.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price: return float(price)
    except Exception:
        pass
        
    return None

# --- 5. THE CORE SCANNER ENGINE ---
def run_bot():
    print("🦅 Cloud Telegram Engine Active. Scanning via Multi-Node Proxy...")
    
    last_summary_time = 0 
    
    while True:
        try:
            if not supabase:
                time.sleep(60)
                continue

            response = supabase.table("watchlists").select("*").execute()
            targets = response.data
            active_spreads = []

            for target in targets:
                original_ticker = target.get("ticker", "").strip().upper()
                trigger_price = float(target.get("trigger_price", 0))
                market = target.get("market", "Unknown")
                
                if not original_ticker or not trigger_price:
                    continue

                # 🥷 1. Attempt primary fetch
                live_price = fetch_price_stealth(original_ticker)
                
                # 🥷 2. Dynamic Auto-Correction for Indian Stocks
                if live_price is None and not original_ticker.endswith(".NS") and not original_ticker.endswith(".BO"):
                    live_price = fetch_price_stealth(f"{original_ticker}.NS")
                
                if live_price is None:
                    print(f"Could not extract price for {original_ticker}")
                    time.sleep(1)
                    continue
                
                # 🚨 BREAKOUT TRIGGER LOGIC
                if live_price >= trigger_price:
                    alert_msg = (
                        f"🚨 <b>BREAKOUT TRIGGERED</b>\n\n"
                        f"🎯 <b>Ticker:</b> {original_ticker}\n"
                        f"🔥 <b>Live Price:</b> ${live_price:.2f}\n"
                        f"📈 <b>Trigger Level:</b> ${trigger_price:.2f}\n"
                        f"📊 <b>Market:</b> {market}"
                    )
                    send_telegram_alert(alert_msg)
                    print(f"Triggered: {original_ticker} at {live_price}")
                    
                    supabase.table("watchlists").delete().eq("id", target.get("id")).execute()
                
                # 📊 SPREAD TRACKING LOGIC
                else:
                    spread_pct = ((trigger_price - live_price) / live_price) * 100
                    row_str = f"{original_ticker:<8} | {live_price:<7.2f} | {trigger_price:<7.2f} | {spread_pct:>5.1f}%"
                    active_spreads.append((spread_pct, row_str))

                # Polite 1-second breather
                time.sleep(1)

            # 🕒 HALF-HOURLY SPREAD REPORT
            current_time = time.time()
            if current_time - last_summary_time >= 1800:
                if active_spreads:
                    active_spreads.sort(key=lambda x: x[0])
                    sorted_text_lines = [item[1] for item in active_spreads]
                    
                    summary_msg = "🦅 <b>30-MINUTE MB RADAR</b> (Closest to Trigger) 🦅\n\n"
                    summary_msg += "<pre>\n"
                    summary_msg += f"{'TICKER':<8} | {'LIVE':<7} | {'TRIG':<7} | {'SPRD'}\n"
                    summary_msg += "-" * 37 + "\n"
                    summary_msg += "\n".join(sorted_text_lines)
                    summary_msg += "\n</pre>"
                    
                    send_telegram_alert(summary_msg)
                
                last_summary_time = current_time

        except Exception as e:
            print(f"Scanner Loop Error: {e}")
        
        # Rest for 60 seconds
        time.sleep(60)

# --- 6. EXECUTION ---
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
