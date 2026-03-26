import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered", page_icon="📅")
st.title("📅 員工預班登記表")

# --- 1. 外部連結設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"
ENTRY_NAME = "entry.2117462394"   
ENTRY_DATE = "entry.1676285197"   
ENTRY_SHIFT = "entry.193877192"  
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

# --- 2. 核心功能函數 ---
def get_cloud_data():
    try:
        df = pd.read_csv(f"{SHEET_CSV_URL}&t={datetime.now().timestamp()}")
        df.columns = [c.strip() for c in df.columns]
        possible_date_cols = ['日期', 'Date', '時間戳記', 'Timestamp']
        date_col = next((c for c in possible_date_cols if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
            df = df.rename(columns={date_col: '日期'})
        return df
    except:
        return pd.DataFrame()

def submit_to_google_form(name, records):
    success_count = 0
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    for r in records:
        payload = {ENTRY_NAME: name, ENTRY_DATE: r["date"], ENTRY_SHIFT: r["shift"]}
        try:
            res = requests.post(FORM_URL, data=payload, headers=headers)
            if res.status_code == 200: success_count += 1
        except: pass
    return success_count

# --- 3. 初始化 Session State ---
if "records" not in st.session_state: st.session_state.records = []
if "reset_key" not in st.session_state: st.session_state.reset_key = 0
if "submitted" not in st.session_state: st.session_state.submitted = False
if "global_reset_key" not in st.session_state: st.session_state.global_reset_key = 0

# --- 4. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 選擇姓名", staff_list, key=f"name_{st.session_state.global_reset_key}")
selected_shift = st.radio("⏰ 2. 選擇班別", ["早", "晚", "休", "不接組"], horizontal=True)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]
selected_dates = st.multiselect("🗓️ 3. 選擇日期", options=date_options, key=f"dates_{st.session_state.reset_key}")

# --- 5. 加入清單與人數檢查 ---
if st.button("➕ 加入預覽清單", use_container_width=True):
    if name == "請選擇" or not selected_dates:
        st.warning("⚠️ 請填妥姓名與日期")
    else:
        cloud_df = get_cloud_data()
        limit_errors = []
        for d in selected_dates:
            if selected_shift == "休":
                cloud_count = 0
                if not cloud_df.empty and '日期' in cloud_df.columns and '班別' in cloud_df.columns:
                    name_col = '姓名' if '姓名' in cloud_df.columns else cloud_df.columns[1]
                    cloud_count = len(cloud_df[(cloud_df["日期"] == d) & (cloud_df["班別"] == "休") & (cloud_df[name_col] != name)])
                
                # 修正報錯點：改用更穩定的計數方式
                preview_count = sum(1 for r in st.session_state.records if r["date"] == d and r["shift"] == "休")
                
                if (cloud_count + preview_count) >= 3:
                    limit_errors.append(d)
                    continue

            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})

        if limit_errors:
            st.error(f"🚨 休息人數已滿 3 人：{', '.join(limit_errors)}")
        else:
            st.success("已成功加入預覽清單！")
            st.session_state.submitted = False

st.write("---")

# --- 6. 提交區 ---
if st.session_state.records:
    st.subheader("📍 待提交預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.table(df_preview)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空全部", use_container_width=True):
            st.session_state.records = []
            st.rerun()
    with col2:
        if st.button("🚀 確認提交", type="primary", use_container_width=True):
            with st.spinner("提交中..."):
                count = submit_to_google_form(name, st.session_state.records)
                if count > 0:
                    st.session_state.submitted = True
                    st.balloons()
                    st.rerun()

if st.session_state.submitted:
    st.success("✅ 提交完成！")
    if st.button("✨ 填寫下一位"):
        st.session_state.records = []
        st.session_state.submitted = False
        st.session_state.global_reset_key += 1
        st.rerun()

# --- 7. 顯示雲端總表 ---
st.write("---")
st.subheader("📊 雲端登記現況")
all_data = get_cloud_data()
if not all_data.empty and '日期' in all_data.columns:
    try:
        display_df = all_data[all_data['日期'] >= str(today)]
        if '班別' in display_df.columns:
            display_df = display_df.sort_values(by=["日期", "班別"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    except:
        st.info("讀取中...")