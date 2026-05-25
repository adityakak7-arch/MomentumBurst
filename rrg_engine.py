import yfinance as yf
import pandas as pd
import warnings
import ssl

warnings.filterwarnings("ignore")
ssl._create_default_https_context = ssl._create_unverified_context

# --- RRG PARAMETERS ---
BENCHMARK = "^NSEI" # Nifty 50
SECTORS = {
    "Financials": "^NSEBANK",
    "Technology": "^CNXIT",
    "Auto": "^CNXAUTO",
    "FMCG (Defensive)": "^CNXFMCG",
    "Healthcare": "^CNXPHARMA",
    "Metals & Mining": "^CNXMETAL",
    "Energy": "^CNXENERGY",
    "Real Estate": "^CNXREALTY",
    "Infrastructure": "^CNXINFRA"
}

def calculate_rrg(period="6mo"):
    print(f"Fetching market data for Benchmark (Nifty 50) and {len(SECTORS)} sectors...")
    
    # Fetch Benchmark
    bench_data = yf.download(BENCHMARK, period=period, progress=False)['Close']
    if isinstance(bench_data, pd.DataFrame):
        bench_data = bench_data.iloc[:, 0]
        
    results = []
    
    for name, ticker in SECTORS.items():
        try:
            sector_data = yf.download(ticker, period=period, progress=False)['Close']
            if isinstance(sector_data, pd.DataFrame):
                sector_data = sector_data.iloc[:, 0]
                
            df = pd.concat([sector_data, bench_data], axis=1).dropna()
            df.columns = ['Sector', 'Benchmark']
            
            # 1. Relative Strength (RS)
            df['RS'] = df['Sector'] / df['Benchmark']
            
            # 2. RS-Ratio (Trend - 14 Day Smoothing)
            df['RS_Ratio'] = 100 * (df['RS'] / df['RS'].rolling(window=14).mean())
            
            # 3. RS-Momentum (Velocity - 14 Day Smoothing)
            df['RS_Momentum'] = 100 * (df['RS_Ratio'] / df['RS_Ratio'].rolling(window=14).mean())
            
            # Extract latest coordinates
            latest_ratio = df['RS_Ratio'].iloc[-1]
            latest_momentum = df['RS_Momentum'].iloc[-1]
            
            # Classify Quadrant
            if latest_ratio > 100 and latest_momentum > 100:
                quadrant = "LEADING 🟢"
            elif latest_ratio > 100 and latest_momentum <= 100:
                quadrant = "WEAKENING 🟡"
            elif latest_ratio <= 100 and latest_momentum <= 100:
                quadrant = "LAGGING 🔴"
            else:
                quadrant = "IMPROVING 🔵"
                
            results.append({
                "Sector": name,
                "RS-Ratio": round(latest_ratio, 2),
                "RS-Momentum": round(latest_momentum, 2),
                "Regime Quadrant": quadrant
            })
        except Exception as e:
            pass
            
    return pd.DataFrame(results)

if __name__ == "__main__":
    print("\n🧭 Booting Macro Regime & RRG Engine...\n")
    rrg_df = calculate_rrg()
    
    if not rrg_df.empty:
        # Sort by best Trend (X-Axis)
        rrg_df = rrg_df.sort_values(by="RS-Ratio", ascending=False)
        print("\n--- CURRENT NIFTY SECTOR REGIMES ---")
        print(rrg_df.to_string(index=False))
        print("------------------------------------\n")
