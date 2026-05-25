import time
import yfinance as yf
import requests
from supabase import create_client, Client

TELEGRAM_BOT_TOKEN = "8603617814:AAHUpYN0HNlHgFatGTl00t4ZGjZkNrYP728"
TELEGRAM_CHAT_ID = "5665299888"

# --- CLOUD DATABASE CONFIGURATION ---
SUPABASE_URL = "https://efterqfbveimhbfvpfpe.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_YOUR_KEY_HERE".strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def get_cloud_watchlists():
    try:
        response = supabase.table("watchlists").select("*").execute()
        return response.data
    except Exception as e:
        print(f"Cloud DB Error: {e}")
        return []

def run_live_tracker():
    print("🦅 Cloud Telegram Engine Active. Scanning...")
    triggered_tickers = set()

    while True:
        watchlists = get_cloud_watchlists()
        
        for row in watchlists:
            ticker = row['ticker']
            market = row['market']
            trigger = row['trigger_price']
            
            if ticker in triggered_tickers: continue
            
            yf_ticker = f"{ticker}.NS" if market == "India" else ticker
            
            try:
                live_price = yf.Ticker(yf_ticker).fast_info.last_price
                if live_price >= trigger:
                    alert = f"🚨 BREAKOUT TRIGGERED\nMarket: {market}\nTicker: {ticker}\nLive Price: {live_price:.2f}\nTrigger: {trigger:.2f}"
                    send_telegram_message(alert)
                    print(alert)
                    triggered_tickers.add(ticker)
            except:
                pass
                
        time.sleep(60)

if __name__ == "__main__":
    run_live_tracker()
