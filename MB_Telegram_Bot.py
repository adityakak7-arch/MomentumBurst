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

# --- 3. TELEGRAM ALERT FUNCTION (Upgraded to HTML & Error Logging) ---
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Mock Alert: \n{message}")
        return
    
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML" # Shifted from fragile Markdown to HTML
    }
    try:
        res = requests.post(url, json=payload)
        # Diagnostic Patch: Print the exact reason if Telegram rejects the ping
        if res.status_code != 200:
            print(f"🚨 Telegram API Rejection: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Telegram Request Error: {e}")

# --- 4. THE SHADOW SCRAPER (Bypasses Cloudflare HTML Shields) ---
def fetch_price_stealth(ticker):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    # Strategy A: Silent ping to Yahoo's raw data backend
    try:
        api_url = f"[https://query2.finance.yahoo.com/v8/finance/chart/](https://query2.finance.yahoo.com/v8/finance/chart/){ticker}?interval=1m&range=1d"
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price: return float(price)
    except Exception:
        pass

    # Strategy B: Deep regex on embedded HTML JSON payloads
    try:
        html_url = f"[https://finance.yahoo.com/quote/](https://finance.yahoo.com/quote/){ticker}"
        res = requests.get(html_url, headers=headers, timeout=5)
        
        match = re.search(r'"currentPrice"\s*:\s*\{"raw"\s*:\s*([\d\.]+)', res.text)
        if match: return float(match.group(1))
        
        match2 = re.search(f'data-symbol="{ticker}"[^>]*data-field="regularMarketPrice"[^>]*value="([^"]+)"', res.text, re.IGNORECASE)
        if match2: return float(match2.group(1))
    except Exception:
        pass
        
    return None

# --- 5. THE CORE SCANNER ENGINE ---
def run_bot():
    print("🦅 Cloud Telegram Engine Active. Scanning via Shadow Protocol...")
    
    # Set to 0 so the very first summary fires immediately on boot
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

                # Auto-correct Indian tickers for Yahoo Finance backend
                fetch_ticker = original_ticker
                if market.lower() == "india" and not fetch_ticker.endswith(".NS") and not fetch_ticker.endswith(".BO"):
                    fetch_ticker += ".NS"

                # 🥷 Fetch using the shadow scraper
                live_price = fetch_price_stealth(fetch_ticker)
                
                if live_price is None:
                    print(f"Could not extract price for {original_ticker}")
                    time.sleep(1)
                    continue
                
                # 🚨 BREAKOUT TRIGGER LOGIC (HTML Format)
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

            # 🕒 HALF-HOURLY SPREAD REPORT (HTML Format)
            current_time = time.time()
            if current_time - last_summary_time >= 1800:
                if active_spreads:
                    active_spreads.sort(key=lambda x: x[0])
                    sorted_text_lines = [item[1] for item in active_spreads]
                    
                    # Using HTML <pre> to force an indestructible monospace table
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
