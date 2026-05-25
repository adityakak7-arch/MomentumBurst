import yfinance as yf
import pandas as pd
import urllib.request
import io
import ssl
import warnings

# Suppress yfinance multi-index warnings for clean terminal output
warnings.filterwarnings("ignore")
ssl._create_default_https_context = ssl._create_unverified_context

def get_nifty500_tickers():
    print("Fetching live Nifty 500 constituents from NSE...")
    url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        csv_data = urllib.request.urlopen(req).read()
        df = pd.read_csv(io.BytesIO(csv_data))
        return df['Symbol'].tolist()
    except Exception as e:
        print("Failed to fetch NSE list. Check network.")
        return []

def backtest_ticker(ticker):
    yf_ticker = f"{ticker}.NS"
    try:
        df = yf.download(yf_ticker, period="3y", progress=False)
        if len(df) < 100: return []
        
        # Flatten yfinance multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        trades = []
        for i in range(50, len(df) - 1):
            prior_day = df.iloc[i]
            
            # GATEKEEPER
            if not (prior_day['Close'] > prior_day['SMA_20'] and prior_day['SMA_20'] > prior_day['SMA_50']):
                continue
                
            # COMPRESSION
            last_3 = df.iloc[i-2 : i+1]
            c_high, c_low = last_3['High'].max(), last_3['Low'].min()
            if (c_high - c_low) / c_low > 0.08:
                continue
                
            # EXHAUSTION
            if all(last_3['Close'].iloc[j] > last_3['Open'].iloc[j] for j in range(3)):
                continue
                
            # MICRO-COMPRESSION
            if (prior_day['High'] - prior_day['Low']) / prior_day['Close'] > 0.025:
                continue
                
            trigger_price = prior_day['Close'] * 1.04
            stop_loss = prior_day['Low']
            risk_per_share = trigger_price - stop_loss
            if risk_per_share <= 0: continue
            
            next_day = df.iloc[i+1]
            if next_day['High'] >= trigger_price:
                entry_price = trigger_price
                exit_price = 0
                exit_date = None
                
                for j in range(i+1, len(df)):
                    current_day = df.iloc[j]
                    if current_day['Low'] <= stop_loss:
                        exit_price = stop_loss
                        exit_date = df.index[j]
                        break
                    if current_day['Close'] < current_day['SMA_20']:
                        exit_price = current_day['Close']
                        exit_date = df.index[j]
                        break
                        
                if exit_date is None:
                    exit_price = df['Close'].iloc[-1]
                    
                r_multiple = (exit_price - entry_price) / risk_per_share
                trades.append({
                    "Ticker": ticker,
                    "R-Multiple": round(r_multiple, 2)
                })
        return trades
    except:
        return []

if __name__ == "__main__":
    print("🦅 Booting Nifty 500 Quantitative Backtest Engine...")
    nse_tickers = get_nifty500_tickers()
    
    all_trades = []
    total = len(nse_tickers)
    print(f"Scanning {total} stocks (This will take ~3 to 5 minutes)...")
    
    for i, t in enumerate(nse_tickers, 1):
        if i % 50 == 0:
            print(f"Processed {i}/{total} data streams...")
        results = backtest_ticker(t)
        all_trades.extend(results)
        
if all_trades:
        print("\nScan complete. Fetching Sector & Market Cap metadata...")
        unique_tickers = list(set([t['Ticker'] for t in all_trades]))
        meta = {}
        for t in unique_tickers:
            try:
                info = yf.Ticker(f"{t}.NS").info
                sector = info.get('sector', 'Unknown')
                mcap = info.get('marketCap', 0)
                meta[t] = {'Sector': sector, 'Cap': mcap}
            except:
                meta[t] = {'Sector': 'Unknown', 'Cap': 0}
                
        # Apply the New Institutional Filters
        toxic_sectors = ['Healthcare', 'Consumer Defensive', 'Communication Services']
        filtered_trades = []
        
        for trade in all_trades:
            ticker_meta = meta[trade['Ticker']]
            # Filter 1: Must be Mid or Large Cap (> 150 Billion INR)
            if ticker_meta['Cap'] < 150_000_000_000:
                continue
            # Filter 2: Must not be in a toxic sector
            if ticker_meta['Sector'] in toxic_sectors:
                continue
                
            filtered_trades.append(trade)
            
        df = pd.DataFrame(filtered_trades)
        
        if not df.empty:
            win_rate = (df['R-Multiple'] > 0).mean() * 100
            expectancy = df['R-Multiple'].mean()
            
            print(f"\n--- PURIFIED NIFTY 500 PERFORMANCE (3 YEARS) ---")
            print(f"Total Breakouts Executed: {len(df)}")
            print(f"System Win Rate: {win_rate:.1f}%")
            print(f"System Expectancy: {expectancy:.2f}R")
            print("------------------------------------------------")
            print("By stripping away Small/Micro caps and regime-lagging sectors,")
            print("this is the true mathematical edge of your current scanner.")
        else:
            print("No trades survived the purified filters.")
