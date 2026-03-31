import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

st.set_page_config(page_title="即時台股股價", layout="wide")
st.title("📈 即時台股股價（技術分析版）")

stocks = [
    {"id": "2330", "name": "台積電"},
    {"id": "2002", "name": "中鋼"},
    {"id": "1326", "name": "台化"},
    {"id": "6505", "name": "台塑化"}
]

# ------------------------
# TWSE API（主來源）
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
        return None


# ------------------------
# yfinance（備援）
# ------------------------
def fetch_yfinance():
    result = []

    for s in stocks:
        ticker = yf.Ticker(f"{s['id']}.TW")
        hist = ticker.history(period="1d")

        if not hist.empty:
            price = hist["Close"].iloc[-1]
            result.append({
                "c": s["id"],
                "n": s["name"],
                "z": price,
                "y": price,
                "v": 0
            })

    return result


# ------------------------
# 技術指標：KD
# ------------------------
def calculate_kd(df, period=9):
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()

    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(com=2).mean()
    df['D'] = df['K'].ewm(com=2).mean()

    return df


# ------------------------
# 技術指標：Momentum
# ------------------------
def calculate_momentum(df, period=10):
    df['Momentum'] = df['Close'] - df['Close'].shift(period)
    return df


# ------------------------
# 訊號分析
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

    momentum = latest['Momentum']

    if momentum > 0:
        trend = "🔥 上升動能"
    else:
        trend = "❄️ 下跌動能"

    return signal, trend


# ------------------------
# 取得 KD 用資料
# ------------------------
def get_kd_data(stock_id):
    ticker = yf.Ticker(f"{stock_id}.TW")
    df = ticker.history(period="3mo")

    if df.empty:
        return None

    df = calculate_kd(df)
    df = calculate_momentum(df)

    return df


# ------------------------
# 整合資料來源
# ------------------------
def get_data():
    data = fetch_twse()

    if data:
        return data, "TWSE"

    data = fetch_yfinance()
    return data, "yfinance"


# ------------------------
# UI 顯示
# ------------------------
data, source = get_data()

if data:
    rows = []

    for stock in data:
        code = stock["c"]
        name = stock["n"]

        price_raw = stock.get("z")
        prev = float(stock.get("y") or 0)

        if price_raw in ["-", "", None]:
            price = prev
            is_closed = True
        else:
            price = float(price_raw)
            is_closed = False

        change = price - prev
        change_pct = (change / prev * 100) if prev else 0

        rows.append({
            "股票": name,
            "代碼": code,
            "價格": f"{price:.2f}" + (" (收盤)" if is_closed else ""),
            "昨收": f"{prev:.2f}",
            "漲跌": f"{change:+.2f}",
            "漲跌幅": f"{change_pct:+.2f}%"
        })

    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.divider()

    # -------- 技術分析區 --------
    st.subheader("📊 技術分析（KD + 動能）")

    for s in stocks:
        df_kd = get_kd_data(s["id"])

        if df_kd is not None:
            signal, trend = analyze_signal(df_kd)
            latest = df_kd.iloc[-1]

            st.write(f"### {s['name']} ({s['id']})")
            st.write(f"K值：{latest['K']:.2f} ｜ D值：{latest['D']:.2f}")
            st.write(f"動能：{latest['Momentum']:.2f}")
            st.write(f"訊號：{signal} ｜ {trend}")
            st.divider()
        else:
            st.write(f"{s['name']} 無法取得技術資料")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"資料來源：{source} ｜ 更新時間：{now}")

else:
    st.error("❌ 無法取得資料（TWSE + yfinance 都失敗）")


# 自動刷新
time.sleep(15)
st.rerun()