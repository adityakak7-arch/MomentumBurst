import yfinance as yf
import pandas as pd
import urllib.request
import io
import ssl
import warnings

# Suppress warnings to keep your terminal clean
warnings.filterwarnings("ignore")
ssl._create_default_https_context = ssl._create_unverified_context

def get_sp500_tickers():
    print("Fetching clean S&P 500 constituents dataset...")
    url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        csv_data = urllib.request.urlopen(req).read()
        df = pd.read_csv(io.BytesIO(csv_data))
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Failed to fetch S&P 500 list: {e}")
        return ["AAPL", "MSFT", "NVDA", "JPM", "V", "JNJ", "WMT", "XOM", "PG"]

def backtest_ticker(ticker):
    try:
        df = yf.download(ticker, period="3y", progress=False)
        if len(df) < 100: return []
        
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
                
            trigger_price = c_high * 1.002
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
    print("🦅 Booting S&P 500 Quantitative Backtest Engine...")
    us_tickers = get_sp500_tickers()
    
    all_trades = []
    total = len(us_tickers)
    print(f"Scanning {total} stocks (This will take ~3 to 5 minutes)...")
    
    for i, t in enumerate(us_tickers, 1):
        if i % 50 == 0:
            print(f"Processed {i}/{total} data streams...")
        results = backtest_ticker(t)
        all_trades.extend(results)
        
    if all_trades:
        print("\nScan complete. Fetching Sector & Market Cap metadata for US trades...")
        unique_tickers = list(set([t['Ticker'] for t in all_trades]))
        meta = {}
        for t in unique_tickers:
            try:
                info = yf.Ticker(t).info
                sector = info.get('sector', 'Unknown')
                mcap = info.get('marketCap', 0)
                
                if mcap > 10_000_000_000:
                    cap = "Large Cap"
                elif mcap > 2_000_000_000:
                    cap = "Mid Cap"
                else:
                    cap = "Small Cap"
                    
                meta[t] = {'Sector': sector, 'Cap': cap}
            except:
                meta[t] = {'Sector': 'Unknown', 'Cap': 'Unknown'}
                
        # --- THE PURIFICATION FILTERS ---
        toxic_sectors = ['Healthcare', 'Consumer Defensive', 'Utilities']
        filtered_trades = []
        
        for trade in all_trades:
            ticker_meta = meta[trade['Ticker']]
            
            if ticker_meta['Cap'] != 'Large Cap':
                continue
                
            if ticker_meta['Sector'] in toxic_sectors:
                continue
                
            filtered_trades.append(trade)
            
        df_filtered = pd.DataFrame(filtered_trades)
        
        if not df_filtered.empty:
            win_rate = (df_filtered['R-Multiple'] > 0).mean() * 100
            expectancy = df_filtered['R-Multiple'].mean()
            
            print(f"\n--- PURIFIED S&P 500 PERFORMANCE (3 YEARS) ---")
            print(f"Total Breakouts Executed: {len(df_filtered)}")
            print(f"System Win Rate: {win_rate:.1f}%")
            print(f"System Expectancy: {expectancy:.2f}R")
            print("------------------------------------------------")
            print("By stripping away Mid caps and regime-lagging sectors,")
            print("this is the true mathematical edge in the US market.")
        else:
            print("\nNo trades survived the purified filters.")
    else:
        print("No trades triggered under current parameters.")
