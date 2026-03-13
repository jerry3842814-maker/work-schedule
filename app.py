import streamlit as st
import pandas as pd
from datetime import datetime

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

# 加入自定義 CSS 讓按鈕在手機上更好點擊
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 3.5em;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
    }
    .stSelectbox, .stRadio {
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📅 員工休假/班別登記表")

# --- 1. 初始化 Session State ---
if "records" not in st.session_state:
    st.session_state.records = []

# --- 2. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox("👤 1. 請選擇您的姓名 *", staff_list)

st.write("---")

col1, col2 = st.columns([1, 1])
with col1:
    selected_date = st.date_input("🗓️ 2. 選擇日期", datetime.now())
with col2:
    selected_shift = st.radio("⏰ 3. 選擇班別", ["早", "晚", "休"], horizontal=True)

# 加入清單按鈕
if st.button("➕ 加入登記清單"):
    date_str = selected_date.strftime("%Y-%m-%d")
    # 檢查是否有重複日期，有的話先移除舊的再加入新的 (覆蓋)
    st.session_state.records = [r for r in st.session_state.records if r["date"] != date_str]
    st.session_state.records.append({"date": date_str, "shift": selected_shift})
    st.toast(f"已加入：{date_str} ({selected_shift})")

st.write("---")

# --- 3. 顯示預覽與處理數據 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    
    # 轉換為 DataFrame 並排序
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    df_preview.columns = ["日期", "班別"]
    
    # 在手機上顯示表格
    st.table(df_preview)
    
    if st.button("🗑️ 清空重選"):
        st.session_state.records = []
        st.rerun()
    
    st.write("---")
    
    # --- 4. 提交與下載 ---
    # 準備下載用的 CSV 資料 (utf-8-sig 確保中文不亂碼)
    final_df = pd.DataFrame(st.session_state.records)
    final_df.insert(0, "姓名", name)
    final_df.insert(0, "登記時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    csv_data = final_df.to_csv(index=False).encode('utf-8-sig')

    if name == "請選擇":
        st.warning("⚠️ 請先在上方「選擇姓名」才能下載提交。")
    else:
        st.success("✅ 登記完成！請點擊下方按鈕下載，並傳回 LINE 群組。")
        st.download_button(
            label="🚀 下載排班登記檔 (並傳回 LINE)",
            data=csv_data,
            file_name=f"{name}_排班登記_{datetime.now().strftime('%m%d')}.csv",
            mime="text/csv",
        )
        st.balloons()
else:
    st.info("💡 請先選擇日期與班別，並點擊「加入登記清單」。")

st.caption("版本：1.0 | 穩定版 (免金鑰)")
