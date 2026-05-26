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
        print(f"Mock Alert (Keys Missing): \n{message}")
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
    
    # Set to 0 so the first summary fires immediately on boot
    last_summary_time = 0 
    
    while True:
        try:
            if not supabase:
                time.sleep(60)
                continue

            # Fetch all active targets from the watchlists table
            response = supabase.table("watchlists").select("*").execute()
            targets = response.data

            active_spreads = []

            for target in targets:
                ticker = target.get("ticker")
                trigger_price = float(target.get("trigger_price", 0))
                market = target.get("market", "Unknown")
                
                if not ticker or not trigger_price:
                    continue

                try:
                    # Fetch live price from Yahoo Finance
                    ticker_data = yf.Ticker(ticker)
                    todays_data = ticker_data.history(period='1d')
                    
                    if todays_data.empty:
                        continue
                    
                    live_price = float(todays_data['Close'].iloc[-1])
                    
                    # 🚨 1. BREAKOUT TRIGGER LOGIC 🚨
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
                    
                    # 📊 2. SPREAD TRACKING LOGIC (For targets not yet triggered) 📊
                    else:
                        spread_pct = ((trigger_price - live_price) / live_price) * 100
                        
                        # Store as a tuple: (mathematical_value, formatted_string)
                        # The fixed widths (<8, <7) guarantee perfect table alignment
                        row_str = f"{ticker:<8} | {live_price:<7.2f} | {trigger_price:<7.2f} | {spread_pct:>5.1f}%"
                        active_spreads.append((spread_pct, row_str))

                except Exception as e:
                    print(f"Error checking {ticker}: {e}")

            # 🕒 3. HALF-HOURLY SPREAD REPORT 🕒
            current_time = time.time()
            if current_time - last_summary_time >= 1800:  # 1800 seconds = 30 minutes
                if active_spreads:
                    # Sort ascending based on the numerical spread percentage
                    active_spreads.sort(key=lambda x: x[0])
                    
                    # Extract just the text strings for the payload
                    sorted_text_lines = [item[1] for item in active_spreads]
                    
                    # Assemble the tabular payload inside a monospace code block
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
        
        # Rest for 60 seconds before scanning the actual prices again
        time.sleep(60)

# --- 5. EXECUTION ---
# 1. Start the scanning engine IMMEDIATELY (Crucial for Gunicorn/Render)
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    # 2. Start the dummy web server (Used for local testing, Render uses Gunicorn)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
