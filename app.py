import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="員工排班登記", layout="centered")
st.title("📅 員工休假/班別登記表 (Google Sheet 版)")

# --- 1. 初始化 Google Sheets 連線 ---
# 注意：試算表網址請填入你剛才複製的那一個
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1b-qtjYq0ABkYZc4mk0qbbqqy9hGD5BDeTQU1FDEF6Qs/edit?gid=0#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_google_sheets(name, records):
    # 1. 讀取現有資料
    try:
        existing_df = conn.read(spreadsheet=SPREADSHEET_URL)
    except:
        existing_df = pd.DataFrame(columns=["登記時間", "姓名", "班別", "日期"])
    
    # 2. 準備新資料
    new_data = []
    for r in records:
        new_data.append({
            "登記時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "姓名": name,
            "班別": r["shift"],
            "日期": r["date"]
        })
    new_df = pd.DataFrame(new_data)
    
    # 3. 合併並寫回
    final_df = pd.concat([existing_df, new_df], ignore_index=True)
    conn.update(spreadsheet=SPREADSHEET_URL, data=final_df)
    return True

# --- 2. 初始化 Session State ---
if "records" not in st.session_state:
    st.session_state.records = []

# --- 3. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("1. 選擇姓名 *", staff_list)

col1, col2 = st.columns(2)
with col1:
    selected_date = st.date_input("2. 選擇日期", datetime.now())
with col2:
    selected_shift = st.radio("3. 選擇班別", ["早", "晚", "休"], horizontal=True)

if st.button("➕ 加入清單", use_container_width=True):
    date_str = selected_date.strftime("%Y-%m-%d")
    # 檢查是否重複，重複則覆蓋
    st.session_state.records = [r for r in st.session_state.records if r["date"] != date_str]
    st.session_state.records.append({"date": date_str, "shift": selected_shift})
    st.success(f"已加入預覽：{date_str} ({selected_shift})")

st.write("---")

# --- 4. 顯示與提交 ---
if st.session_state.records:
    st.write("### 📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.table(df_preview)
    
    if st.button("🗑️ 清空重選"):
        st.session_state.records = []
        st.rerun()
    
    st.write("---")
    
    if st.button("🚀 確認提交到雲端試算表", use_container_width=True, type="primary"):
        if name == "請選擇":
            st.error("❌ 請先選擇姓名！")
        else:
            with st.spinner('正在上傳資料...'):
                success = save_to_google_sheets(name, st.session_state.records)
            if success:
                st.success("✅ 登記成功！資料已同步至 Google 試算表")
                st.session_state.records = []
                st.balloons()
