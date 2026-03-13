import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 3.5em; font-size: 18px; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📅 員工排班登記表 (Google 表單連線版)")

# --- 1. Google 表單設定 (請務必修改此處) ---
# 將下方 ID 換成你從「預先填妥連結」中取得的數字
FORM_ID = "1FAIpQLSe..." # 這是表單網址中的 ID，也可以從 viewform 網址中取得
ENTRY_NAME = "entry.2117462394"  # 姓名的欄位 ID
ENTRY_DATE = "entry.193877192"  # 日期的欄位 ID
ENTRY_SHIFT = "entry.1676285197" # 班別的欄位 ID

# 表單提交網址 (注意結尾是 formResponse)
 base_url = "https://docs.google.com/forms/d/19WRLS2MpUbbexT851UOexI9OXq9Foge0JFj8Dg-SjFg/prefill/formResponse"

def submit_to_google_form(name, records):
    success_count = 0
    for r in records:
        # 建立提交數據
        payload = {
            ENTRY_NAME: name,
            ENTRY_DATE: r["date"],
            ENTRY_SHIFT: r["shift"]
        }
        # 模擬瀏覽器送出
        res = requests.post(FORM_URL, data=payload)
        if res.status_code == 200:
            success_count += 1
    return success_count

# --- 2. 初始化 ---
if "records" not in st.session_state:
    st.session_state.records = []

# --- 3. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 選擇您的姓名 *", staff_list)

st.write("---")

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]
selected_dates = st.multiselect("🗓️ 2. 選擇日期 (可多選) *", options=date_options)
selected_shift = st.radio("⏰ 3. 選擇以上日期的班別", ["早", "晚", "休"], horizontal=True)

if st.button("➕ 加入預覽清單"):
    if not selected_dates:
        st.warning("⚠️ 請先選擇日期")
    else:
        for d in selected_dates:
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"已加入 {len(selected_dates)} 筆資料至預覽")

st.write("---")

# --- 4. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.table(df_preview)
    
    if st.button("🗑️ 清空重選"):
        st.session_state.records = []
        st.rerun()
    
    st.write("---")
    
    if st.button("🚀 確認提交到雲端 (Google 表單)", type="primary"):
        if name == "請選擇":
            st.error("❌ 請先選擇姓名！")
        else:
            with st.spinner('正在上傳資料...'):
                count = submit_to_google_form(name, st.session_state.records)
                if count > 0:
                    st.success(f"✅ 成功提交 {count} 筆資料！請查看 Google 試算表。")
                    st.session_state.records = []
                    st.balloons()
