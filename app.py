import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #e0f0ff;
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

# 產生未來 60 天的日期選項供多選
today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

# 使用 multiselect 實現一次選多個日期
selected_dates = st.multiselect(
    "🗓️ 2. 請選擇日期 (可多選) *", 
    options=date_options,
    placeholder="點擊選擇一個或多個日期"
)

selected_shift = st.radio("⏰ 3. 選擇以上日期的班別", ["早", "晚", "休"], horizontal=True)

# 加入清單按鈕
if st.button("➕ 將選中日期加入登記清單"):
    if not selected_dates:
        st.warning("⚠️ 請先選擇日期！")
    else:
        for d in selected_dates:
            # 檢查是否有重複日期，有的話覆蓋
            st.session_state.records = [r for r in st.session_state.records if r["date"] != d]
            st.session_state.records.append({"date": d, "shift": selected_shift})
        st.success(f"✅ 已加入 {len(selected_dates)} 筆資料")

st.write("---")

# --- 3. 顯示預覽與處理數據 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    
    # 轉換為 DataFrame 並按日期排序
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    df_preview.columns = ["日期", "班別"]
    
    # 顯示表格
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    col_clear, col_download = st.columns(2)
    with col_clear:
        if st.button("🗑️ 清空重選"):
            st.session_state.records = []
            st.rerun()
            
    st.write("---")
    
    # --- 4. 提交與下載 ---
    if name == "請選擇":
        st.warning("⚠️ 請先選擇姓名方可產生下載檔。")
    else:
        # 準備下載用的 CSV 資料 (utf-8-sig 確保中文不亂碼)
        final_df = pd.DataFrame(st.session_state.records).sort_values("date")
        final_df.insert(0, "姓名", name)
        final_df.insert(0, "登記時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        csv_data = final_df.to_csv(index=False).encode('utf-8-sig')

        st.success(f"✅ 您已登記 {len(st.session_state.records)} 天。")
        st.download_button(
            label="🚀 下載排班登記檔 (並傳回 LINE)",
            data=csv_data,
            file_name=f"{name}_排班登記_{datetime.now().strftime('%m%d')}.csv",
            mime="text/csv",
        )
        st.balloons()
else:
    st.info("💡 請先選擇日期與班別，並點擊「將選中日期加入登記清單」。")

st.caption("提示：您可以分批加入，例如先選 3 天早班加入，再選 2 天休假加入。")
