import yfinance as yf
import pandas as pd
import os
import warnings
from datetime import datetime
from supabase import create_client, Client

warnings.filterwarnings("ignore")

# --- CLOUD DATABASE CONFIGURATION ---
SUPABASE_URL = "https://efterqfbveimhbfvpfpe.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_lplcsUMUEzN9WpteL9mMCg_XyggSq-z".strip() # Keep your actual key here

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sp500_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
    except:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tickers = pd.read_html(url)[0]['Symbol'].tolist()
        
    return [str(t).replace('.', '-') for t in tickers]

def analyze_momentum_burst_us(ticker):
    try:
        stock = yf.Ticker(ticker)
        f_info = stock.fast_info
        
        # 1. PURIFICATION: Market Cap > $2B AND Price > $30
        if f_info.market_cap < 2000000000:
            return None
        if f_info.last_price < 30:
            return None
            
        # 2. TECHNICAL GATES
        df = stock.history(period="90d")
        if len(df) < 50: return None
        
        today_str = pd.Timestamp.today('US/Eastern').strftime('%Y-%m-%d')
        if df.index[-1].strftime('%Y-%m-%d') == today_str:
            df = df.iloc[:-1]
            
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        if pd.isna(df['SMA_50'].iloc[-1]): return None
        
        prior_day = df.iloc[-1]
        two_days_ago = df.iloc[-2]
        
        if not (prior_day['Close'] > prior_day['SMA_20'] > prior_day['SMA_50']):
            return None
            
        daily_range = (prior_day['High'] - prior_day['Low']) / prior_day['Low']
        if daily_range > 0.025:
            return None
            
        if prior_day['Volume'] > two_days_ago['Volume']:
            return None
            
        trigger_price = f_info.previous_close * 1.04
        risk_level = prior_day['Low']
        
        # Format dictionary exactly as the Supabase table expects
        return {
            "market": "US",
            "ticker": ticker,
            "prior_close": round(f_info.previous_close, 2),
            "trigger_price": round(trigger_price, 2),
            "risk_level": round(risk_level, 2)
        }
        
    except Exception:
        return None

if __name__ == "__main__":
    print("🦅 Initiating US Market (S&P 500) Cloud Scanner...")
    tickers = fetch_sp500_tickers()
    
    results = []
    print(f"Scanning {len(tickers)} tickers...")
    
    for i, ticker in enumerate(tickers):
        if i % 50 == 0:
            print(f"Scanned {i}/{len(tickers)}...")
            
        data = analyze_momentum_burst_us(ticker)
        if data:
            results.append(data)
            
    if results:
        print("\n✅ Scan Complete! Pushing data to Supabase...")
        
        try:
            # 1. Purge yesterday's US setups from the cloud
            supabase.table("watchlists").delete().eq("market", "US").execute()
            
            # 2. Push today's fresh setups
            supabase.table("watchlists").insert(results).execute()
            
            print(f"☁️ Successfully locked {len(results)} US setups in the cloud database.")
        except Exception as e:
            print(f"⚠️ Database Error: {e}")
            
    else:
        print("\n⚠️ Zero setups passed the institutional gates today.")
        try:
            supabase.table("watchlists").delete().eq("market", "US").execute()
        except:
            pass
