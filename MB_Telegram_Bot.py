import os
import time
import threading
import requests
from supabase import create_client, Client
from flask import Flask

# --- 1. WEB SERVER SETUP (The Trojan Horse) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🦅 MomentumBurst Cloud Engine is LIVE and scanning via TradingView."

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

# --- 4. THE TRADINGVIEW ENGINE (Bypasses Yahoo IP Bans) ---
# Global cache maps raw tickers to exact TV exchanges (e.g., "PAGEIND" -> "NSE:PAGEIND")
tv_cache = {}

def fetch_price_tv(ticker, market):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    # Map database market string to TV country code for accurate search resolution
    country = ""
    if market and "india" in market.lower():
        country = "IN"
    elif market and "us" in market.lower():
        country = "US"

    # 1. Resolve Exact Exchange (Hit once per stock, then cached)
    if ticker not in tv_cache:
        search_url = f"https://symbol-search.tradingview.com/symbol_search/v3/?text={ticker}&hl=1&type=stock"
        if country:
            search_url += f"&country={country}"
        
        try:
            res = requests.get(search_url, headers=headers, timeout=5)
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                exchange = data[0].get("exchange")
                symbol = data[0].get("symbol")
                tv_cache[ticker] = f"{exchange}:{symbol}"
            else:
                return None
        except Exception as e:
            print(f"TV Search Error for {ticker}: {e}")
            return None
            
    full_tv_ticker = tv_cache.get(ticker)
    if not full_tv_ticker:
        return None

    # 2. Fetch Live Price via Global Scanner
    scan_url = "https://scanner.tradingview.com/global/scan"
    payload = {
        "symbols": {"tickers": [full_tv_ticker]},
        "columns": ["close"]
    }
    try:
        res = requests.post(scan_url, headers=headers, json=payload, timeout=5)
        data = res.json()
        if data.get("data") and len(data["data"]) > 0:
            price_array = data["data"][0].get("d", [])
            if price_array and len(price_array) > 0:
                return float(price_array[0])
    except Exception as e:
        print(f"TV Scan Error for {ticker}: {e}")
        
    return None

# --- 5. THE CORE SCANNER ENGINE ---
def run_bot():
    print("🦅 Cloud Telegram Engine Active. Scanning via TradingView Protocol...")
    
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

                # 🥷 Fetch using TradingView Engine
                live_price = fetch_price_tv(original_ticker, market)
                
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
