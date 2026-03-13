import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工排班登記表")

# --- 1. Google 表單設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

# ⚠️ 請再次核對：日期和班別的 ID 是否相反了？（根據你之前的訊息，這兩個 ID 建議再確認一次）
ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"    # 日期
ENTRY_SHIFT = "entry.193877192"  # 班別

def submit_to_google_form(name, records):
    success_count = 0
    # 模擬瀏覽器 Headers
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    for r in records:
        payload = {
            ENTRY_NAME: name,
            ENTRY_DATE: r["date"],
            ENTRY_SHIFT: r["shift"]
        }
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            # Google 表單只要有回應且沒報 400/405 等錯誤，通常會是 200
            if res.status_code == 200:
                # 額外檢查：如果回應內容包含 "登入" 或 "必須"，代表權限沒開
                if "登入" in res.text or "Google 帳戶" in res.text:
                    st.error(f"❌ 提交失敗：表單要求登入。請在 Google 表單設定中關閉「限制填寫一次」。")
                    return -1
                success_count += 1
            else:
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
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 選擇姓名", staff_list)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

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
        st.session_state.submitted = False # 重置提交狀態
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
                    elif count == -1:
                        pass # 權限錯誤已在函數內報錯
                    elif count > 0:
                        st.warning(f"⚠️ 僅成功提交 {count} 筆。")

# --- 5. 提交成功後的顯示 (放在主層級確保不消失) ---
if st.session_state.submitted:
    st.success(f"✅ 成功提交！資料已同步至雲端。")
    if st.button("✨ 點我清空內容", use_container_width=True):
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.submitted = False
        st.rerun()
