import os
import time
import threading
import requests
import re
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

# --- 3. TELEGRAM ALERT FUNCTION ---
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Mock Alert: \n{message}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram API Error: {e}")

# --- 4. GHOST SCRAPER (Bypasses yfinance API rate limits) ---
def fetch_price_stealth(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        
        # Regex to violently extract the price from Yahoo's HTML fin-streamer tags
        pattern = f'data-symbol="{ticker}"[^>]*data-field="regularMarketPrice"[^>]*value="([^"]+)"'
        match = re.search(pattern, res.text)
        
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        print(f"Scraper error on {ticker}: {e}")
        return None

# --- 5. THE CORE SCANNER ENGINE ---
def run_bot():
    print("🦅 Cloud Telegram Engine Active. Scanning via Ghost Scraper...")
    
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
                ticker = target.get("ticker")
                trigger_price = float(target.get("trigger_price", 0))
                market = target.get("market", "Unknown")
                
                if not ticker or not trigger_price:
                    continue

                # 🥷 Fetch using the new HTML scraper
                live_price = fetch_price_stealth(ticker)
                
                if live_price is None:
                    print(f"Could not extract price for {ticker}")
                    time.sleep(1)
                    continue
                
                # 🚨 BREAKOUT TRIGGER LOGIC
                if live_price >= trigger_price:
                    alert_msg = (
                        f"🚨 *BREAKOUT TRIGGERED*\n\n"
                        f"🎯 *Ticker:* {ticker}\n"
                        f"🔥 *Live Price:* ${live_price:.2f}\n"
                        f"📈 *Trigger Level:* ${trigger_price:.2f}\n"
                        f"📊 *Market:* {market}"
                    )
                    send_telegram_alert(alert_msg)
                    print(f"Triggered: {ticker} at {live_price}")
                    
                    supabase.table("watchlists").delete().eq("id", target.get("id")).execute()
                
                # 📊 SPREAD TRACKING LOGIC
                else:
                    spread_pct = ((trigger_price - live_price) / live_price) * 100
                    row_str = f"{ticker:<8} | {live_price:<7.2f} | {trigger_price:<7.2f} | {spread_pct:>5.1f}%"
                    active_spreads.append((spread_pct, row_str))

                # Polite 1-second breather so we don't get HTML banned
                time.sleep(1)

            # 🕒 HALF-HOURLY SPREAD REPORT
            current_time = time.time()
            if current_time - last_summary_time >= 1800:
                if active_spreads:
                    active_spreads.sort(key=lambda x: x[0])
                    sorted_text_lines = [item[1] for item in active_spreads]
                    
                    summary_msg = "🦅 *30-MINUTE MB RADAR* (Closest to Trigger) 🦅\n\n"
                    summary_msg += "```text\n"
                    summary_msg += f"{'TICKER':<8} | {'LIVE':<7} | {'TRIG':<7} | {'SPRD'}\n"
                    summary_msg += "-" * 37 + "\n"
                    summary_msg += "\n".join(sorted_text_lines)
                    summary_msg += "\n```"
                    
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
