import yfinance as yf
import pandas as pd
import numpy as np

# Starting with your curated structural universe for speed
curated_universe = ["HAL.NS", "BEL.NS", "ZENTEC.NS", "GENUSPOWER.NS", "SENCO.NS", "ETERNAL.NS", "SUZLON.NS", "JIOFIN.NS", "TMPV.NS", "RELIANCE.NS", "BHEL.NS"]

def backtest_ticker(ticker):
    try:
        # Fetch 3 years of daily data
        df = yf.download(ticker, period="3y", progress=False)
        if len(df) < 100: return []
        
        # Flatten multi-index columns if yfinance returns them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        trades = []
        
        # We start at day 50 (to allow SMAs to calculate) and stop before the last day
        for i in range(50, len(df) - 1):
            prior_day = df.iloc[i]
            
            # GATEKEEPER: Trend Alignment
            if not (prior_day['Close'] > prior_day['SMA_20'] and prior_day['SMA_20'] > prior_day['SMA_50']):
                continue
                
            # COMPRESSION CHECK: 3-Day Range < 8%
            last_3 = df.iloc[i-2 : i+1]
            c_high, c_low = last_3['High'].max(), last_3['Low'].min()
            if (c_high - c_low) / c_low > 0.08:
                continue
                
            # EXHAUSTION CHECK: Avoid 3 consecutive green days
            if all(last_3['Close'].iloc[j] > last_3['Open'].iloc[j] for j in range(3)):
                continue
                
            # MICRO-COMPRESSION: Prior day range < 2.5%
            if (prior_day['High'] - prior_day['Low']) / prior_day['Close'] > 0.025:
                continue
                
            # SETUP DETECTED. Calculate Execution Parameters.
            trigger_price = prior_day['Close'] * 1.04
            stop_loss = prior_day['Low']
            risk_per_share = trigger_price - stop_loss
            if risk_per_share <= 0: continue
            
            next_day = df.iloc[i+1]
            
            # Did the breakout trigger the next day?
            if next_day['High'] >= trigger_price:
                # We are filled at the trigger price
                entry_price = trigger_price
                entry_date = df.index[i+1]
                
                # --- TRADE MANAGEMENT (Finding the Exit) ---
                exit_price = 0
                exit_date = None
                
                for j in range(i+1, len(df)):
                    current_day = df.iloc[j]
                    
                    # Condition A: Hard Stop Loss Hit Intraday
                    if current_day['Low'] <= stop_loss:
                        exit_price = stop_loss
                        exit_date = df.index[j]
                        break
                        
                    # Condition B: Trailing Stop (Close below 20 SMA)
                    if current_day['Close'] < current_day['SMA_20']:
                        # We exit at the close
                        exit_price = current_day['Close']
                        exit_date = df.index[j]
                        break
                        
                # If the trade is still open today
                if exit_date is None:
                    exit_price = df['Close'].iloc[-1]
                    exit_date = df.index[-1]
                    
                # Calculate R-Multiple
                profit_per_share = exit_price - entry_price
                r_multiple = profit_per_share / risk_per_share
                
                trades.append({
                    "Ticker": ticker.replace('.NS', ''),
                    "Entry Date": entry_date.strftime("%Y-%m-%d"),
                    "Exit Date": exit_date.strftime("%Y-%m-%d"),
                    "R-Multiple": round(r_multiple, 2)
                })
                
        return trades
    except Exception as e:
        return []

if __name__ == "__main__":
    print("🦅 Booting Backtest Engine...")
    print("Scanning 3 years of historical data against Gatekeeper rules...\n")
    
    all_trades = []
    for t in curated_universe:
        results = backtest_ticker(t)
        all_trades.extend(results)
        
    if all_trades:
        results_df = pd.DataFrame(all_trades)
        
        total_trades = len(results_df)
        wins = results_df[results_df['R-Multiple'] > 0]
        losses = results_df[results_df['R-Multiple'] <= 0]
        
        win_rate = (len(wins) / total_trades) * 100
        avg_win = wins['R-Multiple'].mean() if not wins.empty else 0
        avg_loss = losses['R-Multiple'].mean() if not losses.empty else 0
        expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
        
        print(f"--- SYSTEM PERFORMANCE (Last 3 Years) ---")
        print(f"Total Breakouts Traded: {total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Average Winning Trade: +{avg_win:.2f}R")
        print(f"Average Losing Trade: {avg_loss:.2f}R")
        print(f"System Expectancy: {expectancy:.2f}R per trade")
        print("-----------------------------------------")
        
        print("\nTop 5 Best Trades:")
        print(results_df.sort_values(by="R-Multiple", ascending=False).head(5).to_string(index=False))
    else:
        print("No valid setups found in the historical data.")

