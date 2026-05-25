import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- CONFIG ---
st.set_page_config(page_title="Quantitative Execution Cockpit", layout="wide")
st.title("🦅 Institutional Momentum Engine")

# --- CLOUD DATABASE CONFIGURATION ---
SUPABASE_URL = "https://efterqfbveimhbfvpfpe.supabase.co".strip()
SUPABASE_KEY = "sb_publishable_lplcsUMUEzN9WpteL9mMCg_XyggSq-z".strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_live_metrics(ticker, market):
    try:
        yf_ticker = f"{ticker}.NS" if market == "India" else ticker
        stock = yf.Ticker(yf_ticker)
        hist = stock.history(period="40d")
        if len(hist) < 20: return None, None
        return stock.fast_info.last_price, hist['Close'].rolling(window=20).mean().iloc[-1]
    except:
        return None, None

def fetch_live_radar_cloud(market):
    try:
        response = supabase.table("watchlists").select("*").eq("market", market).execute()
        if not response.data: return None
        
        df = pd.DataFrame(response.data)
        df["Live Price"] = 0.0
        df["Spread (%)"] = ""

        for index, row in df.iterrows():
            ticker = row["ticker"]
            yf_ticker = f"{ticker}.NS" if market == "India" else ticker
            try:
                live_price = float(yf.Ticker(yf_ticker).fast_info.last_price)
                trigger_price = float(row["trigger_price"])
                
                df.at[index, "Live Price"] = round(live_price, 2)
                spread = ((trigger_price / live_price) - 1) * 100
                
                if spread <= 0:
                    df.at[index, "Spread (%)"] = f"{abs(round(spread, 2))}% 🚨 TRIGGERED"
                elif spread <= 1.0:
                    df.at[index, "Spread (%)"] = f"{round(spread, 2)}% 🟡 CLOSE"
                else:
                    df.at[index, "Spread (%)"] = f"{round(spread, 2)}%"
            except:
                df.at[index, "Spread (%)"] = "Error"
                
        # Clean up column names for the UI
        df = df.rename(columns={"ticker": "Ticker", "prior_close": "Prior Close", "trigger_price": "Breakout Trigger", "risk_level": "Risk Level"})
        return df[["Ticker", "Prior Close", "Breakout Trigger", "Risk Level", "Live Price", "Spread (%)"]]
    except:
        return None

tab1, tab2, tab3 = st.tabs(["📡 Live Radar", "📝 Log Execution", "🛡️ Active Portfolio & Exits"])

with tab1:
    st.header("Purified Breakout Setups (Cloud)")
    if st.button("🔄 PING LIVE MARKET STATS", type="primary"):
        with st.spinner("Fetching live execution spreads from Supabase..."):
            st.session_state['in_radar'] = fetch_live_radar_cloud("India")
            st.session_state['us_radar'] = fetch_live_radar_cloud("US")
            
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🇮🇳 Indian Market (Nifty 500)")
        if st.session_state.get('in_radar') is not None:
            st.dataframe(st.session_state['in_radar'], width='stretch', hide_index=True)
        else:
            st.info("Hit Ping to load cloud data.")
            
    with col2:
        st.subheader("🇺🇸 US Market (S&P 500)")
        if st.session_state.get('us_radar') is not None:
            st.dataframe(st.session_state['us_radar'], width='stretch', hide_index=True)
        else:
            st.info("Hit Ping to load cloud data.")

with tab2:
    st.header("Log New Position")
    with st.form("trade_logger"):
        c1, c2, c3, c4 = st.columns(4)
        market_sel = c1.selectbox("Market", ["India", "US"])
        account_input = c2.text_input("Account", value="Parth's")
        ticker_input = c3.text_input("Ticker")
        date_input = c4.date_input("Execution Date", datetime.date.today())
        
        c5, c6, c7 = st.columns(3)
        entry_price = c5.number_input("Average Fill Price", min_value=0.01, format="%.2f")
        stop_price = c6.number_input("Hard Stop Loss", min_value=0.01, format="%.2f")
        shares = c7.number_input("Total Shares Bought", min_value=1, step=1)
        
        if st.form_submit_button("Lock Position"):
            if ticker_input and entry_price and stop_price and shares and account_input:
                risk = (entry_price - stop_price) * shares
                new_trade = {
                    "execution_date": str(date_input), 
                    "account": account_input.strip(),
                    "market": market_sel, 
                    "ticker": ticker_input.upper(), 
                    "entry_price": entry_price, 
                    "initial_stop": stop_price, 
                    "shares": shares, 
                    "one_r_risk": round(risk, 2)
                }
                supabase.table("active_portfolio").insert(new_trade).execute()
                st.success(f"Locked {ticker_input.upper()} into '{account_input}' on Supabase! Risk: {risk:.2f}")

with tab3:
    st.header("Live Position Tracking & Exit Alerts")
    
    # Fetch live portfolio from Supabase
    pf_response = supabase.table("active_portfolio").select("*").execute()
    df_pf = pd.DataFrame(pf_response.data) if pf_response.data else pd.DataFrame()
    
    if df_pf.empty:
        st.info("No active positions logged in the cloud.")
    else:
        if st.button("🔄 Run 3:15 PM Exit Scan & P&L"):
            with st.spinner("Polling live market data..."):
                results, exit_alerts = [], []
                total_pnl_in, total_invested_in = 0.0, 0.0
                total_pnl_us, total_invested_us = 0.0, 0.0
                account_metrics = []
                
                for _, row in df_pf.iterrows():
                    live_price, sma_20 = get_live_metrics(row['ticker'], row['market'])
                    if live_price is None: continue
                    
                    account_name = str(row.get('account', "Parth's"))
                    open_risk = float(row.get('one_r_risk', 0))
                    shares = int(row.get('shares', 1))
                    invested_capital = row['entry_price'] * shares
                    pnl = (live_price - row['entry_price']) * shares
                    r_mult = pnl / open_risk if open_risk > 0 else 0
                    
                    if row['market'] == 'India':
                        total_pnl_in += pnl
                        total_invested_in += invested_capital
                        pnl_display = f"₹{pnl:.2f}"
                        capital_display = f"₹{invested_capital:.2f}"
                    else:
                        total_pnl_us += pnl
                        total_invested_us += invested_capital
                        pnl_display = f"${pnl:.2f}"
                        capital_display = f"${invested_capital:.2f}"
                        
                    account_metrics.append({
                        "Account": account_name,
                        "Market": row['market'],
                        "Deployed": invested_capital,
                        "PnL": pnl
                    })
                    
                    status = "HOLD 🟢"
                    if live_price <= row['initial_stop']:
                        status = "🚨 STOP LOSS HIT 🔴"
                        exit_alerts.append(f"SELL {row['ticker']} ({account_name}) at Market (Hard Stop)")
                    elif live_price < sma_20:
                        status = "🚨 SMA BROKEN 🔴"
                        exit_alerts.append(f"SELL {row['ticker']} ({account_name}) at Market (20-SMA Broken)")
                        
                    results.append({
                        "Account": account_name,
                        "Ticker": row['ticker'], 
                        "Market": row['market'], 
                        "Capital Deployed": capital_display,
                        "Entry": row['entry_price'], 
                        "Live Price": round(live_price, 2), 
                        "20-SMA": round(sma_20, 2), 
                        "Live P&L": pnl_display,
                        "Current R-Mult": f"{r_mult:.2f} R", 
                        "Status": status
                    })
                
                st.divider()
                st.subheader("Global Portfolio Exposure")
                pct_return_in = (total_pnl_in / total_invested_in) * 100 if total_invested_in > 0 else 0
                pct_return_us = (total_pnl_us / total_invested_us) * 100 if total_invested_us > 0 else 0
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🇮🇳 Nifty 500 Deployed", f"₹{total_invested_in:,.2f}")
                m2.metric("🇮🇳 Nifty 500 Open P&L", f"₹{total_pnl_in:,.2f}", f"{pct_return_in:.2f}%")
                m3.metric("🇺🇸 S&P 500 Deployed", f"${total_invested_us:,.2f}")
                m4.metric("🇺🇸 S&P 500 Open P&L", f"${total_pnl_us:,.2f}", f"{pct_return_us:.2f}%")
                
                if account_metrics:
                    with st.expander("💼 Account-Level Breakdown", expanded=True):
                        df_acc = pd.DataFrame(account_metrics)
                        df_summary = df_acc.groupby(['Account', 'Market']).sum().reset_index()
                        df_summary['ROIC (%)'] = (df_summary['PnL'] / df_summary['Deployed']) * 100
                        df_summary['ROIC (%)'] = df_summary['ROIC (%)'].apply(lambda x: f"{x:.2f}%")
                        df_summary['Deployed'] = df_summary.apply(lambda r: f"₹{r['Deployed']:,.2f}" if r['Market'] == 'India' else f"${r['Deployed']:,.2f}", axis=1)
                        df_summary['PnL'] = df_summary.apply(lambda r: f"₹{r['PnL']:,.2f}" if r['Market'] == 'India' else f"${r['PnL']:,.2f}", axis=1)
                        st.dataframe(df_summary, width='stretch', hide_index=True)
                
                st.divider()
                st.subheader("Open Positions")
                st.dataframe(pd.DataFrame(results).style.map(lambda v: 'color: #ff4b4b;' if '🚨' in str(v) else 'color: #00cc96;', subset=['Status']), width='stretch')
                
                if exit_alerts:
                    for alert in exit_alerts: st.warning(alert)
                else:
                    st.success("All positions holding trend structure.")
                    
        st.divider()
        close_ticker = st.selectbox("Remove from Active Portfolio:", df_pf['ticker'].tolist())
        if st.button("Mark as Closed"):
            supabase.table("active_portfolio").delete().eq("ticker", close_ticker).execute()
            st.success(f"{close_ticker} removed from cloud database. Refresh page to update.")
