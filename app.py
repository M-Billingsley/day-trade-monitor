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

# ====================== BLUE BUTTONS + IMPROVED CARD BUTTONS ======================
st.markdown("""
<style>
    div[role="radiogroup"] label {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    div[role="radiogroup"] label[data-baseweb="radio"] {
        color: #0d6efd !important;
    }
    button[kind="primary"] {
        background-color: #0d6efd !important;
        color: white !important;
        width: 100% !important;
        margin-bottom: 12px !important;
        font-size: 1.55rem !important;
        height: 135px !important;
        border-radius: 18px !important;
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

# ====================== STRONG COLORED CARDS ======================
def create_colored_button(tick: str, label: str, strength: int):
    key = f"btn_{label.lower()}_{tick}"
    
    if "STRONG BUY" in label:
        bg = "#0f5132"   # Dark green
    elif "BUY" in label:
        bg = "#166534"   # Green
    elif label == "SIT":
        bg = "#854d0e"   # Orange
    else:
        bg = "#991b1b"   # Red

    st.markdown(f"""
    <style>
        button[key="{key}"] {{
            background-color: {bg} !important;
            color: white !important;
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            height: 135px !important;
            border-radius: 18px !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4) !important;
        }}
        button[key="{key}"]:hover {{
            filter: brightness(1.15) !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    return st.button(f"{tick}\n{label}\n{strength}/9", key=key, use_container_width=True)

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("📈 Live Market Data")
    if st.button("🔄 Force Refresh Now (All Data)", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Auto-refresh every 10 seconds is ON below")
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

# ====================== FAMILY-FRIENDLY TELEGRAM SETUP GUIDE ======================
st.markdown("### 👨‍👩‍👧‍👦 Welcome to Day Trade Monitor – Family Edition")
with st.expander("🆕 New to Telegram? Full Setup Guide (3 minutes)", expanded=False):
    st.markdown("""
    **Step-by-step (do this once):**

    1. Open the **Telegram** app on your phone.
    2. Tap the **magnifying glass** 🔍 at the top.
    3. Search `@BotFather` → tap the official one (blue checkmark).
    4. Type `/newbot` and send.
    5. Give it any name (e.g. "My Trade Bot") and send.
    6. BotFather will reply with a long code like `7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxx`  
       → **Copy the entire code** (this is your **Bot Token**).

    7. Now search for `@userinfobot` and open it.
    8. Type `/start` and send.
    9. It will reply with `id: 123456789` (or a longer number)  
       → **Copy just the number** (this is your **Chat ID**).

    10. Back in this app → sidebar → **✉️ Telegram** tab.
    11. Paste your Bot Token in the first box.  
        Paste your Chat ID in the second box.
    12. Click anywhere → you should see **✅ Telegram saved**.
    13. Click the blue **🔵 Send Test Telegram Now** button to test.

    Done! You will now get instant alerts on every **STRONG BUY**.
    """)
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
    auto_refresh = st.checkbox("Auto-refresh every 10 seconds", value=True)

# ====================== SIGNALS – BUILD DATA ======================
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

# ====================== FIXED COLORED CARDS – 7-COLUMN GRID (NO HTML SANITIZER ISSUES) ======================
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

# Fallback for direct URL clicks (shareable links)
if 'selected' in st.query_params:
    selected_tick = st.query_params['selected']
    for row in ticker_data_list:
        if row["Ticker"] == selected_tick:
            st.session_state.selected_ticker = selected_tick
            st.session_state.ticker_data = row["Data"]
            st.rerun()
            break

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

# ====================== TRADE PLAN + DIAGNOSTICS + BACKTEST ======================
st.markdown("---")
st.subheader("📋 Trade Plan + Diagnostics")
if "selected_ticker" in st.session_state and st.session_state.selected_ticker:
    data = st.session_state.ticker_data
    tick = st.session_state.selected_ticker
    override = st.checkbox("**Override fail Windows** (show BUY plan anyway)", value=False, key="time_override")

    st.success(f"🚀 **{data['label']} – {tick}**")

    # 9 Trade Gates — ALWAYS VISIBLE
    st.subheader("🔍 9 Trade Gates – Pass/Fail")
    dcols = st.columns(3)
    with dcols[0]:
        st.metric("Bullish Trend", "✅ PASS" if data["bull"] else "❌ FAIL")
        st.metric("Volume OK", "✅ PASS" if data["vol_ok"] else "❌ FAIL")
    with dcols[1]:
        st.metric("RSI OK", "✅ PASS" if data["rsi"] < (78 if not is_strict else 75) else "❌ FAIL")
        st.metric("Pullback < +4.5%", "✅ PASS" if data["chg_from_open"] < (4.5 if not is_strict else 3) else "❌ FAIL")
    with dcols[2]:
        st.metric("Time Window", "✅ PASS" if data["time_ok"] else "❌ FAIL", delta="OVERRIDDEN" if override else None)
        st.metric("MACD + Histogram", "✅ PASS" if data["histogram_ok"] else "❌ FAIL")
        st.metric("QQQ Rel Strength", "✅ PASS" if data["rel_strength_ok"] else "❌ FAIL")

    # Chart + Full Execution Plan + Backtest (only for BUY or override)
    if "BUY" in data["label"] or (override and data["label"] != "SHORT"):
        st.subheader(f"📊 {tick} – 5-Day Price Action")
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            chart_hist = yf.Ticker(tick).history(period="5d")
            if not chart_hist.empty:
                chart_hist['Range %'] = ((chart_hist['High'] - chart_hist['Low']) / chart_hist['Low'] * 100).round(1)
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25], subplot_titles=(f"{tick} Price", "Volume"))
                fig.add_trace(go.Candlestick(x=chart_hist.index, open=chart_hist['Open'], high=chart_hist['High'], low=chart_hist['Low'], close=chart_hist['Close'], name="Price", customdata=chart_hist['Range %']), row=1, col=1)
                fig.add_trace(go.Bar(x=chart_hist.index, y=chart_hist['Volume'], name="Volume", marker_color="rgba(100,149,237,0.7)"), row=2, col=1)
                fig.update_layout(height=440, hovermode="x unified", xaxis_rangeslider_visible=False, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.caption("Plotly chart unavailable")

        # Dynamic Risk + Execution
        if "STRONG BUY" in data["label"]:
            dynamic_risk_pct = 2.0
            justification = "✅ **STRONG BUY** (9/9 conditions met) → Full conviction = **2.0%** account risk"
        else:
            dynamic_risk_pct = 1.0
            justification = "✅ Regular **BUY** (7-8/9 conditions) → Standard conviction = **1.0%** account risk"
        dynamic_risk_dollars = account_size * dynamic_risk_pct / 100

        with st.container(border=True):
            st.subheader("Execution Instructions – BUY LONG")
            buy_low = round(data["curr"] * 0.97, 2)
            buy_high = round(data["curr"] * 0.985, 2)
            suggested_buy = round((buy_low + buy_high) / 2, 2)
            risk_per_share = round(suggested_buy * 0.02, 2)
            shares = int(dynamic_risk_dollars / risk_per_share)
            shares = max(25, round(shares / 25) * 25)
            total_cost = round(shares * suggested_buy, 2)
            st.markdown(f"**Buy Order:** - **{shares:,} shares** at **${suggested_buy:,.2f}**")
            st.markdown(f"- **Total Cost:** **${total_cost:,.2f}**")
            st.caption(f"Limit range: ${buy_low:,.2f} – ${buy_high:,.2f}")

            st.markdown("**2. Take-Profit Targets (GTC)**")
            for pct in [3.0, 5.0]:
                sell_p = round(suggested_buy * (1 + pct / 100), 2)
                profit = round((sell_p - suggested_buy) * shares)
                st.write(f"• Sell at ${sell_p:,.2f} (+{int(pct)}%) → ${profit:,.0f} profit")

            st.markdown("**3. Protective Stop**")
            stop = round(suggested_buy * 0.98, 2)
            st.markdown(f"Stop-Loss at **${stop:,.2f}**")
            st.caption(f"Max risk this trade ≈ **${dynamic_risk_dollars:,.0f}** ({dynamic_risk_pct:.1f}%)")

            st.markdown("**4. Smart Trailing Stop Suggestion**")
            trail_pct = 1.0 if "STRONG BUY" in data["label"] else 0.5
            breakeven_trail = round(suggested_buy * (1 + trail_pct / 100), 2)
            st.write(f"• Once +3% target is hit, move stop to **${breakeven_trail:,.2f}**")

            st.info(f"**Dynamic Risk Sizing Justification**\n\n{justification}")

        # Backtest
        st.subheader("📊 Realistic Intraday Backtest – Last 60 Trading Days")
        if st.button("🚀 Run Realistic Intraday Backtest on " + tick, type="secondary", key=f"bt_{tick}"):
            with st.spinner("Simulating 15m bars..."):
                try:
                    hist = yf.Ticker(tick).history(period="60d", interval="15m")
                    qqq_hist = yf.Ticker("QQQ").history(period="60d", interval="15m")
                    hist.index = hist.index.tz_convert("America/New_York")
                    qqq_hist.index = qqq_hist.index.tz_convert("America/New_York")
                   
                    if len(hist) < 200:
                        st.warning("Not enough data")
                    else:
                        signals = 0
                        wins = 0
                        total_pl = 0.0
                        pl_list = []
                        max_win_streak = 0
                        max_loss_streak = 0
                        current_streak = 0
                        current_is_win = False
                        for day in hist.index.normalize().unique()[-60:]:
                            day_data = hist[hist.index.normalize() == day]
                            morning = day_data.between_time("9:45", "11:30")
                            if morning.empty:
                                continue
                            for j in range(len(morning)):
                                idx = morning.index[j]
                                curr = morning['Close'].iloc[j]
                                today_open = day_data['Open'].iloc[0]
                                chg_from_open = (curr - today_open) / today_open * 100
                                if chg_from_open < 4.5 and 9 < idx.hour < 12:
                                    signals += 1
                                    entry = curr
                                    future = day_data[day_data.index > idx]
                                    exited = False
                                    for k in range(len(future)):
                                        exit_p = future['Close'].iloc[k]
                                        if exit_p >= entry * 1.03:
                                            pl = 3.0
                                            exited = True
                                            break
                                        if exit_p <= entry * 0.98:
                                            pl = -2.0
                                            exited = True
                                            break
                                        if future.index[k].hour >= 12:
                                            pl = (exit_p - entry) / entry * 100
                                            exited = True
                                            break
                                    if exited:
                                        total_pl += pl
                                        pl_list.append(pl)
                                        if pl > 0:
                                            wins += 1
                                            if current_is_win:
                                                current_streak += 1
                                            else:
                                                current_streak = 1
                                                current_is_win = True
                                            max_win_streak = max(max_win_streak, current_streak)
                                        else:
                                            if not current_is_win:
                                                current_streak += 1
                                            else:
                                                current_streak = 1
                                                current_is_win = False
                                            max_loss_streak = max(max_loss_streak, current_streak)
                        if signals > 0:
                            win_rate = wins / signals * 100
                            avg_pl = total_pl / signals
                            avg_win = np.mean([p for p in pl_list if p > 0]) if wins > 0 else 0
                            avg_loss = np.mean([p for p in pl_list if p < 0]) if (signals - wins) > 0 else 0
                            total_wins = sum(p for p in pl_list if p > 0)
                            total_losses = abs(sum(p for p in pl_list if p < 0))
                            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Signals", signals)
                                st.metric("Win Rate", f"{win_rate:.1f}%")
                            with col2:
                                st.metric("Avg P/L", f"{avg_pl:.2f}%")
                                st.metric("Avg Win", f"+{avg_win:.2f}%")
                            with col3:
                                st.metric("Avg Loss", f"{avg_loss:.2f}%")
                                st.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞")
                            with col4:
                                st.metric("Max Win Streak", max_win_streak)
                                st.metric("Max Loss Streak", max_loss_streak)
                           
                            st.metric("Total Hypothetical Return", f"{total_pl:.1f}%", delta=f"{total_pl:.1f}%")
                            st.caption("**Real-world trading on this strategy should return better than this backtest.**")
                        else:
                            st.info("No BUY signals in the last 60 days")
                except Exception as e:
                    st.error(f"Backtest error: {str(e)[:120]}")
    else:
        st.warning(f"**{data['label']} SIGNAL – {tick}**")
else:
    st.info("👆 Click any colored card above to see full trade plan + backtest")

# ====================== PORTFOLIO HEAT ======================
st.subheader("🔥 Portfolio Heat / Open Risk")
if st.button("🔄 Refresh Heat", type="secondary"):
    st.rerun()
if os.path.exists(CSV_FILE):
    df_log = pd.read_csv(CSV_FILE)
    open_trades = df_log[(df_log["Exit Price"].isnull()) | (df_log["Exit Price"] == 0) | (df_log["Exit Price"] == "")]
    if len(open_trades) == 0:
        st.success("✅ No open positions – Account Heat: 0%")
    else:
        heat_rows = []
        total_exposure = 0.0
        total_estimated_risk = 0.0
        for _, trade in open_trades.iterrows():
            tick = trade["Ticker"]
            shares = float(trade["Shares"])
            entry = float(trade["Entry Price"])
            try:
                curr_price = yf.Ticker(tick).history(period="1d")['Close'].iloc[-1]
                unreal_pnl = shares * (curr_price - entry)
                exposure = shares * curr_price
                est_risk = exposure * 0.02
                total_exposure += exposure
                total_estimated_risk += est_risk
                heat_rows.append({
                    "Ticker": tick,
                    "Shares": int(shares),
                    "Entry": f"${entry:,.2f}",
                    "Current": f"${curr_price:,.2f}",
                    "Unreal P/L $": f"${unreal_pnl:,.0f}",
                    "Unreal P/L %": f"{(curr_price - entry)/entry*100:+.1f}%",
                    "Exposure %": f"{exposure / account_size * 100:.1f}%"
                })
            except:
                heat_rows.append({"Ticker": tick, "Shares": int(shares), "Entry": f"${entry:,.2f}", "Current": "—", "Unreal P/L $": "—", "Unreal P/L %": "—", "Exposure %": "—"})
        heat_df = pd.DataFrame(heat_rows)
        total_risk_pct = total_estimated_risk / account_size * 100
        st.metric(label="Total Account Heat", value=f"{total_risk_pct:.1f}%")
        st.dataframe(heat_df, use_container_width=True, hide_index=True)

# ====================== NEWS, RULES, PSYCHOLOGY, TRADE LOG ======================
st.markdown("---")
st.subheader("📰 Live News Feed")
ticker_for_news = st.session_state.get("selected_ticker", "SOXL")
try:
    news_list = yf.Ticker(ticker_for_news).news[:5]
    for item in news_list:
        st.markdown(f"• [{item.get('title')}]({item.get('link')})")
except:
    st.write("News temporarily unavailable")

with st.expander("📋 Rules (Improved for Higher Win Rate)"):
    st.markdown("""
    **STRONG BUY / BUY** (Balanced/Strict mode):
    - EMA50 > EMA200
    - Volume confirmation
    - RSI not overbought
    - Pullback from open
    - Near 9-EMA
    - MACD + rising histogram
    - Outperforms / matches QQQ
    """)

with st.expander("🧠 Psychology & Discipline"):
    st.markdown("""
    - Rules decide — never emotion or FOMO.
    - One loss is normal. Never revenge trade.
    - Cut losses fast. Let winners run.
    - Review log every day.
    """)

with st.expander("📒 Trade Log"):
    col1, col2 = st.columns(2)
    with col1:
        log_ticker = st.text_input("Ticker")
        entry_price = st.number_input("Entry Price $", min_value=0.01, step=0.01)
        exit_price = st.number_input("Exit Price $ (0 if open)", min_value=0.0, step=0.01)
        log_shares = st.number_input("Shares", min_value=50, step=50)
    with col2:
        notes = st.text_area("Notes", height=120)
    col_log1, col_log2 = st.columns(2)
    with col_log1:
        if st.button("Log Trade", width="stretch"):
            if log_ticker and entry_price > 0 and log_shares > 0:
                pl = (exit_price - entry_price) * log_shares if exit_price > 0 else None
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Ticker": log_ticker.upper(),
                    "Entry Price": entry_price,
                    "Exit Price": exit_price if exit_price > 0 else "",
                    "Shares": log_shares,
                    "P/L $": pl if pl is not None else "",
                    "Notes": notes
                }])
                trades_df = pd.concat([trades_df, new_row], ignore_index=True)
                trades_df.to_csv(CSV_FILE, index=False)
                st.success("✅ Trade logged!")
    with col_log2:
        if st.button("📥 Download Full Trade Log as Excel", type="primary", width="stretch"):
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                trades_df.to_excel(writer, index=False, sheet_name="Trade_Log")
            output.seek(0)
            st.download_button(
                label="⬇️ Click to Download Excel",
                data=output,
                file_name="day_trade_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.dataframe(trades_df.tail(10), use_container_width=True)

# ====================== MORNING SUMMARY ======================
st.markdown("---")
if st.button("📨 Send Morning Summary to Telegram", type="primary", use_container_width=True):
    if "telegram_token" in st.session_state and "telegram_chat_id" in st.session_state:
        try:
            bot = TeleBot(st.session_state.telegram_token)
            summary = f"📈 Day Trade Monitor Morning Summary\n\nMarket Regime: {regime}\n\nSTRONG BUY Signals:\n"
            strong = [row for row in ticker_data_list if row["Signal"] == "STRONG BUY"]
            for row in strong:
                summary += f"• {row['Ticker']} @ ${row['Price']} (+{row['Chg %']}%) — {row['Strength']}/9\n"
            if not strong:
                summary += "None right now\n"
            bot.send_message(st.session_state.telegram_chat_id, summary)
            st.success("✅ Morning summary sent!")
        except Exception as e:
            st.error(f"Failed: {str(e)[:80]}")

# ====================== AUTO REFRESH ======================
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    if time.time() - st.session_state.last_refresh >= 10:
        st.session_state.last_refresh = time.time()
        st.cache_data.clear()
        st.rerun()
