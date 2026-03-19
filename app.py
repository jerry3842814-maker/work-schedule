import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工排班登記表")

# --- 1. Google 表單設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"    # 日期
ENTRY_SHIFT = "entry.193877192"  # 班別

# 當班別改變時，增加 reset_key 以重置日期選單
def reset_dates():
    st.session_state.reset_key += 1

def submit_to_google_form(name, records):
    success_count = 0
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    for r in records:
        payload = {
            ENTRY_NAME: name,
            ENTRY_DATE: r["date"],
            ENTRY_SHIFT: r["shift"]
        }
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            if res.status_code == 200:
                if "登入" in res.text or "Google 帳戶" in res.text:
                    st.error(f"❌ 提交失敗：表單要求登入。請關閉 Google 表單的「限制填寫一次」。")
                    return -1
                success_count += 1
            else:
                # 這裡如果出現 401，請檢查 Google 表單權限是否設為「公開」
                st.error(f"❌ 日期 {r['date']} 失敗，代碼：{res.status_code}")
        except Exception as e:
            st.error(f"❌ 網路錯誤：{e}")
    return success_count

# --- 2. 初始化 ---
if "records" not in st.session_state:
    st.session_state.records = []
if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# --- 3. 介面設計 ---

# 為姓名選單加上 key，讓它能隨 reset_key 重置
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名", 
    staff_list, 
    key=f"name_select_{st.session_state.reset_key}"
)

# 第 2 步：選擇班別
selected_shift = st.radio(
    "⏰ 2. 選擇班別", 
    ["早", "晚", "休"], 
    horizontal=True, 
    on_change=reset_dates,
    key=f"shift_radio_{st.session_state.reset_key}"
)

# 第 3 步：選擇日期
today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

# 這裡也加上 key 確保連動重置
selected_dates = st.multiselect(
    "🗓️ 3. 選擇日期 (選好班別再選日期)", 
    options=date_options, 
    key=f"date_selector_{st.session_state.reset_key}"
)

if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇":
        st.error("⚠️ 請先選擇姓名")
    elif not selected_dates:
        st.warning("⚠️ 請選擇日期")
    else:
        st.session_state.submitted = False
        for d in selected_dates:
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"已加入預覽：{len(selected_dates)} 筆 ({selected_shift}班)")

st.write("---")

# --- 4. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清除預覽與日期", use_container_width=True):
            st.session_state.records = []
            st.session_state.reset_key += 1
            st.session_state.submitted = False
            st.rerun() 
            
    with col2:
        if st.button("🚀 確認提交到雲端", type="primary", use_container_width=True):
            if name == "請選擇":
                st.error("❌ 請選擇姓名")
            else:
                with st.spinner('正在提交資料...'):
                    count = submit_to_google_form(name, st.session_state.records)
                    if count == len(st.session_state.records):
                        st.session_state.submitted = True
                        st.balloons()
                    elif count > 0:
                        st.warning(f"⚠️ 僅成功提交 {count} 筆。")

if st.session_state.submitted:
    st.success(f"✅ 成功提交！資料已同步至雲端。")
    if st.button("✨ 點我清空內容", use_container_width=True):
        # 核心重置邏輯：清空紀錄並更新 reset_key
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.submitted = False
        st.rerun()
