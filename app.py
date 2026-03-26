import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from collections import Counter

# --- 基本設定 ---
st.set_page_config(page_title="員工排班登記系統", layout="centered")

st.title("📅 員工預班登記表")

# --- 1. Google 表單設定 ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb4wjd8regrwdgHkM_FX2urIAGbO807ZjVYQjh-WYQ7NzXXQ/formResponse"

ENTRY_NAME = "entry.2117462394"   # 姓名
ENTRY_DATE = "entry.1676285197"   # 日期
ENTRY_SHIFT = "entry.193877192"   # 班別

# --- 2. Google 試算表 CSV 連結 ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-utk_RXaKqx5Iy6xf3xhN-q9wTdvvLy8iHr2yrUr-VIXyaQVjEZu2_SGXSkh0-EZY5_Zgu298AEEO/pub?gid=1144015050&single=true&output=csv"

# --- 3. 休假上限設定 ---
REST_LIMIT = 3


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
                    st.error("❌ 提交失敗：表單要求登入。請關閉 Google 表單的「限制填寫一次」。")
                    return -1
                success_count += 1
            else:
                st.error(f"❌ 日期 {r['date']} 失敗，代碼：{res.status_code}")
        except Exception as e:
            st.error(f"❌ 網路錯誤：{e}")
    return success_count


@st.cache_data(ttl=60)
def get_cloud_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = [str(c).strip() for c in df.columns]

        if "日期" in df.columns:
            df["日期"] = df["日期"].astype(str).str.strip()
            df = df.sort_values(by="日期", ascending=True)

        if "班別" in df.columns:
            df["班別"] = df["班別"].astype(str).str.strip()

        return df
    except Exception:
        return None


def get_rest_count_from_cloud(df):
    """統計雲端中每一天『休』的人數"""
    if df is None or df.empty:
        return Counter()

    if "日期" not in df.columns or "班別" not in df.columns:
        return Counter()

    rest_df = df[df["班別"] == "休"].copy()
    if rest_df.empty:
        return Counter()

    rest_df["日期"] = rest_df["日期"].astype(str).str.strip()
    return Counter(rest_df["日期"].tolist())


def get_rest_count_from_preview(records):
    """統計目前預覽清單中每一天『休』的人數"""
    return Counter([r["date"] for r in records if r["shift"] == "休"])


def build_simulated_records(current_records, selected_dates, selected_shift):
    """
    模擬這次加入後的預覽結果：
    同一天若已存在舊資料，先移除再加入新班別
    """
    updated_records = [r for r in current_records if r["date"] not in selected_dates]
    for d in selected_dates:
        updated_records.append({"date": d, "shift": selected_shift})
    return updated_records


def check_rest_limit(records_after_update, cloud_df, limit=REST_LIMIT):
    """
    檢查加入/提交後，各日期『休』是否超過上限
    回傳：
    - violating_dates: 超過上限的日期列表
    - detail_list: 顯示細節用
    """
    cloud_counter = get_rest_count_from_cloud(cloud_df)
    preview_counter = get_rest_count_from_preview(records_after_update)

    violating_dates = []
    detail_list = []

    for date, preview_rest_count in preview_counter.items():
        total_rest = cloud_counter.get(date, 0) + preview_rest_count
        if total_rest > limit:
            violating_dates.append(date)
            detail_list.append(
                f"{date}（雲端已 {cloud_counter.get(date, 0)} 人，本次預覽後共 {total_rest} 人）"
            )

    return sorted(violating_dates), detail_list


# --- 4. 初始化 ---
if "records" not in st.session_state:
    st.session_state.records = []

if "reset_key" not in st.session_state:
    st.session_state.reset_key = 0

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "global_reset_key" not in st.session_state:
    st.session_state.global_reset_key = 0


# --- 5. 介面設計 ---
staff_list = ["請選擇", "廖小婷", "洪慧玲", "謝梁惠芳", "周錫雄", "郭建志", "林瑋晟", "吳孟儒", "洪黃宥森", "劉柏宏", "陳嘉華"]
name = st.selectbox(
    "👤 1. 選擇姓名",
    staff_list,
    key=f"name_select_{st.session_state.global_reset_key}"
)

selected_shift = st.radio(
    "⏰ 2. 選擇班別",
    ["早", "晚", "休", "不接組"],
    horizontal=True,
    on_change=reset_dates
)

today = datetime.now().date()
date_options = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(60)]

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
        simulated_records = build_simulated_records(
            st.session_state.records,
            selected_dates,
            selected_shift
        )

        # 只有在登記「休」時才檢查人數上限
        if selected_shift == "休":
            cloud_df = get_cloud_data()

            if cloud_df is not None:
                violating_dates, detail_list = check_rest_limit(simulated_records, cloud_df, REST_LIMIT)

                if violating_dates:
                    st.error(f"⚠️ 以下日期登記『休』後會超過 {REST_LIMIT} 人，無法加入：")
                    for msg in detail_list:
                        st.write(f"- {msg}")
                else:
                    st.session_state.submitted = False
                    st.session_state.records = simulated_records
                    st.success(f"已加入預覽：{len(selected_dates)} 筆 (休班)")
            else:
                # 雲端讀不到時，先允許加入預覽，但提交前會再檢查
                st.session_state.submitted = False
                st.session_state.records = simulated_records
                st.warning("⚠️ 目前無法讀取雲端資料，已先加入預覽；送出前會再次檢查『休』的人數上限。")
        else:
            st.session_state.submitted = False
            st.session_state.records = simulated_records
            st.success(f"已加入預覽：{len(selected_dates)} 筆 ({selected_shift}班)")

st.write("---")

# --- 6. 顯示與提交 ---
if st.session_state.records:
    st.subheader("📍 目前登記預覽")
    df_preview = pd.DataFrame(st.session_state.records).sort_values("date")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)

    # 額外顯示目前預覽中「休」的資訊
    preview_rest_counter = get_rest_count_from_preview(st.session_state.records)
    if preview_rest_counter:
        rest_info = [f"{d}：{c} 人" for d, c in sorted(preview_rest_counter.items())]
        st.caption("目前預覽中的『休』日期：" + "｜".join(rest_info))

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
                # 提交前再次檢查「休」是否超過上限
                has_rest_record = any(r["shift"] == "休" for r in st.session_state.records)

                if has_rest_record:
                    cloud_df = get_cloud_data()

                    if cloud_df is None:
                        st.error("❌ 目前無法讀取雲端資料，無法檢查『休』是否超過 3 人，請稍後再試。")
                    else:
                        violating_dates, detail_list = check_rest_limit(st.session_state.records, cloud_df, REST_LIMIT)

                        if violating_dates:
                            st.error(f"⚠️ 以下日期登記『休』後會超過 {REST_LIMIT} 人，請先修改預覽清單：")
                            for msg in detail_list:
                                st.write(f"- {msg}")
                        else:
                            with st.spinner('正在提交資料...'):
                                count = submit_to_google_form(name, st.session_state.records)
                                if count == len(st.session_state.records):
                                    st.session_state.submitted = True
                                    st.balloons()
                                elif count > 0:
                                    st.warning(f"⚠️ 僅成功提交 {count} 筆。")
                else:
                    with st.spinner('正在提交資料...'):
                        count = submit_to_google_form(name, st.session_state.records)
                        if count == len(st.session_state.records):
                            st.session_state.submitted = True
                            st.balloons()
                        elif count > 0:
                            st.warning(f"⚠️ 僅成功提交 {count} 筆。")

if st.session_state.submitted:
    st.success("✅ 成功提交！資料已同步至雲端。")
    if st.button("✨ 點我清空內容", use_container_width=True):
        st.session_state.records = []
        st.session_state.reset_key += 1
        st.session_state.global_reset_key += 1
        st.session_state.submitted = False
        st.rerun()


# --- 7. 顯示雲端所有人的登記紀錄 ---
st.write("---")
st.subheader("📊 雲端預班總表")

if st.button("🔄 查看登記表"):
    st.cache_data.clear()

all_data = get_cloud_data()

if all_data is not None and not all_data.empty:
    st.dataframe(
        all_data,
        use_container_width=True,
        hide_index=True
    )

    # 顯示哪些日期的「休」已達上限或超過上限
    cloud_rest_counter = get_rest_count_from_cloud(all_data)

    reached_limit_dates = []
    exceeded_limit_dates = []

    for date, count in sorted(cloud_rest_counter.items()):
        if count == REST_LIMIT:
            reached_limit_dates.append(f"{date}（{count}人）")
        elif count > REST_LIMIT:
            exceeded_limit_dates.append(f"{date}（{count}人）")

    if reached_limit_dates:
        st.warning("⚠️ 以下日期的『休』已達上限：" + "、".join(reached_limit_dates))

    if exceeded_limit_dates:
        st.error("🚨 以下日期的『休』已超過上限：" + "、".join(exceeded_limit_dates))

    # 顯示最後更新時間（台灣時間）
    tw_time = datetime.utcnow() + timedelta(hours=8)
    st.caption(f"最後更新時間 (UTC+8)：{tw_time.strftime('%Y-%m-%d %H:%M:%S')}")

else:
    st.info("目前雲端尚無資料，或尚未發佈到網路。")
