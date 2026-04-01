import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="大師加持開發版", layout="wide")

# ------------------------
# 🌙 深色主題 + 卡片樣式
# ------------------------
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e1117;
    color: #e6edf3;
}

/* 卡片 */
.card {
    background: #161b22;
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    margin-bottom: 20px;
}

/* 標題 */
.card-title {
    font-size: 20px;
    font-weight: bold;
}

/* 價格 */
.price {
    font-size: 28px;
    font-weight: bold;
}

/* 上漲 */
.up {
    color: #ff4d4f;
}

/* 下跌 */
.down {
    color: #52c41a;
}

/* badge */
.badge {
    padding: 6px 10px;
    border-radius: 10px;
    font-size: 12px;
    display: inline-block;
    margin-right: 6px;
}

/* 技術指標 */
.kd {
    background-color: #1f6feb;
}
.momentum {
    background-color: #d29922;
}
.signal {
    background-color: #8957e5;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 大師加持（開發版 v2 UI升級）")

stocks = [
    {"id": "2330", "name": "台積電"},
    {"id": "2002", "name": "中鋼"},
    {"id": "1326", "name": "台化"},
    {"id": "6505", "name": "台塑化"}
]

# ------------------------
# TWSE 即時資料
# ------------------------
def fetch_twse():
    ex_ch = "|".join([f"tse_{s['id']}.tw" for s in stocks])
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://mis.twse.com.tw/"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("msgArray", [])
    except:
        return []


# ------------------------
# yfinance 歷史資料
# ------------------------
def fetch_yf_hist(stock_id):
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="3mo")
        if df.empty:
            return None
        return df
    except:
        return None


# ------------------------
# KD
# ------------------------
def calculate_kd(df, period=9):
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()

    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(com=2).mean()
    df['D'] = df['K'].ewm(com=2).mean()

    return df


# ------------------------
# 動能
# ------------------------
def calculate_momentum(df, period=10):
    df['Momentum'] = df['Close'] - df['Close'].shift(period)
    return df


# ------------------------
# 訊號判斷
# ------------------------
def analyze_signal(df):
    if len(df) < 2:
        return "資料不足", "無法判斷"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signal = "觀望"

    if prev['K'] < prev['D'] and latest['K'] > latest['D']:
        signal = "📈 買進（黃金交叉）"
    elif prev['K'] > prev['D'] and latest['K'] < latest['D']:
        signal = "📉 賣出（死亡交叉）"

    trend = "🔥 上升動能" if latest['Momentum'] > 0 else "❄️ 下跌動能"

    return signal, trend


# ------------------------
# 整合單一股票資料
# ------------------------
def get_stock_data(twse_data, stock):
    code = stock["id"]
    name = stock["name"]

    tw = next((x for x in twse_data if x["c"] == code), None)

    df = fetch_yf_hist(code)

    if df is not None and len(df) >= 2:
        prev_close = df["Close"].iloc[-2]
        open_price = df["Open"].iloc[-1]
        high = df["High"].iloc[-1]
        low = df["Low"].iloc[-1]
        yf_close = df["Close"].iloc[-1]
    else:
        prev_close = open_price = high = low = yf_close = None

    # 即時價優先 TWSE
    if tw:
        z = tw.get("z")
        if z not in ["-", "", None]:
            price = float(z)
        else:
            price = yf_close
    else:
        price = yf_close

    # fallback
    if prev_close is None and tw:
        try:
            prev_close = float(tw.get("y") or 0)
        except:
            prev_close = 0

    # 技術指標
    if df is not None:
        df = calculate_kd(df)
        df = calculate_momentum(df)
        signal, trend = analyze_signal(df)

        latest = df.iloc[-1]
        k = latest["K"]
        d = latest["D"]
        momentum = latest["Momentum"]
    else:
        signal = trend = "無資料"
        k = d = momentum = None

    change = price - prev_close if prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0

    return {
        "name": name,
        "code": code,
        "price": price,
        "prev_close": prev_close,
        "open": open_price,
        "high": high,
        "low": low,
        "change": change,
        "change_pct": change_pct,
        "K": k,
        "D": d,
        "Momentum": momentum,
        "signal": signal,
        "trend": trend
    }


# ------------------------
# 主流程
# ------------------------
twse_data = fetch_twse()

rows = []
for s in stocks:
    rows.append(get_stock_data(twse_data, s))

df = pd.DataFrame(rows)

# ------------------------
# 📊 卡片 UI（報價）
# ------------------------
st.subheader("📊 即時報價")

cols = st.columns(2)

for i, row in df.iterrows():
    col = cols[i % 2]

    change_class = "up" if row["change"] > 0 else "down"

    with col:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">
                {row['name']} ({row['code']})
            </div>

            <div class="price {change_class}">
                {row['price']:.2f}
            </div>

            <div class="{change_class}">
                {row['change']:.2f} ({row['change_pct']:.2f}%)
            </div>

            <hr>

            📌 開盤：{row['open']}　
            最高：{row['high']}　
            最低：{row['low']}

        </div>
        """, unsafe_allow_html=True)

# ------------------------
# 📈 技術分析卡片
# ------------------------
st.subheader("📈 技術分析")

for _, row in df.iterrows():

    change_class = "up" if row["change"] > 0 else "down"

    k_val = f"{row['K']:.2f}" if row["K"] is not None else "-"
    d_val = f"{row['D']:.2f}" if row["D"] is not None else "-"
    m_val = f"{row['Momentum']:.2f}" if row["Momentum"] is not None else "-"

    st.markdown(f"""
    <div class="card">
        <div class="card-title">
            {row['name']} ({row['code']})
        </div>

        <div>
            <span class="badge kd">K: {k_val}</span>
            <span class="badge kd">D: {d_val}</span>
            <span class="badge momentum">動能: {m_val}</span>
        </div>

        <br>

        <div class="badge signal">
            {row['signal']}
        </div>

        <div style="margin-top:10px;" class="{change_class}">
            {row['trend']}
        </div>

    </div>
    """, unsafe_allow_html=True)

# ------------------------
# 更新時間
# ------------------------
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.markdown(f"""
<div style="text-align:right; color:gray;">
🕒 更新時間：{now}
</div>
""", unsafe_allow_html=True)

# ------------------------
# 自動刷新
# ------------------------
time.sleep(15)
st.rerun()