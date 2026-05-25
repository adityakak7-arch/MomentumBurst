import yfinance as yf
import pandas as pd
import warnings
from supabase import create_client, Client

warnings.filterwarnings("ignore")

# --- CLOUD DATABASE CONFIGURATION ---
SUPABASE_URL = "https://efterqfbveimhbfvpfpe.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_lplcsUMUEzN9WpteL9mMCg_XyggSq-z".strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        return [f"{ticker}.NS" for ticker in df['Symbol'].tolist()]
    except:
        return [] # Fallback logic can be added if NSE blocks

def analyze_momentum_burst_in(ticker):
    try:
        stock = yf.Ticker(ticker)
        f_info = stock.fast_info
        
        # 1. PURIFICATION: Market Cap > ₹2000 Cr AND Price > ₹30
        if f_info.market_cap < 20000000000 or f_info.last_price < 30:
            return None
            
        # 2. TECHNICAL GATES
        df = stock.history(period="90d")
        if len(df) < 50: return None
        
        today_str = pd.Timestamp.today('Asia/Kolkata').strftime('%Y-%m-%d')
        if df.index[-1].strftime('%Y-%m-%d') == today_str:
            df = df.iloc[:-1]
            
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        if pd.isna(df['SMA_50'].iloc[-1]): return None
        
        prior_day = df.iloc[-1]
        two_days_ago = df.iloc[-2]
        
        if not (prior_day['Close'] > prior_day['SMA_20'] > prior_day['SMA_50']): return None
        if ((prior_day['High'] - prior_day['Low']) / prior_day['Low']) > 0.025: return None
        if prior_day['Volume'] > two_days_ago['Volume']: return None
            
        # Strip the .NS for cleaner database storage
        clean_ticker = ticker.replace('.NS', '')
        
        return {
            "market": "India",
            "ticker": clean_ticker,
            "prior_close": round(f_info.previous_close, 2),
            "trigger_price": round(f_info.previous_close * 1.04, 2),
            "risk_level": round(prior_day['Low'], 2)
        }
    except:
        return None

if __name__ == "__main__":
    print("🦅 Initiating Indian Market (Nifty 500) Cloud Scanner...")
    tickers = fetch_nifty500_tickers()
    results = []
    
    for i, ticker in enumerate(tickers):
        if i % 50 == 0: print(f"Scanned {i}/{len(tickers)}...")
        data = analyze_momentum_burst_in(ticker)
        if data: results.append(data)
            
    if results:
        supabase.table("watchlists").delete().eq("market", "India").execute()
        supabase.table("watchlists").insert(results).execute()
        print(f"☁️ Successfully locked {len(results)} Indian setups in the cloud.")
    else:
        print("⚠️ Zero setups passed.")
        try: supabase.table("watchlists").delete().eq("market", "India").execute()
        except: pass
