import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import os
import time
import numpy as np
from twilio.rest import Client
import telebot
from telebot import TeleBot

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="Day Trade Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== STRONG GLOBAL STYLING (forces colors + clean size + hides toolbar) ======================
st.markdown("""
<style>
    /* Hide unwanted toolbar */
    header, footer, [data-testid="stToolbar"], [data-testid="stHeader"], .stAppDeployButton {
        display: none !important;
    }
    
    /* Button styling */
    button {
        width: 100% !important;
        height: 118px !important;
        font-size: 1.45rem !important;
        font-weight: 700 !important;
        border-radius: 16px !important;
        border: none !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.35) !important;
        margin-bottom: 10px !important;
    }
    button:hover {
        transform: scale(1.03) !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# ====================== CACHING ======================
@st.cache_data(ttl=5, show_spinner=False)
def get_history(ticker: str, period: str = "2d", interval: str = "1d"):
    return yf.Ticker(ticker).history(period=period, interval=interval)

# ====================== CONFIG ======================
DEFAULT_ACCOUNT_SIZE = 175000.0
CSV_FILE = "trade_log.csv"
TICKERS = ["SOXL", "TQQQ", "TECL", "SPXL", "FNGU", "BULZ", "TSLL", "NVDL", "BITX",
           "QLD", "UPRO", "SSO", "LABU", "WEBL"]
KEY_UNDERLYINGS = ["NVDA", "TSLA", "AMD", "AVGO", "AAPL", "MSFT", "META", "AMZN"]

if os.path.exists(CSV_FILE):
    trades_df = pd.read_csv(CSV_FILE)
else:
    trades_df = pd.DataFrame(columns=["Date", "Ticker", "Entry Price", "Exit Price", "Shares", "P/L $", "Notes"])
    trades_df.to_csv(CSV_FILE, index=False)

# ====================== SECRETS ======================
try:
    secrets = st.secrets
except:
    secrets = {}

for prefix, section in [("twilio_", "twilio"), ("telegram_", "telegram")]:
    for key in secrets.get(section, {}):
        sess_key = f"{prefix}{key}"
        if sess_key not in st.session_state:
            st.session_state[sess_key] = secrets[section][key]

# ====================== COLORED BUTTON FUNCTION ======================
def create_colored_button(tick: str, label: str, strength: int):
    key = f"btn_{label.lower().replace(' ', '_')}_{tick}"
    return st.button(f"{tick}\n{label}\n{strength}/9", key=key, use_container_width=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("📈 Live Market Data")
    if st.button("🔄 Force Refresh Now (All Data)", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Auto-refresh every 10s during market hours only")
    st.subheader("Major Indices")
    for sym, name in zip(["^DJI", "^IXIC", "^GSPC"], ["Dow", "Nasdaq", "S&P 500"]):
        try:
            data = get_history(sym, "2d")
            if len(data) > 1:
                price = data['Close'].iloc[-1]
                chg = (price - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100
                st.metric(name, f"{price:,.0f}", f"{chg:+.2f}%")
        except:
            st.metric(name, "—")
    st.divider()
    st.subheader("Your Tickers")
    for tick in TICKERS:
        try:
            data = get_history(tick, "5d")
            if len(data) > 1:
                price = data['Close'].iloc[-1]
                chg = (price - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100
                st.metric(tick, f"${price:,.2f}", f"{chg:+.1f}%")
        except:
            st.metric(tick, "—")
    st.divider()
    st.subheader("Key Underlyings")
    for u in KEY_UNDERLYINGS:
        try:
            price = get_history(u, "1d")['Close'].iloc[-1]
            st.metric(u, f"${price:,.2f}")
        except:
            st.metric(u, "—")
    st.divider()
    now_et = datetime.now(ZoneInfo("America/New_York"))
    st.caption(f"🔄 Last refreshed: {now_et.strftime('%H:%M:%S ET')}")

    st.subheader("Strategy Settings")
    strategy_mode = st.selectbox("Strategy Mode", ["Balanced (more opportunities)", "Strict (higher win rate)"], index=0)
    is_strict = strategy_mode.startswith("Strict")

    st.subheader("📲 Telegram Alerts")
    tg_token = st.text_input("Telegram Bot Token", type="password", value=st.session_state.get("telegram_token", ""))
    tg_chat = st.text_input("Chat ID", value=st.session_state.get("telegram_chat_id", ""))
    st.caption("Get from @BotFather and @userinfobot")
    if tg_token and tg_chat:
        st.session_state.telegram_token = tg_token
        st.session_state.telegram_chat_id = tg_chat
        st.success("✅ Telegram saved")
    if st.button("🔵 Send Test Telegram Now"):
        try:
            bot = TeleBot(st.session_state.telegram_token)
            bot.send_message(st.session_state.telegram_chat_id, "✅ TEST SUCCESSFUL! Day Trade Monitor is ready 🚀")
            st.success("✅ Test sent!")
        except Exception as e:
            st.error(f"Test failed: {str(e)[:80]}")

# ====================== TITLE + REGIME + HEAT-MAP + ACCOUNT ======================
st.title("Day Trade Monitor")
st.caption("High Risk / High Reward – Rules only, no emotion")

qqq_today = get_history("QQQ", "2d")
qqq_chg = (qqq_today['Close'].iloc[-1] - qqq_today['Close'].iloc[-2]) / qqq_today['Close'].iloc[-2] * 100 if len(qqq_today) > 1 else 0
if qqq_chg > 0.8:
    regime = "🟢 Bullish Day – Trade Aggressively"
elif qqq_chg > -0.8:
    regime = "🟡 Neutral Day – Stick to Strong Buys"
else:
    regime = "🔴 Choppy/Bearish Day – Caution Advised"
st.markdown(f"<h3 style='text-align:center; background:#1e3a8a; color:white; padding:14px; border-radius:12px; margin-bottom:12px;'>{regime} (QQQ {qqq_chg:+.1f}%)</h3>", unsafe_allow_html=True)

# ====================== TELEGRAM GUIDE + HEAT-MAP + ACCOUNT ======================
st.markdown("### 👨‍👩‍👧‍👦 Welcome to Day Trade Monitor – Family Edition")
with st.expander("🆕 New to Telegram? Full Setup Guide (3 minutes)", expanded=False):
    st.markdown("""**Step-by-step (do this once):** ... (your full guide text here) ...""")
    st.success("✅ Setup complete — you’re ready for alerts!")

st.subheader("📈 Live Heat-Map – All 14 Tickers")
heat_cols = st.columns(7)
for i, tick in enumerate(TICKERS):
    try:
        data = get_history(tick, "2d")
        price = data['Close'].iloc[-1]
        chg = (price - data['Close'].iloc[-2]) / data['Close'].iloc[-2] * 100
        color = "#15803d" if chg > 0 else "#b91c1c"
        with heat_cols[i % 7]:
            st.markdown(f"""
            <div style="background:{color}; color:white; padding:10px; border-radius:10px; text-align:center; margin-bottom:8px;">
                <b>{tick}</b><br>${price:,.2f}<br><span style="font-size:1.1em;">{chg:+.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
    except:
        with heat_cols[i % 7]:
            st.markdown(f"""
            <div style="background:#374151; color:white; padding:10px; border-radius:10px; text-align:center; margin-bottom:8px;">
                <b>{tick}</b><br>—<br>—
            </div>
            """, unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    account_size = st.number_input("Trading Account Size $", value=DEFAULT_ACCOUNT_SIZE, step=10000.0)
with col2:
    risk_pct = st.selectbox("Risk per Trade", ["0.5%", "1.0%", "1.5%", "2.0%", "3.0%"], index=1)
base_risk_dollars = account_size * float(risk_pct.strip("%")) / 100
st.caption(f"**Base Max Loss (fixed risk):** ${base_risk_dollars:,.0f} ({risk_pct})")

refresh_col, auto_col = st.columns([1, 3])
with refresh_col:
    if st.button("🔄 Refresh All Data", type="primary", width="stretch"):
        st.rerun()
with auto_col:
    auto_refresh = st.checkbox("Auto-refresh market data every 10 seconds", value=True, key="auto_refresh_checkbox")

# ====================== SIGNALS ======================
st.subheader("🚀 Trade Signals")
ticker_data_list = []
qqq_hist = get_history("QQQ", "5d")
qqq_open = qqq_hist['Open'].iloc[-1] if not qqq_hist.empty else 0
qqq_curr = qqq_hist['Close'].iloc[-1] if not qqq_hist.empty else 0
qqq_chg_from_open = (qqq_curr - qqq_open) / qqq_open * 100 if qqq_open != 0 else 0

for tick in TICKERS:
    try:
        hist = get_history(tick, "5d")
        if hist.empty: continue
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1]
        curr = hist['Close'].iloc[-1]
        today_open = hist['Open'].iloc[-1]
        chg_from_open = (curr - today_open) / today_open * 100
        prev_vol = hist['Volume'].iloc[-2] if len(hist) > 1 else 0
        curr_vol = hist['Volume'].iloc[-1]
        vol_ok = curr_vol > prev_vol * (1.5 if not is_strict else 1.8)
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean().abs()
        loss_safe = loss.replace(0, 1e-10)
        rs = gain / loss_safe
        rsi = max(0, min(100, 100 - (100 / (1 + rs)).iloc[-1]))
        rsi_ok = rsi < (78 if not is_strict else 75)
        ema50 = hist['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = hist['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
        bull = ema50 > ema200
        ema9 = hist['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
        near_9ema = abs(curr - ema9) / ema9 < (0.02 if not is_strict else 0.015)
        now_et_time = datetime.now(ZoneInfo("America/New_York")).time()
        time_ok = dt_time(9, 30) <= now_et_time <= dt_time(12, 0) if not is_strict else dt_time(9, 45) <= now_et_time <= dt_time(11, 30)
        ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
        ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1]
        hist_positive = macd_hist.iloc[-1] > 0
        hist_rising = macd_hist.iloc[-1] > macd_hist.iloc[-2] if len(macd_hist) > 1 else False
        histogram_ok = hist_positive and (hist_rising if is_strict else True)
        rel_strength_ok = chg_from_open > qqq_chg_from_open - 0.5
        conditions_met = sum([bull, vol_ok, rsi_ok, chg_from_open < (4.5 if not is_strict else 3),
                              near_9ema, time_ok, macd_bullish, histogram_ok, rel_strength_ok])
        if conditions_met >= 9:
            label = "STRONG BUY"
        elif conditions_met >= 7 and time_ok:
            label = "BUY"
        elif chg_from_open > 6 or rsi > 82:
            label = "SIT"
        else:
            label = "SHORT"
        ticker_data_list.append({
            "Ticker": tick,
            "Price": round(curr, 2),
            "Chg %": round(chg_from_open, 1),
            "Strength": conditions_met,
            "Signal": label,
            "Data": {
                "curr": curr, "prev": prev_close, "chg_from_open": chg_from_open,
                "rsi": rsi, "bull": bull, "vol_ok": vol_ok, "near_9ema": near_9ema,
                "time_ok": time_ok, "macd_bullish": macd_bullish, "histogram_ok": histogram_ok,
                "rel_strength_ok": rel_strength_ok, "label": label, "strength": conditions_met
            }
        })
    except:
        pass

# ====================== FORCE COLORED BUTTON CSS (placed BEFORE buttons) ======================
color_css = "<style>"
for row in ticker_data_list:
    tick = row["Ticker"]
    label = row["Signal"]
    key = f"btn_{label.lower().replace(' ', '_')}_{tick}"
    if "STRONG BUY" in label:
        bg = "#0f5132"   # Dark green
    elif "BUY" in label:
        bg = "#166534"   # Green
    elif label == "SIT":
        bg = "#854d0e"   # Orange
    else:
        bg = "#991b1b"   # Red
    color_css += f'button[key="{key}"] {{ background-color: {bg} !important; color: white !important; }}\n'
color_css += "</style>"
st.markdown(color_css, unsafe_allow_html=True)

# ====================== COLORED BUTTON GRID ======================
cols = st.columns(7)
for i, row in enumerate(ticker_data_list):
    tick = row["Ticker"]
    label = row["Signal"]
    strength = row["Strength"]
    with cols[i % 7]:
        if create_colored_button(tick, label, strength):
            st.session_state.selected_ticker = tick
            st.session_state.ticker_data = row["Data"]
            st.rerun()

# Handle direct URL click
if 'selected' in st.query_params:
    selected_tick = st.query_params['selected']
    for row in ticker_data_list:
        if row["Ticker"] == selected_tick:
            st.session_state.selected_ticker = selected_tick
            st.session_state.ticker_data = row["Data"]
            st.rerun()
            break

# ====================== REST OF YOUR APP (AUTO ALERTS, TRADE PLAN, BACKTEST, HEAT, NEWS, etc.) ======================
# (All the remaining code from your original script is exactly the same — copy-paste the rest from your previous version here)

# ====================== AUTO ALERTS ======================
now_et = datetime.now(ZoneInfo("America/New_York"))
if dt_time(9, 30) <= now_et.time() <= dt_time(12, 0):
    for row in ticker_data_list:
        if row["Signal"] == "STRONG BUY":
            key = f"last_alert_{row['Ticker']}"
            last = st.session_state.get(key, 0)
            if time.time() - last > 900:
                msg = f"🚀 STRONG BUY {row['Ticker']} @ ${row['Price']} (+{row['Chg %']}%) — {now_et.strftime('%H:%M ET')}"
                if all(k in st.session_state for k in ["twilio_sid","twilio_token","twilio_from","twilio_to"]):
                    try:
                        client = Client(st.session_state.twilio_sid, st.session_state.twilio_token)
                        client.messages.create(body=msg, from_=st.session_state.twilio_from, to=st.session_state.twilio_to)
                    except: pass
                if all(k in st.session_state for k in ["telegram_token","telegram_chat_id"]):
                    try:
                        bot = TeleBot(st.session_state.telegram_token)
                        bot.send_message(st.session_state.telegram_chat_id, msg)
                    except: pass
                st.session_state[key] = time.time()
                st.toast(f"📲 Alert sent for {row['Ticker']}", icon="🚀")

# ====================== TRADE PLAN + DIAGNOSTICS + PERSISTENT BACKTEST ======================
st.markdown("---")
st.subheader("📋 Trade Plan + Diagnostics")
if "selected_ticker" in st.session_state and st.session_state.selected_ticker:
    # (your full trade plan code here — exactly as before)
    # ... (backtest with st.session_state persistence) ...
    pass
else:
    st.info("👆 Click any colored card above to see full trade plan + backtest")

# (Portfolio Heat, News, Rules, Trade Log, Morning Summary, Auto-refresh — copy from your last working version)

# ====================== SMART AUTO-REFRESH ======================
if auto_refresh:
    now_et = datetime.now(ZoneInfo("America/New_York"))
    market_open = dt_time(9, 30) <= now_et.time() <= dt_time(16, 0)
    if market_open:
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()
        if time.time() - st.session_state.last_refresh >= 10:
            st.session_state.last_refresh = time.time()
            st.rerun()
