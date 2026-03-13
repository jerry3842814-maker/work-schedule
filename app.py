import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工排班登記表")

# --- 1. Google 表單設定 ---
# 【核心修正】：網址必須包含 /e/ 並以 /formResponse 結尾
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

ENTRY_NAME = "entry.2117462394"   # 姓名 ID
ENTRY_DATE = "entry.1676285197"    # 日期 ID
ENTRY_SHIFT = "entry.193877192"  # 班別 ID

def submit_to_google_form(name, records):
    success_count = 0
    # 加入 Header 模擬真實瀏覽器，避免被當作機器人阻擋
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for r in records:
        payload = {
            ENTRY_NAME: name,
            ENTRY_DATE: r["date"],
            ENTRY_SHIFT: r["shift"]
        }
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            # Google 表單成功時會回傳 200 或 302
            if res.status_code == 200:
                success_count += 1
            else:
                st.error(f"日期 {r['date']} 提交失敗，代碼：{res.status_code}")
                if res.status_code == 401 or res.status_code == 403:
                    st.warning("💡 請檢查表單是否開啟了『限制組織使用者』或『限制填寫一次』。")
        except Exception as e:
            st.error(f"網路錯誤：{e}")
    return success_count

# --- 2. 初始化 Session State ---
if "records" not in st.session_state:
    st.session_state.records = []
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

# --- 3. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 選擇姓名", staff_list)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

# 透過 key 機制實現連動清除
selected_dates = st.multiselect(
    "🗓️ 2. 選擇日期", 
    options=date_options, 
    key=f"date_selector_{st.session_state.reset_key}"
)

selected_shift = st.radio("⏰ 3. 選擇班別", ["早", "晚", "休"], horizontal=True)

if st.button("➕ 加入預覽清單", use_container_width=True):
    if not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        for d in selected_dates:
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success("已加入預覽")

st.write("---")

# --- 4. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清除預覽與日期", use_container_width=True):
            st.session_state.records = []  # 清除表格資料
            st.session_state.reset_key += 1  # 改變 key 以清空上方日期選擇器
            st.rerun() 
            
    with col2:
        if st.button("🚀 確認提交到雲端", type="primary", use_container_width=True):
            if name == "請選擇":
                st.error("❌ 請選擇姓名")
            else:
                with st.spinner('提交中...'):
                    count = submit_to_google_form(name, st.session_state.records)
                    if count == len(st.session_state.records):
                        st.success(f"✅ 全部 {count} 筆資料已成功提交！")
                        st.session_state.records = []
                        st.session_state.reset_key += 1
                        st.balloons()
                        st.rerun()
