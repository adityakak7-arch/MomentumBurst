import os
import time
import threading
import requests
import yfinance as yf
from supabase import create_client, Client
from flask import Flask

# --- 1. WEB SERVER SETUP (The Trojan Horse) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🦅 MomentumBurst Cloud Engine is LIVE and scanning."

# --- 2. CREDENTIALS & INITIALIZATION ---
# These pull securely from Render's Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Initialize Supabase Database
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("⚠️ CRITICAL: Supabase credentials missing from environment.")

# --- 3. TELEGRAM ALERT FUNCTION ---
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Mock Alert (Keys Missing): {message}")
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

# --- 4. THE CORE SCANNER ENGINE ---
def run_bot():
    print("🦅 Cloud Telegram Engine Active. Scanning...")
    
    while True:
        try:
            if not supabase:
                time.sleep(60)
                continue

            # Fetch all active targets from the watchlists table
            response = supabase.table("watchlists").select("*").execute()
            targets = response.data

            for target in targets:
                ticker = target.get("ticker")
                trigger_price = float(target.get("trigger_price", 0))
                market = target.get("market", "Unknown")
                
                if not ticker or not trigger_price:
                    continue

                # Fetch live price from Yahoo Finance
                try:
                    ticker_data = yf.Ticker(ticker)
                    todays_data = ticker_data.history(period='1d')
                    
                    if todays_data.empty:
                        continue
                    
                    live_price = float(todays_data['Close'].iloc[-1])
                    
                    # 🚨 TRIGGER LOGIC 🚨
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
                        
                        # Delete the row so it doesn't spam you every 60 seconds
                        supabase.table("watchlists").delete().eq("id", target.get("id")).execute()
                        
                except Exception as e:
                    print(f"Error checking {ticker}: {e}")

        except Exception as e:
            print(f"Scanner Loop Error: {e}")
        
        # Rest for 60 seconds before scanning again
        time.sleep(60)

# --- 5. EXECUTION ---
if __name__ == '__main__':
    # 1. Start the scanning engine in the background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # 2. Start the dummy web server to keep Render Free Tier happy
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
