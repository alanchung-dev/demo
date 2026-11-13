"""
data.py — 資料載入模組
================================
架構：
  - 使用者選擇「團隊」+「季度」
  - 從 Google Sheets Raw Data tab 一次讀取所有列
  - 用 pandas 依日期範圍過濾，套用 METRIC_DEFS 計算各指標
  - 已定義指標 → 即時計算；未定義指標 → fallback SAMPLE 樣本資料
  - @st.cache_data(ttl=300) 每 5 分鐘自動重新整理
"""

import os
import re
from datetime import date
import streamlit as st
from field_map import (
    SHEET_ID, CREDENTIALS_FILE, FIELD_MAP,
    TEAM_NAMES, TEAM_GID_MAP, METRIC_DEFS,
    AVAILABLE_QUARTERS, DEFAULT_QUARTER,
    ROADMAP_GID_MAP, INDEX_GID, ROADMAP_FILE_MAP, ROADMAP_INDEX_GID,
    RAW_TAB_NAME_PATTERNS, RELEASE_GID, FROZEN_QUARTERS,
)

# ── DEMO 展示版：合成假資料（不連任何外部服務）──────────────────────────
try:
    from field_map import MOCK
except ImportError:
    MOCK = False
_mock = None
if MOCK:
    import mock_data as _mock


# ─── 季度工具函式 ─────────────────────────────────────────────────────────────

def quarter_to_dates(q: str) -> tuple[date, date]:
    """
    "2026Q1" → (date(2026,1,1), date(2026,3,31))
    支援 Q1~Q4
    """
    year = int(q[:4])
    qnum = int(q[5])
    month_start = (qnum - 1) * 3 + 1
    month_end   = qnum * 3
    day_end = {1: 31, 2: 30, 3: 30, 4: 31}[qnum]
    return date(year, month_start, 1), date(year, month_end, day_end)


def prev_quarter(q: str) -> str:
    """
    "2026Q1" → "2025Q4"
    "2025Q3" → "2025Q2"
    """
    year, qnum = int(q[:4]), int(q[5])
    if qnum == 1:
        return f"{year - 1}Q4"
    return f"{year}Q{qnum - 1}"


def quarter_label(q: str) -> str:
    """"2026Q1" → "2026 Q1" """
    return f"{q[:4]} {q[4:]}"


# ─── 樣本資料（2026Q1 實際數值，Demo / fallback 用）──────────────────────────
SAMPLE: dict[str, str] = {
    "YEAR": "2026", "QUARTER": "1", "TEAM_NAME": "Data Team",
    "REPORT_DATE": "2026-08-07", "DATA_CUTOFF_DATE": "2026-08-07",

    # 一、發版情形
    "s1_cur_plan_freq": "13",  "s1_cur_normal_freq": "13",
    "s1_cur_hotfix": "0",      "s1_cur_fl_bug": "0",  "s1_cur_fl_feat": "0",
    "s1_prev_plan_freq": "12", "s1_prev_normal_freq": "12",
    "s1_prev_hotfix": "0",     "s1_prev_fl_bug": "0", "s1_prev_fl_feat": "0",
    "s1_cur_rollback": "0",    "s1_cur_delay": "0",
    "s1_prev_rollback": "0",   "s1_prev_delay": "0",
    "s1_obs": "（範例文字：本區為展示版佔位說明）",
    "s1_focus": "（範例文字：本區為展示版佔位說明）",

    # 二、2.1 團隊專項(Roadmap_Item)
    "s21_cur_total_req": "24",  "s21_prev_total_req": "23",
    "s21_req_qoq": "4.35%",    "s21_cur_est_done": "9",
    "s21_cur_act_done": "8", "s21_prev_act_done": "7",
    "s21_cur_act_done_rm": "9", "s21_prev_act_done_rm": "13",
    "s21_cur_est_rate": "100.00%", "s21_prev_est_done": "13",
    "s21_prev_est_rate": "53.85%","s21_cur_addon": "1",
    "s21_prev_addon": "4",      "s21_addon_qoq": "-75.00%",

    # 二、2.2 PM
    "s22_cur_prd_owner": "0",   "s22_cur_prd_support": "0",  "s22_cur_prd_total": "0",
    "s22_prev_prd_owner": "3",  "s22_prev_prd_support": "0", "s22_prev_prd_total": "3",
    "s22_prd_qoq_owner": "-100.00%", "s22_prd_qoq_total": "-100.00%",
    "s22_cur_rev_owner": "1",   "s22_cur_rev_support": "0",  "s22_cur_rev_total": "1",
    "s22_prev_rev_owner": "2",  "s22_prev_rev_support": "0", "s22_prev_rev_total": "2",
    "s22_rev_qoq_owner": "-50.00%",  "s22_rev_qoq_total": "-50.00%",
    "s22_cur_avg_owner": "0.00","s22_cur_avg_support": "0.00","s22_cur_avg_total": "0.00",
    "s22_prev_avg_owner": "1.91","s22_prev_avg_support": "0.00","s22_prev_avg_total": "1.91",
    "s22_avg_qoq_owner": "-100.00%", "s22_avg_qoq_total": "-100.00%",
    "s2_obs": "（範例文字：本區為展示版佔位說明）",
    "s2_focus": "（範例文字：本區為展示版佔位說明）",

    # 二、2.3 UED
    "s23_cur_total": "0",       "s23_cur_prd_cnt": "0",   "s23_cur_prd_rate": "-",
    "s23_cur_dev_cnt": "0",     "s23_cur_dev_rate": "-",
    "s23_prev_total": "2",      "s23_prev_prd_cnt": "2",  "s23_prev_prd_rate": "100.00%",
    "s23_prev_dev_cnt": "2",    "s23_prev_dev_rate": "100.00%",
    "s23_cur_sm_total": "0",    "s23_cur_sm_dev_cnt": "0","s23_cur_sm_dev_rate": "-",
    "s23_prev_sm_total": "1",   "s23_prev_sm_dev_cnt": "1","s23_prev_sm_dev_rate": "100.00%",

    # 二、2.4 研測
    "s24_cur_est_owner": "-",   "s24_cur_est_support": "-","s24_cur_est_total": "9",
    "s24_cur_done_owner": "4",  "s24_cur_done_support": "5","s24_cur_done_total": "9",
    "s24_cur_ratio_owner": "26.67%","s24_cur_ratio_support": "29.41%","s24_cur_ratio_total": "28.13%",
    "s24_cur_target_owner": "-","s24_cur_target_support": "-","s24_cur_target_total": "100.00%",
    "s24_prev_est_owner": "-",  "s24_prev_est_support": "-","s24_prev_est_total": "13",
    "s24_prev_done_owner": "3", "s24_prev_done_support": "4","s24_prev_done_total": "7",
    "s24_prev_ratio_owner": "25.00%","s24_prev_ratio_support": "36.36%","s24_prev_ratio_total": "30.43%",
    "s24_prev_target_owner":"-","s24_prev_target_support":"-","s24_prev_target_total": "53.85%",
    "s23_s24_obs": "（範例文字：本區為展示版佔位說明）",
    "s23_s24_focus": "（範例文字：本區為展示版佔位說明）",

    # 二、2.5 顆粒度
    "s25_cur_eng_dev": "4.89",  "s25_cur_eng_pre": "0.00",  "s25_cur_eng_nc": "2.56",  "s25_cur_eng_total": "7.44",
    "s25_prev_eng_dev": "15.00","s25_prev_eng_pre": "0.00", "s25_prev_eng_nc": "1.36", "s25_prev_eng_total": "16.36",
    "s25_qoq_eng_dev": "-67.41%","s25_qoq_eng_pre": "-",   "s25_qoq_eng_nc": "88.30%","s25_qoq_eng_total": "-54.49%",
    "s25_cur_qa_dev": "0.00",   "s25_cur_qa_pre": "0.00",   "s25_cur_qa_nc": "0.11",   "s25_cur_qa_total": "0.11",
    "s25_prev_qa_dev": "3.86",  "s25_prev_qa_pre": "0.29",  "s25_prev_qa_nc": "0.00",  "s25_prev_qa_total": "4.14",
    "s25_qoq_qa_dev": "-100.00%","s25_qoq_qa_pre": "-100.00%","s25_qoq_qa_nc": "-",    "s25_qoq_qa_total": "-97.32%",

    # 三、上版專項(Roadmap_Item)吞吐量
    "s3_cur_done_owner": "4",   "s3_cur_done_support": "5",  "s3_cur_done_total": "9",
    "s3_cur_ratio_owner": "26.67%","s3_cur_ratio_support": "29.41%","s3_cur_ratio_total": "28.13%",
    "s3_prev_done_owner": "3",  "s3_prev_done_support": "4",  "s3_prev_done_total": "7",
    "s3_prev_ratio_owner": "25.00%","s3_prev_ratio_support":"36.36%","s3_prev_ratio_total":"30.43%",
    "s3_cur_eng_tp_owner": "0.50","s3_cur_eng_tp_support": "0.62","s3_cur_eng_tp_total": "1.12",
    "s3_prev_eng_tp_owner": "0.37","s3_prev_eng_tp_support":"0.50","s3_prev_eng_tp_total":"0.87",
    "s3_qoq_eng_tp_owner": "32.95%","s3_qoq_eng_tp_support":"24.64%","s3_qoq_eng_tp_total":"28.20%",
    "s3_cur_qa_tp_owner": "3.64","s3_cur_qa_tp_support": "4.55","s3_cur_qa_tp_total": "8.18",
    "s3_prev_qa_tp_owner": "3.40","s3_prev_qa_tp_support": "4.53","s3_prev_qa_tp_total": "7.92",
    "s3_qoq_qa_tp_owner": "7.07%","s3_qoq_qa_tp_support": "0.38%","s3_qoq_qa_tp_total": "3.25%",
    **{k: "無" for k in [
        "s3_cur_smk_ot_o","s3_cur_smk_ot_s","s3_cur_smk_ot_t",
        "s3_cur_smk_ot_ro","s3_cur_smk_ot_rs","s3_cur_smk_ot_rt",
        "s3_prev_smk_ot_o","s3_prev_smk_ot_s","s3_prev_smk_ot_t",
        "s3_prev_smk_ot_ro","s3_prev_smk_ot_rs","s3_prev_smk_ot_rt",
        "s3_cur_smk_fp_o","s3_cur_smk_fp_s","s3_cur_smk_fp_t",
        "s3_cur_smk_fp_ro","s3_cur_smk_fp_rs","s3_cur_smk_fp_rt",
        "s3_prev_smk_fp_o","s3_prev_smk_fp_s","s3_prev_smk_fp_t",
        "s3_prev_smk_fp_ro","s3_prev_smk_fp_rs","s3_prev_smk_fp_rt",
    ]},
    "s3_cur_6w_o": "66.67%","s3_cur_6w_s": "25.00%","s3_cur_6w_t": "42.86%",
    "s3_prev_6w_o": "0.00%","s3_prev_6w_s": "33.33%","s3_prev_6w_t": "16.67%",
    "s3_diff_6w_o": "66.67%","s3_diff_6w_s": "-8.33%","s3_diff_6w_t": "26.19%",
    "s3_cur_12w_o": "66.67%","s3_cur_12w_s": "25.00%","s3_cur_12w_t": "42.86%",
    "s3_prev_12w_o": "33.33%","s3_prev_12w_s": "33.33%","s3_prev_12w_t": "33.33%",
    "s3_diff_12w_o": "33.33%","s3_diff_12w_s": "-8.33%","s3_diff_12w_t": "9.52%",
    "s3_obs": "（範例文字：本區為展示版佔位說明）",
    "s3_focus": "（範例文字：本區為展示版佔位說明）",

    # 四、非專項
    "s4_cur_bug": "5",    "s4_cur_feat": "21",   "s4_cur_total": "26",
    "s4_prev_bug": "3",   "s4_prev_feat": "28",  "s4_prev_total": "31",
    "s4_yoy_bug": "9",    "s4_yoy_feat": "39",   "s4_yoy_total": "48",
    "s4_yoy_diff_bug": "-44.44%","s4_yoy_diff_feat": "-46.15%","s4_yoy_diff_total": "-91%",
    "s4_cur_eng_tp_bug": "0.62","s4_cur_eng_tp_feat": "2.61","s4_cur_eng_tp_total": "3.23",
    "s4_prev_eng_tp_bug": "0.37","s4_prev_eng_tp_feat": "3.49","s4_prev_eng_tp_total": "3.86",
    "s4_qoq_eng_tp_bug": "66.18%","s4_qoq_eng_tp_feat": "-25.22%","s4_qoq_eng_tp_total": "-16.37%",
    "s4_cur_qa_tp_bug": "4.55","s4_cur_qa_tp_feat": "19.09","s4_cur_qa_tp_total": "23.64",
    "s4_prev_qa_tp_bug": "3.40","s4_prev_qa_tp_feat": "31.70","s4_prev_qa_tp_total": "35.09",
    "s4_qoq_qa_tp_bug": "33.84%","s4_qoq_qa_tp_feat": "-39.77%","s4_qoq_qa_tp_total": "-32.65%",
    "s4_obs": "（範例文字：本區為展示版佔位說明）",
    "s4_focus": "（範例文字：本區為展示版佔位說明）",

    # 五、週期
    "s51_cur_prd_avg": "32.50","s51_cur_prd_med": "無有效值",
    "s51_prev_prd_avg": "84.50","s51_prev_prd_med": "18.00",
    "s51_yoy_prd_avg": "0.00","s51_yoy_prd_med": "0.00","s51_qoq_prd": "-61.54%",
    "s51_cur_mock_avg": "無","s51_cur_mock_med": "無",
    "s51_prev_mock_avg": "無","s51_prev_mock_med": "無",
    "s51_yoy_mock_avg": "0.00","s51_yoy_mock_med": "0.00","s51_qoq_mock": "-",
    "s51_cur_dev_avg": "無","s51_cur_dev_med": "無",
    "s51_prev_dev_avg": "44.00","s51_prev_dev_med": "57.50",
    "s51_yoy_dev_avg": "0.00","s51_yoy_dev_med": "0.00","s51_qoq_dev": "-",
    "s51_cur_qa_avg": "無","s51_cur_qa_med": "無",
    "s51_prev_qa_avg": "20.00","s51_prev_qa_med": "無",
    "s51_yoy_qa_avg": "0.00","s51_yoy_qa_med": "0.00","s51_qoq_qa": "-",
    "s51_cur_total_avg": "53.00","s51_cur_total_med": "無",
    "s51_prev_total_avg": "150.50","s51_prev_total_med": "無",
    "s51_yoy_total_avg": "0.00","s51_yoy_total_med": "0.00","s51_qoq_total": "-64.78%",
    "s51_cur_prd_prep_avg": "37.00","s51_cur_prd_prep_med": "無",
    "s51_prev_prd_prep_avg": "63.50","s51_prev_prd_prep_med": "無","s51_qoq_prd_prep": "-41.73%",
    "s51_cur_wait_rev_avg": "無","s51_cur_wait_rev_med": "無",
    "s51_prev_wait_rev_avg": "14.00","s51_prev_wait_rev_med": "無","s51_qoq_wait_rev": "-",
    "s51_cur_rev_avg": "1.00","s51_cur_rev_med": "無",
    "s51_prev_rev_avg": "1.00","s51_prev_rev_med": "0.00","s51_qoq_rev": "-",
    "s51_cur_res_avg": "無","s51_cur_res_med": "無",
    "s51_prev_res_avg": "0.00","s51_prev_res_med": "0.00","s51_qoq_res": "-",
    "s51_cur_devp_avg": "9.50","s51_cur_devp_med": "無",
    "s51_prev_devp_avg": "8.50","s51_prev_devp_med": "2.50","s51_qoq_devp": "11.76%",
    "s51_cur_dev2_avg": "無","s51_cur_dev2_med": "無",
    "s51_prev_dev2_avg": "35.00","s51_prev_dev2_med": "45.00","s51_qoq_dev2": "-",
    "s51_cur_qap_avg": "無","s51_cur_qap_med": "無",
    "s51_prev_qap_avg": "4.75","s51_prev_qap_med": "12.00","s51_qoq_qap": "-",
    "s51_cur_qa2_avg": "無","s51_cur_qa2_med": "無",
    "s51_prev_qa2_avg": "11.00","s51_prev_qa2_med": "無","s51_qoq_qa2": "-",
    "s52_cur_wait_dev": "23.62","s52_cur_dev": "12.31",
    "s52_cur_wait_qa": "0","s52_cur_qa": "0","s52_cur_total": "42.17",
    "s52_prev_wait_dev": "24.58","s52_prev_dev": "15.50",
    "s52_prev_wait_qa": "0","s52_prev_qa": "1.00","s52_prev_total": "52.80",
    "s52_qoq_wait_dev": "-3.93%","s52_qoq_dev": "-20.60%",
    "s52_qoq_wait_qa": "-","s52_qoq_qa": "-","s52_qoq_total": "-20.13%",
    "s51_s52_obs": "（範例文字：本區為展示版佔位說明）",
    "s51_s52_focus": "（範例文字：本區為展示版佔位說明）",

    # 六、工作天
    "s6_cur_eng_a": "1.82","s6_cur_eng_b": "1.72","s6_cur_eng_ab": "3.54",
    "s6_cur_eng_c": "0.00","s6_cur_eng_d": "1.16","s6_cur_eng_e": "0.00","s6_cur_eng_total": "4.70",
    "s6_eng_loss_a": "-1.32","s6_eng_loss_b": "0.33","s6_eng_loss_ab": "-0.99",
    "s6_eng_loss_c": "0.00","s6_eng_loss_d": "0.00","s6_eng_loss_e": "0.00","s6_eng_loss_total": "-0.99",
    "s6_adj_eng_a": "0.50","s6_adj_eng_b": "2.05","s6_adj_eng_ab": "2.54",
    "s6_adj_eng_c": "0.00","s6_adj_eng_d": "1.16","s6_adj_eng_e": "0.00","s6_adj_eng_total": "3.70",
    "s6_cur_qa_a": "0.00","s6_cur_qa_b": "0.00","s6_cur_qa_ab": "0.00",
    "s6_cur_qa_c": "0.00","s6_cur_qa_d": "0.30","s6_cur_qa_e": "0.00","s6_cur_qa_total": "0.30",
    "s6_qa_loss_a": "-3.03","s6_qa_loss_b": "0.00","s6_qa_loss_ab": "-3.03",
    "s6_qa_loss_c": "0.00","s6_qa_loss_d": "0.00","s6_qa_loss_e": "0.00","s6_qa_loss_total": "-3.03",
    "s6_adj_qa_a": "-3.03","s6_adj_qa_b": "0.00","s6_adj_qa_ab": "-3.03",
    "s6_adj_qa_c": "0.00","s6_adj_qa_d": "0.30","s6_adj_qa_e": "0.00","s6_adj_qa_total": "-2.73",
    "s6_obs": "（範例文字：本區為展示版佔位說明）",
    "s6_focus": "（範例文字：本區為展示版佔位說明）",
    "s62_eng_story": "112.25","s62_eng_fix": "6.50","s62_eng_sf": "118.75",
    "s62_eng_task": "28.00","s62_eng_survey": "0.00","s62_eng_defect": "0.00","s62_eng_total": "146.75",
    "s62_eng_avg_story": "4.64","s62_eng_avg_fix": "0.27","s62_eng_avg_sf": "4.91",
    "s62_eng_avg_task": "1.16","s62_eng_avg_survey": "0.00","s62_eng_avg_defect": "0.00","s62_eng_avg_total": "6.07",
    "s62_qa_story": "0.10","s62_qa_fix": "0.25","s62_qa_sf": "0.35",
    "s62_qa_task": "1.00","s62_qa_survey": "0.00","s62_qa_defect": "0.00","s62_qa_total": "1.35",
    "s62_qa_avg_story": "0.03","s62_qa_avg_fix": "0.08","s62_qa_avg_sf": "0.11",
    "s62_qa_avg_task": "0.30","s62_qa_avg_survey": "0.00","s62_qa_avg_defect": "0.00","s62_qa_avg_total": "0.41",
    "s62_obs": "（範例文字：本區為展示版佔位說明）",
    "s62_focus": "（範例文字：本區為展示版佔位說明）",
    # 六 隔季首月上線預覽（輔助）
    "s6next_month": "", "s6next_count": "0",
    "s6next_eng_story": "0.00","s6next_eng_fix": "0.00","s6next_eng_sf": "0.00","s6next_eng_task": "0.00","s6next_eng_survey": "0.00","s6next_eng_defect": "0.00","s6next_eng_total": "0.00",
    "s6next_qa_story": "0.00","s6next_qa_fix": "0.00","s6next_qa_sf": "0.00","s6next_qa_task": "0.00","s6next_qa_survey": "0.00","s6next_qa_defect": "0.00","s6next_qa_total": "0.00",

    # 七、在職人力
    "s7_m1_pm": "1","s7_m1_be": "1.75","s7_m1_fe": "7.00","s7_m1_ios": "1.10","s7_m1_qa": "0.00","s7_m1_ratio": "1:4.6:0.8",
    "s7_m2_pm": "1.75","s7_m2_be": "7.29","s7_m2_fe": "1.10","s7_m2_ios": "0.00","s7_m2_qa": "1.10","s7_m2_ratio": "1:4.8:0.6",
    "s7_m3_pm": "1.50","s7_m3_be": "6.58","s7_m3_fe": "1.10","s7_m3_ios": "0.00","s7_m3_qa": "0.80","s7_m3_ratio": "1:5.1:0.5",
    "s7_q_pm": "1.67","s7_q_be": "6.96","s7_q_fe": "1.10","s7_q_ios": "0.00","s7_q_qa": "1.10","s7_q_ratio": "1:4.8:0.7",
    "s7_obs": "（範例文字：本區為展示版佔位說明）",
    "s7_focus": "（範例文字：本區為展示版佔位說明）",

    # 八、報告總結
    "s8_pm_ued": "（範例文字：本區為展示版佔位說明）",
    "s8_rd": "（範例文字：本區為展示版佔位說明）",
    "s8_qa": "（範例文字：本區為展示版佔位說明）",
    "s8_pmo": "（範例文字：本區為展示版佔位說明）",

    # 九、參考資料
    "s9_link_dashboard": "(請填入人效看板連結)",
    "s9_link_raw_data":  "(請填入 Raw Data 連結)",
    "s9_link_jira":      "(請填入 Jira/Roadmap 連結)",
    "s9_link_other":     "(選填)",
}

# ── DEMO 去識別化：敘述性欄位(現況觀察/關注重點等，compute 不產生)換成範例文字 ──
_DEMO_NARRATIVE = {"s8_pm_ued", "s8_rd", "s8_qa", "s8_pmo"}
for _k in list(SAMPLE):
    if _k.endswith("_obs"):
        SAMPLE[_k] = "本季各項指標觀察詳見上方數據與圖表（展示版範例文字）。"
    elif _k.endswith("_focus"):
        SAMPLE[_k] = "關注重點：持續改善交付週期與資料完整度（範例文字）。"
    elif _k in _DEMO_NARRATIVE:
        SAMPLE[_k] = "（範例文字）"


# ─── 欄字母 → 0-indexed 整數 ──────────────────────────────────────────────────
def _col_to_idx(col: str) -> int:
    col = col.upper()
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


# ─── 設定檢查 ─────────────────────────────────────────────────────────────────
def _sheets_configured() -> bool:
    if MOCK:
        return False   # DEMO：不走 legacy Google Sheets 路徑
    return bool(SHEET_ID and os.path.exists(CREDENTIALS_FILE))


# ─── 主檔 tab 讀取（雙模式：公開 CSV 優先 → 服務帳號 gspread fallback）───────
def _tab_df(gid, header: int = 0) -> "pd.DataFrame | None":
    """
    讀主檔（SHEET_ID）指定 gid 的 tab → DataFrame。
    1) 先走免憑證 CSV export（主檔有開「連結可檢視」時）
    2) 讀不到（401/回 HTML 登入頁）改走服務帳號 gspread（主檔需分享給服務帳號 email）
    兩路都轉成 CSV 再用 pd.read_csv 解析，確保 dtype 行為一致。
    """
    import pandas as pd, requests, io, csv, time

    if gid is None:
        return None
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and not r.text.lstrip()[:15].lower().startswith("<!doctype"):
            r.encoding = "utf-8"   # 強制 UTF-8，避免中文亂碼
            df = pd.read_csv(io.StringIO(r.text), header=header)
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    # fallback：服務帳號讀取（主檔為私有時走這條）。
    # 遇 API 配額 429 時短退避重試，避免瞬間讀取失敗把整個 app 打成 DEMO。
    gc = _get_gspread_client()
    if gc is None:
        return None
    for attempt in range(3):
        try:
            ws = gc.open_by_key(SHEET_ID).get_worksheet_by_id(int(gid))
            vals = ws.get_all_values()
            if len(vals) <= header:
                return None
            buf = io.StringIO()
            csv.writer(buf).writerows(vals)
            buf.seek(0)
            df = pd.read_csv(buf, header=header)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            if ("429" in str(e) or "Quota" in str(e)) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))   # 1.5s、3s
                continue
            return None
    return None


# ─── Raw Data tab 抓取 ─────────────────────────────────────────────────────
# 上次成功讀到的封版索引（跨快取過期保留在記憶體）。
# 用途：某次讀取因 API 配額 429 失敗時，沿用上次結果，避免整個 app 誤判成「全隊 DEMO」。
_LAST_GOOD_INDEX: dict = {}

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_index() -> dict:
    """
    讀封版索引 tab（INDEX_GID），回傳 {(季度, 團隊): gid或None}。
    索引的角色 = Live/DEMO 把關：有該 (季度, 團隊) 列即視為「資料就緒」。
    gid 欄可留空（定址交給名稱自動對應），有填則作為 fallback/手動覆蓋。
    讀取失敗（如 429）→ 沿用上次成功結果，不回空（否則會誤把全部團隊打成 DEMO）。
    """
    global _LAST_GOOD_INDEX
    if MOCK:
        return _mock.index_set()
    try:
        df = _tab_df(INDEX_GID)
        if df is None:
            return dict(_LAST_GOOD_INDEX)   # 讀失敗 → 沿用上次成功的索引
        out: dict = {}
        for _, row in df.iterrows():
            q = str(row.get("季度", "")).strip()
            t = str(row.get("團隊", "")).strip()
            if not q or not t or q.lower() == "nan" or t.lower() == "nan":
                continue
            gid_raw = str(row.get("gid", "")).strip()
            try:
                out[(q, t)] = int(float(gid_raw))
            except ValueError:
                out[(q, t)] = None   # 沒填 gid 也算已封版，定址走名稱對應
        if out:
            _LAST_GOOD_INDEX = dict(out)   # 記住這次成功結果
        return out
    except Exception:
        return dict(_LAST_GOOD_INDEX)   # 例外時也沿用上次成功結果


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_tab_catalog() -> dict:
    """列出主檔所有 tab（服務帳號），回傳 {正規化名稱: gid}。讀不到回 {}。"""
    try:
        gc = _get_gspread_client()
        if gc is None:
            return {}
        return {" ".join(w.title.lower().split()): w.id
                for w in gc.open_by_key(SHEET_ID).worksheets()}
    except Exception:
        return {}


def _gid_by_name(team: str, quarter: str):
    """依 RAW_TAB_NAME_PATTERNS 用「tab 名稱」自動找 (季度, 團隊) 的 gid；找不到回 None。"""
    catalog = _fetch_tab_catalog()
    if not catalog:
        return None
    y4, qn = quarter[:4], quarter[4:]   # "2026Q1" → "2026", "Q1"
    for pat in RAW_TAB_NAME_PATTERNS:
        name = pat.format(team=team, y4=y4, y2=y4[2:], q=qn)
        name = " ".join(name.lower().split())
        if name in catalog:
            return catalog[name]
    return None


def _resolve_gid(team: str, quarter=None):
    """(季度,團隊) → tab gid。
    把關：必須在封版索引中（否則 None → DEMO）。
    定址：優先依 tab 命名規則自動對應（tab 重建 gid 變更不受影響）；
          名稱找不到才 fallback 用索引手填的 gid。
    quarter=None 為舊路徑（目前未使用），用 TEAM_GID_MAP。"""
    if quarter:
        idx = _fetch_index()
        if (quarter, team) not in idx:
            return None
        return _gid_by_name(team, quarter) or idx.get((quarter, team))
    return TEAM_GID_MAP.get(team)


def is_quarter_designated(team: str, quarter: str) -> bool:
    """該 (季度, 團隊) 是否已在封版索引中（決定 live / DEMO）。"""
    return bool(team) and ((quarter, team) in _fetch_index())


# ─── 服務帳號（讀私有外部檔，如 PMO Roadmap Risk Assessment Sheet）─────────────
_GSPREAD_CLIENT = None
_GSPREAD_TRIED = False

def _get_gspread_client():
    """回傳已授權的 gspread client：優先 Streamlit Secrets，其次本機 credentials.json；無則 None。"""
    global _GSPREAD_CLIENT, _GSPREAD_TRIED
    if _GSPREAD_TRIED:
        return _GSPREAD_CLIENT
    _GSPREAD_TRIED = True
    try:
        import gspread, json
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
                  "https://www.googleapis.com/auth/drive.readonly"]
        info = None
        try:
            if "gcp_service_account" in st.secrets:
                raw = st.secrets["gcp_service_account"]
                info = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            info = None
        if info:
            creds = Credentials.from_service_account_info(info, scopes=scopes)
        else:
            # 找 credentials.json：先當前工作目錄，再 data.py 同目錄（避免 server CWD 不同找不到）
            cand = CREDENTIALS_FILE if os.path.exists(CREDENTIALS_FILE) else \
                   os.path.join(os.path.dirname(os.path.abspath(__file__)), CREDENTIALS_FILE)
            if not os.path.exists(cand):
                return None
            creds = Credentials.from_service_account_file(cand, scopes=scopes)
        _GSPREAD_CLIENT = gspread.authorize(creds)
    except Exception:
        _GSPREAD_CLIENT = None
    return _GSPREAD_CLIENT


# ─── 外部 Roadmap 檔案索引（季度 → 檔案ID）─────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_roadmap_file_index() -> dict:
    """讀主檔「Roadmap檔索引」tab（ROADMAP_INDEX_GID），回傳 {季度: 檔案ID}。未設/失敗回 {}。"""
    if not ROADMAP_INDEX_GID:
        return {}
    try:
        df = _tab_df(ROADMAP_INDEX_GID)
        if df is None:
            return {}
        qcol = next((c for c in df.columns if "季度" in c), None)
        fcol = next((c for c in df.columns if "檔案" in c or "ID" in c.upper()), None)
        if not qcol or not fcol:
            return {}
        out = {}
        for _, row in df.iterrows():
            q = str(row[qcol]).strip()
            fid = str(row[fcol]).strip()
            if q and fid and fid.lower() != "nan":
                out[q] = fid
        return out
    except Exception:
        return {}


def _roadmap_file_id(quarter: str):
    """季度 → 外部 Roadmap 檔案ID：先查索引 tab，再 fallback 用 ROADMAP_FILE_MAP。"""
    return _fetch_roadmap_file_index().get(quarter) or ROADMAP_FILE_MAP.get(quarter)


# ─── 封版（凍結）季度：2.1 讀快照，不再即時計算 ─────────────────────────────────
def frozen_date(quarter: str):
    """回傳該季度的封版日（如 '2026-07-22'）；未封版回 None。"""
    return FROZEN_QUARTERS.get(quarter)


@st.cache_data(ttl=600, show_spinner=False)
def _load_frozen_s21(quarter: str):
    """讀凍結快照 frozen_s21_<季度>.json → {team: {total_req/act_done/est_done/addon: {count,items}}}。"""
    import json
    if quarter not in FROZEN_QUARTERS:
        return None
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"frozen_s21_{quarter}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("teams", {})
    except Exception:
        return None


# ─── 加速快照（snapshots/<季度>.json；由 build_snapshot.py 產生、git 保存）──────
@st.cache_data(ttl=600, show_spinner=False)
def _load_snapshot(quarter: str):
    """讀當季加速快照 → {"generated_at":str, "teams":{team:{"is_live":bool,"data":{...}}}}；無則 None。"""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots", f"{quarter}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def snapshot_time(quarter: str):
    """回傳該季快照產生時間（字串）；無快照回 None。供 app 表頭顯示。"""
    snap = _load_snapshot(quarter)
    return snap.get("generated_at") if snap else None


# ─── 2.1 外部 Roadmap 項目（需求/實際完成/預估完成/插件 的數字與清單）──────────
@st.cache_data(ttl=300, show_spinner=False)
def get_roadmap_items(team: str, quarter: str) -> dict:
    """
    從外部 PMO Roadmap 檔（ROADMAP_FILE_MAP[quarter]）讀該團隊 tab，依 PMO 權威公式算
    四類的數字＋項目清單。回傳 {key: {"count": int, "items": [項目名稱,...]}}，
    key = total_req/act_done/est_done/addon。四公式逐格讀 PMO 權威表解出、逐隊驗證一致。
    ⚠️ 各季 PMO 公式/欄位不同 —— 已封版季度（FROZEN_QUARTERS）改讀凍結快照，
       非封版季度（如當季 Q2）才即時計算（下方公式為 Q2 現行定義）。
    讀不到（無檔/無憑證/無 tab）回傳全 0。表頭在第 4 列（row index 3）。
    """
    import pandas as pd

    if MOCK:
        return _mock.roadmap_items(team, quarter)

    def _empty():
        return {"count": 0, "items": []}
    out = {"total_req": _empty(), "act_done": _empty(), "est_done": _empty(), "addon": _empty()}

    # 已封版季度：回傳凍結快照（不再即時計算，數據不隨 PMO 外部檔變動）
    frozen = _load_frozen_s21(quarter)
    if frozen is not None:
        t = frozen.get(team)
        return t if t else out

    file_id = _roadmap_file_id(quarter)
    gc = _get_gspread_client()
    if not file_id or gc is None:
        return out
    try:
        ws = gc.open_by_key(file_id).worksheet(team)   # tab 名稱 = 團隊名
    except Exception:
        return out
    try:
        vals = ws.get_all_values()
        if len(vals) < 5:
            return out
        hdr = [str(c).strip() for c in vals[3]]
        df = pd.DataFrame(vals[4:], columns=hdr)

        def _col(kw):
            return next((c for c in df.columns if kw in c), None)

        name_c = _col("項目名稱")
        if not name_c:
            return out
        role_c, stat_c, risk_c = _col("角色"), _col("團隊當前狀態"), _col("季初風險評估")
        prio_c = _col("項目重要性")
        date_c = _col("最新預期交付日") or _col("New Target Delivery")
        goal_c = _col("團隊維度之本季目標")                       # AP：不會更新，已停用（勿拿來判斷上線）
        goal2_c = _col("本季期望目標") or _col("Quarterly Delivery")  # U：需求總/預估完成 判斷「上線」用（會持續更新）
        addon_c = "插件" if "插件" in df.columns else None

        df = df[df[name_c].astype(str).str.strip() != ""]
        names = df[name_c].astype(str).str.strip()
        role  = df[role_c].astype(str).str.strip() if role_c else pd.Series([""] * len(df), index=df.index)
        stat  = df[stat_c].astype(str).str.strip() if stat_c else pd.Series([""] * len(df), index=df.index)
        risk  = df[risk_c].astype(str).str.strip() if risk_c else pd.Series([""] * len(df), index=df.index)
        addon = df[addon_c].astype(str).str.strip() if addon_c else pd.Series([""] * len(df), index=df.index)
        prio  = df[prio_c].astype(str) if prio_c else pd.Series([""] * len(df), index=df.index)
        goal  = df[goal_c].astype(str) if goal_c else pd.Series([""] * len(df), index=df.index)
        goal2 = df[goal2_c].astype(str) if goal2_c else pd.Series([""] * len(df), index=df.index)

        base = role.isin(["Owner", "Support"])

        def _pack(mask):
            return {"count": int(mask.sum()), "items": names[mask].tolist()}

        # ── PMO「Roadmap 數據」四欄 SUMPRODUCT 公式 ──────────────────────────────
        # （2026Q2 逐格讀取權威表公式解出，並以 16/16 隊對照驗證一致）
        # 團隊當前狀態排除清單：PMO 現行定義排除 Blocked（不再排除 Done）。
        _EXC  = {"Removed", "Wont Develop", "Wont Fix", "No Need", "Blocked"}
        _EXCd = _EXC | {"Done"}                       # 插件另外多排除 Done
        q_start, q_end = quarter_to_dates(quarter)
        # 日期務必用 format="mixed"：同一欄可能混用 2026-04-08 與 2026/04/08，
        # 否則 pandas 會用第一筆格式套全欄、把不同格式者誤判成 NaT 而漏算。
        m_date = (pd.to_datetime(df[date_c], errors="coerce", format="mixed") if date_c
                  else pd.Series([pd.NaT] * len(df), index=df.index))
        _raw_date = (df[date_c].astype(str).str.strip() if date_c
                     else pd.Series([""] * len(df), index=df.index))
        # ※【2026-07-24 使用者定案】全報告統一「不區分重要性(High)」——
        #   本季完成就是完成多少，故以下四類皆不再篩 High（與 PMO 權威表的 High 版本不同）。
        # 「交付日 ≥ 季初」：比照 Google Sheets 語意 —— 日期格內若放「非空的文字」(無法解析成日期)，
        # Sheets 的 M>=DATE() 會判 True(文字>數字)。只有下界(≥)的三欄需比照，否則需求總會少算。
        _ge_start = (
            (m_date >= pd.Timestamp(q_start))
            | (m_date.isna() & (_raw_date != "") & (_raw_date.str.lower() != "nan"))
        )

        # 實際完成（S 欄）：狀態∉排除／交付日落在本季 [季初,季末]／角色≠Consult（不分 High）
        #   ※有上下界，文字日期在上界 <季末 會被排除，故用嚴格解析（不套 _ge_start）
        act_mask = (
            (role != "Consult") & (~stat.isin(_EXC))
            & (m_date >= pd.Timestamp(q_start)) & (m_date <= pd.Timestamp(q_end))
        )

        # 預估完成（AM 欄）：角色≠Consult／狀態∉排除／季初風險評估=Safe／本季期望目標(U)含「上線」
        # 【2026-08-11 使用者定案】不判斷「交付日≥季初」——預估是季初判斷，當下不會知道交付日，
        #   故移除 _ge_start（僅預估完成移除；需求總/插件仍保留交付日條件）。
        est_mask = (
            (role != "Consult") & (~stat.isin(_EXC))
            & (risk == "Safe")
            & goal2.str.contains("上線", na=False)
        )

        # 需求總數量（E=F+G 欄）：狀態∉排除／交付日≥季初／角色∈{Owner,Support}／
        #   「上線」判斷用「本季期望目標」(U 欄，會持續更新)，非「團隊維度之本季目標」
        #   （後者用途不同、不會更新，會漏卡）（不分 High）。
        total_mask = (
            base & (~stat.isin(_EXC))
            & _ge_start
            & goal2.str.contains("上線", na=False)
        )

        # 插件需求（P+Q 欄）：狀態∉排除∪{Done}／交付日≥季初／角色∈{Owner,Support}／插件=Y（不分 High）
        addon_mask = (
            base & (~stat.isin(_EXCd))
            & _ge_start
            & (addon == "Y")
        )

        out["total_req"] = _pack(total_mask)
        out["act_done"]  = _pack(act_mask)
        out["est_done"]  = _pack(est_mask)
        out["addon"]     = _pack(addon_mask)
        # 附帶「需求總」「預估完成」依角色拆（供三章/2.4 的分母使用）
        out["total_req"]["owner"]   = int((total_mask & (role == "Owner")).sum())
        out["total_req"]["support"] = int((total_mask & (role == "Support")).sum())
        out["est_done"]["owner"]    = int((est_mask & (role == "Owner")).sum())
        out["est_done"]["support"]  = int((est_mask & (role == "Support")).sum())
        return out
    except Exception:
        return out


def _fetch_raw_csv(team: str, quarter=None) -> "pd.DataFrame | None":
    """
    讀指定（團隊, 季度）的 Raw Data tab（_tab_df 雙模式：公開 CSV → 服務帳號）。
    gid 來源：封版索引（依季度）；quarter=None 為舊路徑，用 TEAM_GID_MAP。
    回傳 DataFrame，header = 第一列欄位名稱。
    """
    if MOCK:
        return _mock.raw_df(team, quarter)
    try:
        gid = _resolve_gid(team, quarter)
        if gid is None:
            return None
        return _tab_df(gid)
    except Exception:
        return None


# ─── Google Sheets 讀取（每 team+quarter 組合快取 5 分鐘）────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_raw(team: str) -> list[list[str]]:
    """讀取該團隊的整個 tab，回傳 list[list[str]]（含 header row）"""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    gid = TEAM_GID_MAP.get(team)
    ws = sh.get_worksheet_by_id(gid) if gid is not None else sh.worksheet(team)
    if ws is None:
        raise ValueError(f"找不到團隊「{team}」的工作表")
    return ws.get_all_values()


def _compute_metrics(
    raw: list[list[str]],
    cur_q: str,
    prev_q: str,
) -> dict[str, str]:
    """
    套用 METRIC_DEFS 計算所有已定義指標的本季與上季值。
    回傳 {field_cur: value, field_prev: value, ...}
    """
    try:
        import pandas as pd
    except ImportError:
        return {}

    if len(raw) < 2:
        return {}

    # 建立 DataFrame（第 0 列 = 欄位名稱，不作 header 使用，用欄位索引取值）
    header = raw[0]
    df = pd.DataFrame(raw[1:], columns=header)

    cur_start, cur_end   = quarter_to_dates(cur_q)
    prev_start, prev_end = quarter_to_dates(prev_q)

    def _apply_filter(df_in: pd.DataFrame, filters: dict) -> pd.DataFrame:
        mask = pd.Series([True] * len(df_in), index=df_in.index)
        for col_letter, val in filters.items():
            # 找到對應欄名
            col_idx = _col_to_idx(col_letter)
            if col_idx >= len(df_in.columns):
                continue
            col_name = df_in.columns[col_idx]
            series = df_in[col_name]

            if val == "*":                         # 不為空
                mask &= series.astype(str).str.strip().ne("")
            elif val is True:                      # 布林 True
                mask &= series.astype(str).str.strip().str.lower().isin(
                    ["true", "1", "yes", "是", "v", "✓"]
                )
            elif val is False:                     # 布林 False
                mask &= series.astype(str).str.strip().str.lower().isin(
                    ["false", "0", "no", "否", "x"]
                )
            elif isinstance(val, list):            # in list
                mask &= series.isin(val)
            else:                                  # exact match
                mask &= series.astype(str).str.strip() == str(val)
        return df_in[mask]

    def _filter_by_date(df_in: pd.DataFrame, date_col: str,
                        start: date, end: date) -> pd.DataFrame:
        col_idx = _col_to_idx(date_col)
        if col_idx >= len(df_in.columns):
            return df_in.iloc[0:0]
        col_name = df_in.columns[col_idx]
        dates = pd.to_datetime(df_in[col_name], errors="coerce").dt.date
        return df_in[(dates >= start) & (dates <= end)]

    # 第一輪：計算所有 count 類指標
    computed: dict[str, dict[str, int | float]] = {}   # {base_key: {cur, prev}}
    for base_key, defn in METRIC_DEFS.items():
        agg = defn["agg"]
        if agg not in ("count", "ratio", "derived"):
            continue
        if agg == "count":
            filtered = _apply_filter(df, defn.get("filters", {}))
            date_col  = defn["date_col"]
            cur_val  = len(_filter_by_date(filtered, date_col, cur_start, cur_end))
            prev_val = len(_filter_by_date(filtered, date_col, prev_start, prev_end))
            computed[base_key] = {"cur": cur_val, "prev": prev_val}

    # 第二輪：derived（相加）
    for base_key, defn in METRIC_DEFS.items():
        if defn["agg"] != "derived":
            continue
        formula = defn["formula"]   # ["a", "+", "b"]
        cur_val = prev_val = 0
        for token in formula:
            if token == "+":
                continue
            if token in computed:
                cur_val  += computed[token]["cur"]
                prev_val += computed[token]["prev"]
        computed[base_key] = {"cur": cur_val, "prev": prev_val}

    # 第三輪：ratio
    for base_key, defn in METRIC_DEFS.items():
        if defn["agg"] != "ratio":
            continue
        num_key = defn["numerator"]
        den_key = defn["denominator"]
        num = computed.get(num_key, {"cur": 0, "prev": 0})
        den = computed.get(den_key, {"cur": 0, "prev": 0})
        cur_val  = (num["cur"]  / den["cur"]  if den["cur"]  else 0)
        prev_val = (num["prev"] / den["prev"] if den["prev"] else 0)
        computed[base_key] = {"cur": cur_val, "prev": prev_val}

    # 格式化成字串；命名規則：{section}_{period}_{metric_suffix}
    # 例：base_key="s3_smk_ot_o" → "s3_cur_smk_ot_o" / "s3_prev_smk_ot_o"
    # 內部中間值（i_ 開頭）照樣輸出，但 app.py 不會引用，無影響
    result: dict[str, str] = {}
    for base_key, vals in computed.items():
        defn = METRIC_DEFS[base_key]
        section, metric_suffix = base_key.split("_", 1)
        for period in ("cur", "prev"):
            app_key = f"{section}_{period}_{metric_suffix}"
            v = vals[period]
            if defn["agg"] == "ratio":
                result[app_key] = f"{v:.2%}"
            else:
                result[app_key] = str(int(v))

    return result


# ─── 日期範圍過濾工具 ─────────────────────────────────────────────────────────
def _filter_by_quarter(df: "pd.DataFrame", date_col: str, q: str) -> "pd.DataFrame":
    """過濾 date_col 欄位在指定季度區間內的列"""
    import pandas as pd
    start, end = quarter_to_dates(q)
    # 統一轉成 Timestamp 避免 datetime64 vs date 型別衝突
    ts_start = pd.Timestamp(start)
    ts_end   = pd.Timestamp(end)
    dates = pd.to_datetime(df[date_col], errors="coerce")
    return df[(dates >= ts_start) & (dates <= ts_end)]


# ─── Roadmap tab 抓取（依季度選對應 GID，快取 5 分鐘）──────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_roadmap(quarter: str) -> "pd.DataFrame | None":
    """
    從對應季度的 Roadmap 彙總 tab 讀取資料。
    回傳 DataFrame（header = Row 2），找不到 GID 時回傳 None。
    """
    try:
        gid = ROADMAP_GID_MAP.get(quarter)
        if gid is None:
            return None
        # Row 1 = 群組標題（合併儲存格），Row 2 = 實際欄位名稱
        return _tab_df(gid, header=1)
    except Exception:
        return None


# ─── 一、季度發版情形（主檔「上版紀錄」tab）────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _fetch_release() -> "pd.DataFrame | None":
    """讀主檔「上版紀錄」tab（RELEASE_GID），header = Row 0。"""
    if MOCK:
        return _mock.release_df()
    return _tab_df(RELEASE_GID, header=0)


def _release_quarter_str(quarter: str) -> str:
    """app 季度 "2026Q2" → 上版紀錄的 Time 格式 "2026年Q2"。"""
    return f"{quarter[:4]}年{quarter[4:]}"


def compute_s1(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    一、季度發版情形：從「上版紀錄」tab 取該隊本季 / 上季的 7 項發版統計。
    欄位固定順序（第 4~10 欄，0-indexed 3~9）：
      3 預期常規發頻率 4 常規版本頻率 5 Hotfix 6 Fastlane-Bug 7 Fastlane-Feat 8 版本回滾 9 延遲上版
    找不到該隊該季的列時，該側（cur/prev）欄位留空字串。
    """
    df = _fetch_release()
    if df is None or df.shape[1] < 10:
        return {}   # tab 讀不到 → 回 {}，保留 SAMPLE（連線失敗 fallback）

    # 以「欄位位置」建索引 {(季度字串, 團隊): [7 個值]}；欄名含換行，故用 iloc 位置
    lookup: dict[tuple, list] = {}
    for _, row in df.iterrows():
        q = str(row.iloc[0]).strip()
        t = str(row.iloc[1]).strip()
        if q and t:
            lookup[(q, t)] = [str(row.iloc[i]).strip() for i in range(3, 10)]

    fields = ("plan_freq", "normal_freq", "hotfix", "fl_bug", "fl_feat", "rollback", "delay")

    def _clean(v: str) -> str:
        # 忠實保留來源：未填留空（不臆測成 0，避免把「尚未填報」誤報成「0 次」）；
        # 並去掉 pandas 把整數欄讀成 float 產生的 ".0"（"12.0" → "12"）。
        v = str(v).strip()
        if v in ("", "nan", "None"):
            return ""
        try:
            f = float(v)
            return str(int(f)) if f == int(f) else v
        except ValueError:
            return v

    # tab 讀得到就一律回全部 14 個 key（缺列/未填 → 空字串），
    # 避免任一側 fallback 到 SAMPLE 的假值（如某隊上季尚無資料）。
    result: dict[str, str] = {}
    for prefix, quarter in (("cur", cur_q), ("prev", prev_q)):
        vals = lookup.get((_release_quarter_str(quarter), team))
        for i, f in enumerate(fields):
            result[f"s1_{prefix}_{f}"] = _clean(vals[i]) if vals else ""
    return result


# ─── 2.1 團隊專項(Roadmap_Item)交付樣貌 ─────────────────────────────────────────────────────────
def compute_s21(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    需求總 / 預估完成 / 插件：來源＝外部 Roadmap Risk Assessment 檔（get_roadmap_items）。
    **實際完成量：主幹改用 Raw Data**（本季上線 Epic+Roadmap_Item，R 落本季，與交付準確率母體、
      三章完成量一致）；Roadmap 檔的實際完成另存 `*_act_done_rm` 當輔助對照（括號並列）。
    預估目標達成比例 = Raw 實際完成 ÷ Roadmap 預估完成。
    本季無對應外部檔則回 {}（保留 SAMPLE，不覆蓋）。
    """
    if not _roadmap_file_id(cur_q):
        return {}

    import pandas as pd
    cur  = get_roadmap_items(team, cur_q)
    prev = get_roadmap_items(team, prev_q)

    # Raw Data 實際完成（主幹）＝本季上線 Epic + Roadmap_Item 計數（＝交付準確率母體）
    def _raw_done(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        b = df[(df["Issue Type"].astype(str).str.strip() == "Epic")
               & (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")]
        return int(len(_filter_by_quarter(b, "New Target Delivery Date", q)))

    raw_cur, raw_prev = _raw_done(cur_q), _raw_done(prev_q)
    # 讀不到 Raw（罕見）→ 退回 Roadmap 值，避免空白
    act_cur  = raw_cur  if raw_cur  is not None else cur["act_done"]["count"]
    act_prev = raw_prev if raw_prev is not None else prev["act_done"]["count"]

    def _qoq(c: int, p: int) -> str:
        return f"{(c - p) / p:+.2%}" if p else "－"

    def _rate(done: int, est: int) -> str:   # 預估目標達成比例 = 實際完成(Raw) ÷ 預估完成
        return f"{done / est:.2%}" if est else "－"

    return {
        "s21_cur_total_req":  str(cur["total_req"]["count"]),
        "s21_prev_total_req": str(prev["total_req"]["count"]),
        "s21_cur_act_done":     str(act_cur),                        # 主幹：Raw
        "s21_prev_act_done":    str(act_prev),
        "s21_cur_act_done_rm":  str(cur["act_done"]["count"]),       # 輔助：Roadmap 檔
        "s21_prev_act_done_rm": str(prev["act_done"]["count"]),
        "s21_cur_est_done":   str(cur["est_done"]["count"]),
        "s21_prev_est_done":  str(prev["est_done"]["count"]),
        "s21_cur_est_rate":   _rate(act_cur,  cur["est_done"]["count"]),
        "s21_prev_est_rate":  _rate(act_prev, prev["est_done"]["count"]),
        "s21_cur_addon":      str(cur["addon"]["count"]),
        "s21_prev_addon":     str(prev["addon"]["count"]),
        "s21_req_qoq":        _qoq(cur["total_req"]["count"], prev["total_req"]["count"]),
        "s21_addon_qoq":      _qoq(cur["addon"]["count"], prev["addon"]["count"]),
    }


# ─── 2.2 產品（PM）PRD 輸出數 ────────────────────────────────────────────────
def compute_s22(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    資料來源：各團隊 Raw Data tab（TEAM_GID_MAP）
    篩選條件：
      C (Issue Type)                    = "Epic"
      AF (PRD Size)                     in ["S", "M", "L", "XL"]
      Z (PRD/TRD Internal Review End Date) = 季度區間
      AE (Role)                         = "Owner" / "Support"
    """
    import pandas as pd

    prd_sizes = ["S", "M", "L", "XL"]

    def _base(q: str):
        # 各期讀各期的 tab（封版）；fallback 時各期皆為 lifetime tab
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        return df[
            (df["Issue Type"].str.strip() == "Epic") &
            (df["PRD Size"].str.strip().isin(prd_sizes))
        ].copy()

    base_cur, base_prev = _base(cur_q), _base(prev_q)
    if base_cur is None and base_prev is None:
        return {}

    def _count(base, q: str) -> tuple[int, int, int]:
        if base is None:
            return 0, 0, 0
        filtered = _filter_by_quarter(base, "PRD/TRD Internal Review End Date", q)
        owner   = len(filtered[filtered["Role"].str.strip() == "Owner"])
        support = len(filtered[filtered["Role"].str.strip() == "Support"])
        return owner, support, owner + support

    cur_o,  cur_s,  cur_t  = _count(base_cur, cur_q)
    prev_o, prev_s, prev_t = _count(base_prev, prev_q)

    def _qoq(cur: int, prev: int) -> str:
        return f"{(cur - prev) / prev:+.2%}" if prev else "－"

    # PRD 評審數（W 欄：PRD/TRD Review Final Date）
    def _count_rev(base, q: str) -> tuple[int, int, int]:
        if base is None:
            return 0, 0, 0
        filtered = _filter_by_quarter(base, "PRD/TRD Review Final Date", q)
        owner   = len(filtered[filtered["Role"].str.strip() == "Owner"])
        support = len(filtered[filtered["Role"].str.strip() == "Support"])
        return owner, support, owner + support

    cur_ro,  cur_rs,  cur_rt  = _count_rev(base_cur, cur_q)
    prev_ro, prev_rs, prev_rt = _count_rev(base_prev, prev_q)

    # PM 月均人數（用於人均計算）
    cur_pm_avg  = get_avg_headcount(team, cur_q).get("pm",  0.0)
    prev_pm_avg = get_avg_headcount(team, prev_q).get("pm", 0.0)

    def _per_pm(count: int, pm_avg: float) -> str:
        if pm_avg == 0:
            return "－"
        return f"{count / pm_avg:.2f}"

    return {
        # PRD 輸出數
        "s22_cur_prd_owner":   str(cur_o),
        "s22_cur_prd_support": str(cur_s),
        "s22_cur_prd_total":   str(cur_t),
        "s22_prev_prd_owner":  str(prev_o),
        "s22_prev_prd_support":str(prev_s),
        "s22_prev_prd_total":  str(prev_t),
        "s22_prd_qoq_owner":   _qoq(cur_o, prev_o),
        "s22_prd_qoq_support": _qoq(cur_s, prev_s),
        "s22_prd_qoq_total":   _qoq(cur_t, prev_t),
        # PRD 評審數
        "s22_cur_rev_owner":   str(cur_ro),
        "s22_cur_rev_support": str(cur_rs),
        "s22_cur_rev_total":   str(cur_rt),
        "s22_prev_rev_owner":  str(prev_ro),
        "s22_prev_rev_support":str(prev_rs),
        "s22_prev_rev_total":  str(prev_rt),
        "s22_rev_qoq_owner":   _qoq(cur_ro, prev_ro),
        "s22_rev_qoq_support": _qoq(cur_rs, prev_rs),
        "s22_rev_qoq_total":   _qoq(cur_rt, prev_rt),
        # PM 人均 PRD 輸出量
        "s22_cur_avg_owner":   _per_pm(cur_o,  cur_pm_avg),
        "s22_cur_avg_support": _per_pm(cur_s,  cur_pm_avg),
        "s22_cur_avg_total":   _per_pm(cur_t,  cur_pm_avg),
        "s22_prev_avg_owner":  _per_pm(prev_o, prev_pm_avg),
        "s22_prev_avg_support":_per_pm(prev_s, prev_pm_avg),
        "s22_prev_avg_total":  _per_pm(prev_t, prev_pm_avg),
        "s22_avg_qoq_owner":   _qoq(cur_o,  prev_o)  if cur_pm_avg and prev_pm_avg else "－",
        "s22_avg_qoq_support": _qoq(cur_s,  prev_s)  if cur_pm_avg and prev_pm_avg else "－",
        "s22_avg_qoq_total":   _qoq(cur_t,  prev_t)  if cur_pm_avg and prev_pm_avg else "－",
    }


# ─── 2.2 PRD 項目清單（供 app.py 直接呼叫，不走 SAMPLE）────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_prd_items(team: str, quarter: str) -> dict[str, list[str]]:
    """
    回傳本季通過 PRD 輸出 / PRD 評審的項目名稱清單。
    {
      "output": ["項目 A", "項目 B", ...],   # Z 欄在季度內
      "review": ["項目 C", ...],              # W 欄在季度內
    }
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return {"output": [], "review": []}

    prd_sizes = ["S", "M", "L", "XL"]
    base = df[
        (df["Issue Type"].str.strip() == "Epic") &
        (df["PRD Size"].str.strip().isin(prd_sizes))
    ].copy()

    def _names(date_col: str) -> list[str]:
        filtered = _filter_by_quarter(base, date_col, quarter)
        return filtered["Summary"].dropna().str.strip().tolist()

    return {
        "output": _names("PRD/TRD Internal Review End Date"),
        "review": _names("PRD/TRD Review Final Date"),
    }


# ─── 七、在職人力 ────────────────────────────────────────────────────────────────
HEADCOUNT_GID = 646253325   # 在職人力彙總 tab

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_headcount() -> "pd.DataFrame | None":
    """讀取在職人力 tab，回傳 DataFrame（header = Row 1）"""
    if MOCK:
        return _mock.headcount_df()
    return _tab_df(HEADCOUNT_GID)


def get_avg_headcount(team: str, quarter: str) -> dict[str, float]:
    """
    回傳指定團隊、指定季度的月均人力（三個月平均）。
    {
      "be": float, "fe": float, "ios": float,
      "qa": float, "pm": float,
      "eng": float,   # be + fe + ios
    }
    """
    import pandas as pd

    df = _fetch_headcount()
    if df is None:
        return {}

    year = int(quarter[:4])
    qnum = int(quarter[5])
    month_start = (qnum - 1) * 3 + 1

    def _month_label(offset: int) -> str:
        m = month_start + offset
        y = year
        if m > 12:
            m -= 12; y += 1
        return f"{y}年{m}月"

    def _safe(val) -> float:
        try:
            return float(str(val).strip()) if str(val).strip() not in ("", "nan") else 0.0
        except ValueError:
            return 0.0

    vals: dict[str, list[float]] = {"be": [], "fe": [], "ios": [], "qa": [], "pm": []}
    for i in range(3):
        label = _month_label(i)
        row = df[(df.iloc[:, 0].astype(str).str.strip() == label) &
                 (df.iloc[:, 1].astype(str).str.strip() == team)]
        if row.empty:
            continue
        r = row.iloc[0]
        vals["be"].append(_safe(r.iloc[2]))
        vals["fe"].append(_safe(r.iloc[3]))
        vals["ios"].append(_safe(r.iloc[4]))
        vals["qa"].append(_safe(r.iloc[5]))
        vals["pm"].append(_safe(r.iloc[6]))

    result = {k: sum(v) / len(v) if v else 0.0 for k, v in vals.items()}
    result["eng"] = result["be"] + result["fe"] + result["ios"]
    return result


def compute_s7(team: str, quarter: str) -> dict[str, str]:
    """
    資料來源：在職人力彙總 tab（HEADCOUNT_GID）
    欄位：A=Time（2026年1月）, B=Team, C=BE, D=FE, E=iOS, F=QA, G=PM
    比例：PM : (BE+FE+iOS) : QA，以 PM=1 為基準
    """
    import pandas as pd

    df = _fetch_headcount()
    if df is None:
        return {}

    year = int(quarter[:4])
    qnum = int(quarter[5])
    month_start = (qnum - 1) * 3 + 1   # Q1→1, Q2→4, Q3→7, Q4→10

    # 各月的中文月份標籤
    def _month_label(offset: int) -> str:
        m = month_start + offset
        y = year
        if m > 12:
            m -= 12
            y += 1
        return f"{y}年{m}月"

    def _safe(val) -> float:
        try:
            return float(str(val).strip()) if str(val).strip() not in ("", "nan") else 0.0
        except ValueError:
            return 0.0

    def _ratio(pm: float, dev: float, qa: float) -> str:
        if pm == 0:
            return "－"
        return f"1:{dev/pm:.1f}:{qa/pm:.1f}"

    result: dict[str, str] = {}
    found = False

    for i, key_prefix in enumerate(["m1", "m2", "m3"]):
        label = _month_label(i)
        row = df[(df.iloc[:, 0].astype(str).str.strip() == label) &
                 (df.iloc[:, 1].astype(str).str.strip() == team)]
        if row.empty:
            continue
        found = True
        r = row.iloc[0]
        be  = _safe(r.iloc[2])   # C
        fe  = _safe(r.iloc[3])   # D
        ios = _safe(r.iloc[4])   # E
        qa  = _safe(r.iloc[5])   # F
        pm  = _safe(r.iloc[6])   # G
        dev = be + fe + ios

        result[f"s7_{key_prefix}_be"]    = f"{be:.2f}"
        result[f"s7_{key_prefix}_fe"]    = f"{fe:.2f}"
        result[f"s7_{key_prefix}_ios"]   = f"{ios:.2f}"
        result[f"s7_{key_prefix}_qa"]    = f"{qa:.2f}"
        result[f"s7_{key_prefix}_pm"]    = f"{pm:.2f}"
        result[f"s7_{key_prefix}_ratio"] = _ratio(pm, dev, qa)

    # 季均（三個月平均）
    def _avg_key(k: str) -> str:
        vals = [float(result[f"s7_{m}_{k}"])
                for m in ["m1", "m2", "m3"]
                if f"s7_{m}_{k}" in result]
        return f"{sum(vals)/len(vals):.2f}" if vals else ""

    for k in ["be", "fe", "ios", "qa", "pm"]:
        v = _avg_key(k)
        if v:
            result[f"s7_q_{k}"] = v

    # 季均比例
    try:
        q_pm  = float(result.get("s7_q_pm",  "0"))
        q_be  = float(result.get("s7_q_be",  "0"))
        q_fe  = float(result.get("s7_q_fe",  "0"))
        q_ios = float(result.get("s7_q_ios", "0"))
        q_qa  = float(result.get("s7_q_qa",  "0"))
        result["s7_q_ratio"] = _ratio(q_pm, q_be + q_fe + q_ios, q_qa)
    except (ValueError, KeyError):
        pass

    # 整隊該季都無資料（如人力表尚未建 Cloud 各隊）→ 回 {}，保留 SAMPLE（DEMO）
    if not found:
        return {}

    # 有資料 → 缺月（如季末月份來源尚未填）明確補空字串，蓋掉 SAMPLE 假值，
    # 避免表格 / 走勢圖露出樣本資料（空字串在 app 端顯示空白、折線斷點）。
    for key_prefix in ["m1", "m2", "m3"]:
        for k in ("be", "fe", "ios", "qa", "pm", "ratio"):
            result.setdefault(f"s7_{key_prefix}_{k}", "")

    return result


# ─── 假期名稱中性化（避免敏感地名字眼）─────────────────────────────────────────
# base 名稱 → 中性別名（保留「（補假）」等後綴）
_HOLIDAY_ALIASES = {
    "中華民國開國紀念日": "元旦",
    "臺灣光復暨金門古寧頭大捷紀念日": "光復節",
    "香港特別行政區成立紀念日": "特別行政區成立紀念日",
}
# 保險：若未來套件新增其他含敏感詞的名稱，殘留字眼一律移除
_SENSITIVE_TOKENS = ("中華民國", "中华民国", "臺灣", "台灣", "台湾", "香港", "中國", "中国")


def _neutral_name(name: str) -> str:
    """把假期名稱中的敏感地名字眼換成中性別名。"""
    for base, alias in _HOLIDAY_ALIASES.items():
        if base in name:
            name = name.replace(base, alias)
    for tok in _SENSITIVE_TOKENS:
        name = name.replace(tok, "")
    return name.strip()


# ─── 公眾假期（TW 辦公室 / HK 辦公室 / CN 辦公室）──────────────────────────────
def get_public_holidays(quarter: str) -> dict[str, list[tuple]]:
    """
    回傳本季 TW 辦公室、HK 辦公室、CN 辦公室的工作日公眾假期。
    {
      "TW": [(date, "假期名稱"), ...],
      "HK": [(date, "假期名稱"), ...],
      "CN": [(date, "假期名稱"), ...],
    }
    資料來源：Python holidays 套件（python-holidays.org）
    """
    try:
        import holidays as _holidays
        from datetime import date, timedelta

        year = int(quarter[:4])
        qnum = int(quarter[5])
        month_start = (qnum - 1) * 3 + 1
        month_end   = month_start + 2

        def _last_day(y: int, m: int) -> int:
            import calendar
            return calendar.monthrange(y, m)[1]

        start = date(year, month_start, 1)
        end   = date(year, month_end, _last_day(year, month_end))

        result: dict[str, list[tuple]] = {}
        for code in ("TW", "HK", "CN"):
            cal = _holidays.country_holidays(code, years=year)
            items = []
            d = start
            while d <= end:
                if d.weekday() < 5 and d in cal:   # 週一~週五
                    items.append((d, _neutral_name(cal[d])))
                d += timedelta(days=1)
            result[code] = items

        return result
    except Exception:
        return {"TW": [], "HK": [], "CN": []}


# ─── 月份工具函式 ──────────────────────────────────────────────────────────────
def last_n_months(quarter: str, n: int = 6) -> list[tuple[int, int]]:
    """
    回傳以本季最後一個月為終點，往前推 n 個月的 (year, month) 清單（升冪）。
    例：quarter="2026Q1", n=6 → [(2025,10),(2025,11),(2025,12),(2026,1),(2026,2),(2026,3)]
    """
    year = int(quarter[:4])
    qnum = int(quarter[5])
    end_month = qnum * 3          # Q1→3, Q2→6, Q3→9, Q4→12
    months = []
    for i in range(n - 1, -1, -1):
        m = end_month - i
        y = year
        while m <= 0:
            m += 12; y -= 1
        months.append((y, m))
    return months


def month_label_str(year: int, month: int) -> str:
    return f"{year}/{month:02d}"


# ─── 5.1 交付週期母體項目清單 ─────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_s51_items(team: str, quarter: str) -> list:
    """
    回傳 5.1 母體（Item Type=Roadmap_Item、New Target Delivery Date 落在本季）的項目，
    [{"name": Summary, "date": 上線日 yyyy-mm-dd}]，依上線日排序。供 app.py 列「本季專項項目」。
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None or "Summary" not in df.columns:
        return []
    base = df[(df["Item Type"].astype(str).str.strip() == "Roadmap_Item")
              & (df["Issue Type"].astype(str).str.strip() == "Epic")].copy()   # 專項 = Epic 母卡
    base = _filter_by_quarter(base, "New Target Delivery Date", quarter)
    if base.empty:
        return []
    base = base.assign(_r=pd.to_datetime(base["New Target Delivery Date"], errors="coerce")).sort_values("_r")
    out = []
    for _, row in base.iterrows():
        nm = str(row.get("Summary", "")).strip()
        if not nm:
            continue
        d = row["_r"]
        out.append({"name": nm, "date": d.strftime("%Y-%m-%d") if pd.notna(d) else "－"})
    return out


# 散點圖用的整體階段（順序＝流程；整體交付放最後）
_S51_SCATTER = [("prd", "需求文檔定稿"), ("mock", "Mockup 定稿"),
                ("dev", "開發完成"), ("qa", "測試完成"), ("total", "整體交付")]


@st.cache_data(ttl=300, show_spinner=False)
def get_s51_scatter(team: str, quarter: str) -> dict:
    """
    回傳本季各專項（Epic 母卡）在整體階段的實際交付天數，供散點圖看分布/outlier。
    {階段label: [{"name","days"}]}；計算同 compute_s51（日曆/工作天、同天最少 1 天）。
    """
    import pandas as pd
    import numpy as np

    out = {lbl: [] for _, lbl in _S51_SCATTER}
    raw = _fetch_raw_csv(team, quarter)
    if raw is None or "Summary" not in raw.columns:
        return out
    b = raw[(raw["Item Type"].astype(str).str.strip() == "Roadmap_Item")
            & (raw["Issue Type"].astype(str).str.strip() == "Epic")].copy()   # 專項 = Epic 母卡
    b = _filter_by_quarter(b, "New Target Delivery Date", quarter)
    if b.empty:
        return out

    def _col(name):
        for cand in _S51_COL_ALIASES.get(name, (name,)):
            if cand in b.columns:
                return cand
        return None

    names = b["Summary"].astype(str).str.strip()
    for key, lbl in _S51_SCATTER:
        sc, ec, working, _ = _S51_METRICS[key]
        scol, ecol = _col(sc), _col(ec)
        if not scol or not ecol:
            continue
        s = pd.to_datetime(b[scol], errors="coerce")
        e = pd.to_datetime(b[ecol], errors="coerce")
        m = s.notna() & e.notna()
        if not m.any():
            continue
        if working:
            days = np.busday_count(s[m].values.astype("datetime64[D]"),
                                   e[m].values.astype("datetime64[D]")).astype(float)
        else:
            days = (e[m] - s[m]).dt.days.astype(float).values
        for nm, v in zip(names[m].tolist(), days):
            out[lbl].append({"name": nm, "days": max(1.0, float(v))})
    return out


# ─── 三、6/12 周交付項目清單 ──────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_delivery_weeks(team: str, quarter: str) -> "pd.DataFrame":
    """
    回傳本季上線（R 欄在季度區間）且有 PRD/TRD Review Final Date（W 欄）的 Epic 項目。
    新增欄位：
      calendar_days : W → R 日曆天數
      within_6w     : bool，≤ 42 天
      within_12w    : bool，≤ 84 天
    依 calendar_days 升冪排序。
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return pd.DataFrame()

    # 只看本季上線的 Epic + Roadmap_Item
    filtered = _filter_by_quarter(df, "New Target Delivery Date", quarter).copy()
    filtered = filtered[
        (filtered["Issue Type"].astype(str).str.strip() == "Epic") &
        (filtered["Item Type"].astype(str).str.strip() == "Roadmap_Item")
    ]

    # 計算 W → R 天數
    filtered["_w"] = pd.to_datetime(filtered["PRD/TRD Review Final Date"], errors="coerce")
    filtered["_r"] = pd.to_datetime(filtered["New Target Delivery Date"],   errors="coerce")
    filtered["calendar_days"] = (filtered["_r"] - filtered["_w"]).dt.days

    # 只保留兩個日期都有值、且天數 >= 0 的列
    filtered = filtered.dropna(subset=["_w", "_r"])
    filtered = filtered[filtered["calendar_days"] >= 0]
    # 有效交付至少呈現 1 天（同天 0 → 1）；不影響 6/12 週分類（仍 ≤ 42/84）
    filtered["calendar_days"] = filtered["calendar_days"].clip(lower=1)

    filtered["within_6w"]  = filtered["calendar_days"] <= 42
    filtered["within_12w"] = filtered["calendar_days"] <= 84

    cols = ["Key", "Summary", "Role", "PRD/TRD Review Final Date",
            "New Target Delivery Date", "calendar_days", "within_6w", "within_12w"]
    cols = [c for c in cols if c in filtered.columns]
    return filtered[cols].sort_values("calendar_days").reset_index(drop=True)


# ─── 三、6/12 週交付率月份趨勢 ────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_delivery_trend_monthly(team: str, quarter: str, n_months: int = 6) -> "pd.DataFrame":
    """
    回傳最近 n 個月，每月的 6/12 週交付率。
    columns: month_label, total, cnt_6w, cnt_12w, rate_6w, rate_12w
    """
    import pandas as pd
    import calendar

    months = last_n_months(quarter, n_months)
    rows = []
    _cache: dict = {}
    def _df_for(q):
        # 每月對應其季度的 tab（封版）；同季只抓一次
        if q not in _cache:
            _cache[q] = _fetch_raw_csv(team, q)
        return _cache[q]

    for y, m in months:
        q_str = f"{y}Q{(m - 1) // 3 + 1}"
        df = _df_for(q_str)
        if df is None:
            rows.append({"month_label": month_label_str(y, m), "total": 0,
                         "cnt_6w": 0, "cnt_12w": 0, "rate_6w": None, "rate_12w": None})
            continue
        last_day = calendar.monthrange(y, m)[1]
        start = pd.Timestamp(y, m, 1)
        end   = pd.Timestamp(y, m, last_day)
        dates = pd.to_datetime(df["New Target Delivery Date"], errors="coerce")
        sub = df[(dates >= start) & (dates <= end)].copy()
        sub = sub[
            (sub["Issue Type"].astype(str).str.strip() == "Epic") &
            (sub["Item Type"].astype(str).str.strip() == "Roadmap_Item")
        ]
        sub["_w"] = pd.to_datetime(sub["PRD/TRD Review Final Date"], errors="coerce")
        sub["_r"] = pd.to_datetime(sub["New Target Delivery Date"],   errors="coerce")
        sub["days"] = (sub["_r"] - sub["_w"]).dt.days
        sub = sub.dropna(subset=["_w", "_r"])
        sub = sub[sub["days"] >= 0]

        total  = len(sub)
        cnt_6  = int((sub["days"] <= 42).sum())
        cnt_12 = int((sub["days"] <= 84).sum())
        rows.append({
            "month_label": month_label_str(y, m),
            "total":   total,
            "cnt_6w":  cnt_6,
            "cnt_12w": cnt_12,
            "rate_6w":  round(cnt_6  / total * 100, 1) if total else None,
            "rate_12w": round(cnt_12 / total * 100, 1) if total else None,
        })

    return pd.DataFrame(rows)


# ─── 三、Smoke Test（首次準時 / 首次通過）───────────────────────────────────────
def compute_s3_smoke(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    母體：本季上線的 Epic + Roadmap_Item（R = New Target Delivery Date 落在本季）。
    來源欄：First_smoke_on_time（準時）、First_smoke_passed（首次通過），值為 True/False/空白。
    每指標分 Owner / Support / Total(=Owner+Support)：
      數量 = 該組中值為 True 的數；比例 = True 數 ÷ 該組「有填(非空)」的數（無母體 → 「－」）。
    讀不到 tab / 缺欄 → 回 {}（保留 SAMPLE）。
    """
    import pandas as pd

    def _one(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None or "First_smoke_on_time" not in df.columns or "First_smoke_passed" not in df.columns:
            return None
        base = df[(df["Issue Type"].astype(str).str.strip() == "Epic")
                  & (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")].copy()
        base = _filter_by_quarter(base, "New Target Delivery Date", q)
        role = (base["Role"].astype(str).str.strip() if "Role" in base.columns
                else pd.Series([""] * len(base), index=base.index))
        groups = {"o": role == "Owner", "s": role == "Support", "t": role.isin(["Owner", "Support"])}

        def _metric(colname: str) -> dict:
            # ⚠️ 用 .map(str(...)) 而非 .astype(str).str.lower()：後者對真正的 NaN 會
            #    再變回 float nan，isin(["","nan","none"]) 抓不到 → 空白列誤灌進分母。
            col = base[colname].map(lambda v: str(v).strip().lower())
            nonempty = ~col.isin(["", "nan", "none"])
            istrue = col == "true"
            out = {}
            for g, mask in groups.items():
                denom = int((nonempty & mask).sum())
                num   = int((istrue & mask).sum())
                out[g]      = str(num)
                out["r" + g] = f"{num / denom:.2%}" if denom else "－"
            return out

        return {"ot": _metric("First_smoke_on_time"), "fp": _metric("First_smoke_passed")}

    out: dict[str, str] = {}
    for prefix, q in (("cur", cur_q), ("prev", prev_q)):
        r = _one(q)
        if r is None:
            continue
        for g in ("o", "s", "t"):
            out[f"s3_{prefix}_smk_ot_{g}"]      = r["ot"][g]
            out[f"s3_{prefix}_smk_ot_r{g}"]     = r["ot"]["r" + g]
            out[f"s3_{prefix}_smk_fp_{g}"]      = r["fp"][g]
            out[f"s3_{prefix}_smk_fp_r{g}"]     = r["fp"]["r" + g]
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_s3_smoke_items(team: str, quarter: str) -> list[dict]:
    """
    本季 Smoke Test 母體逐項清單（供 app.py 展開核對；與 compute_s3_smoke 同母體）。
    母體：本季上線的 Epic + Roadmap_Item（R = New Target Delivery Date 落在本季）。
    每項回傳：{name, role, on_time, passed, counted}
      on_time/passed：原始值正規化為 "True"/"False"/""（空白＝該指標未填，不列入比例分母）
      counted：兩指標只要有一個非空即 True（代表有被列入計算）
    讀不到 tab / 缺欄 → 回 []。
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None or "First_smoke_on_time" not in df.columns or "First_smoke_passed" not in df.columns:
        return []
    base = df[(df["Issue Type"].astype(str).str.strip() == "Epic")
              & (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")].copy()
    base = _filter_by_quarter(base, "New Target Delivery Date", quarter)
    if len(base) == 0:
        return []

    def _norm(v: str) -> str:
        s = str(v).strip().lower()
        if s in ("", "nan", "none"):
            return ""
        return "True" if s == "true" else "False"

    names = (base["Summary"] if "Summary" in base.columns
             else base.get("Key", pd.Series([""] * len(base), index=base.index))).astype(str)
    role  = (base["Role"].astype(str).str.strip() if "Role" in base.columns
             else pd.Series([""] * len(base), index=base.index))
    items = []
    for idx in base.index:
        ot = _norm(base.at[idx, "First_smoke_on_time"])
        fp = _norm(base.at[idx, "First_smoke_passed"])
        items.append({
            "name": names.at[idx].strip(),
            "role": role.at[idx] or "－",
            "on_time": ot,
            "passed": fp,
            "counted": bool(ot or fp),
        })
    return items


# ─── 三、6/12 週交付比率（比率表；重用 get_delivery_weeks）─────────────────────
def compute_s3_weeks(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    6/12 週交付比率表。母體＝本季上線的 Epic + Roadmap_Item 且有 W(PRD/TRD Review Final)
    與 R(New Target Delivery) 兩日期者（＝get_delivery_weeks 的母體）。
      6 週比率 = 該組 within_6w 數 ÷ 該組母體；12 週同理。
      分組：O=Role Owner、S=Role Support、T=全體母體（整體交付率）。
      差異(diff) = 本季比率 − 上季比率（百分點）。無母體 → 「－」。
    """
    import pandas as pd

    def _rates(q: str):
        dw = get_delivery_weeks(team, q)
        if dw is None or dw.empty:
            return None
        role = (dw["Role"].astype(str).str.strip() if "Role" in dw.columns
                else pd.Series([""] * len(dw), index=dw.index))
        groups = {"o": role == "Owner", "s": role == "Support",
                  "t": pd.Series([True] * len(dw), index=dw.index)}
        res = {}
        for g, mask in groups.items():
            denom = int(mask.sum())
            res[f"6w_{g}"]  = (int((dw["within_6w"]  & mask).sum()) / denom) if denom else None
            res[f"12w_{g}"] = (int((dw["within_12w"] & mask).sum()) / denom) if denom else None
        return res

    cur, prev = _rates(cur_q), _rates(prev_q)
    if cur is None and prev is None:
        return {}

    def _pct(v):
        return f"{v:.2%}" if v is not None else "－"

    out: dict[str, str] = {}
    for wk in ("6w", "12w"):
        for g in ("o", "s", "t"):
            cv = cur.get(f"{wk}_{g}") if cur else None
            pv = prev.get(f"{wk}_{g}") if prev else None
            out[f"s3_cur_{wk}_{g}"]  = _pct(cv)
            out[f"s3_prev_{wk}_{g}"] = _pct(pv)
            out[f"s3_diff_{wk}_{g}"] = f"{cv - pv:+.2%}" if (cv is not None and pv is not None) else "－"
    return out


# ─── 三、完成量 & 人均吞吐量 ─────────────────────────────────────────────────
def compute_s3_done(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    完成量：本季上線的 Epic + Roadmap_Item（R 落在本季，Raw Data；不分 High），依 Role 拆
            Owner / Support / Total(=Owner+Support，排除 Consult)。
    完成比例：完成量 ÷ 需求總數量(2.1，同角色；來自外部 Roadmap 檔)。分母 0 → 「－」。
    人均吞吐量：完成量 ÷ 季均人力（開發=BE+FE+iOS、測試=QA；不再 ÷3）。環比=(本季−上季)÷上季。
    """
    import pandas as pd
    _GK = {"o": "owner", "s": "support", "t": "total"}

    def _period(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        base = df[(df["Issue Type"].astype(str).str.strip() == "Epic")
                  & (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")].copy()
        base = _filter_by_quarter(base, "New Target Delivery Date", q)
        role = (base["Role"].astype(str).str.strip() if "Role" in base.columns
                else pd.Series([""] * len(base), index=base.index))
        done = {"o": int((role == "Owner").sum()), "s": int((role == "Support").sum())}
        done["t"] = done["o"] + done["s"]
        try:
            rm = get_roadmap_items(team, q).get("total_req", {})
        except Exception:
            rm = {}
        req = {"o": int(rm.get("owner", 0)), "s": int(rm.get("support", 0)), "t": int(rm.get("count", 0))}
        hc = get_avg_headcount(team, q)
        return {"done": done, "req": req, "eng_hc": hc.get("eng", 0.0), "qa_hc": hc.get("qa", 0.0)}

    cur, prev = _period(cur_q), _period(prev_q)
    if cur is None and prev is None:
        return {}

    def _tp(done, hc):
        return (done / hc) if hc else None

    out: dict[str, str] = {}
    tp_num = {"cur": {}, "prev": {}}   # 存數值供環比
    for pfx, per in (("cur", cur), ("prev", prev)):
        if per is None:
            continue
        for g in ("o", "s", "t"):
            gk = _GK[g]
            out[f"s3_{pfx}_done_{gk}"] = str(per["done"][g])
            r = per["req"][g]
            out[f"s3_{pfx}_ratio_{gk}"] = f"{per['done'][g] / r:.2%}" if r else "－"
            e = _tp(per["done"][g], per["eng_hc"]); q_ = _tp(per["done"][g], per["qa_hc"])
            out[f"s3_{pfx}_eng_tp_{gk}"] = f"{e:.2f}" if e is not None else "－"
            out[f"s3_{pfx}_qa_tp_{gk}"]  = f"{q_:.2f}" if q_ is not None else "－"
            tp_num[pfx][f"eng_{gk}"] = e
            tp_num[pfx][f"qa_{gk}"]  = q_

    # 吞吐量環比
    for metric in ("eng", "qa"):
        for gk in ("owner", "support", "total"):
            c = tp_num["cur"].get(f"{metric}_{gk}"); p = tp_num["prev"].get(f"{metric}_{gk}")
            out[f"s3_qoq_{metric}_tp_{gk}"] = f"{(c - p) / p:+.2%}" if (c is not None and p) else "－"
    return out


# ─── 2.4 研測（RD & QA）完成量 & 目標達成率 ──────────────────────────────────
def compute_s24(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    實際完成需求量 = 三章完成量（本季上線 Epic+Roadmap，依角色，不分 High）。
    預估完成數量   = 2.1 預估完成（季初風險=Safe＋上線），依角色（來自外部 Roadmap 檔）。
    實際交付比例   = 實際完成 ÷ 需求總數量(2.1)。
    預估目標達成比例 = 實際完成 ÷ 預估完成。
    分 Owner / Support / Total(=Owner+Support)；分母 0 → 「－」。
    """
    import pandas as pd
    _GK = {"o": "owner", "s": "support", "t": "total"}

    def _period(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        base = df[(df["Issue Type"].astype(str).str.strip() == "Epic")
                  & (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")].copy()
        base = _filter_by_quarter(base, "New Target Delivery Date", q)
        role = (base["Role"].astype(str).str.strip() if "Role" in base.columns
                else pd.Series([""] * len(base), index=base.index))
        done = {"o": int((role == "Owner").sum()), "s": int((role == "Support").sum())}
        done["t"] = done["o"] + done["s"]
        try:
            rm = get_roadmap_items(team, q)
            tr, ed = rm.get("total_req", {}), rm.get("est_done", {})
        except Exception:
            tr, ed = {}, {}
        req = {"o": int(tr.get("owner", 0)), "s": int(tr.get("support", 0)), "t": int(tr.get("count", 0))}
        est = {"o": int(ed.get("owner", 0)), "s": int(ed.get("support", 0)), "t": int(ed.get("count", 0))}
        return {"done": done, "req": req, "est": est}

    cur, prev = _period(cur_q), _period(prev_q)
    if cur is None and prev is None:
        return {}

    out: dict[str, str] = {}
    for pfx, per in (("cur", cur), ("prev", prev)):
        if per is None:
            continue
        for g in ("o", "s", "t"):
            gk = _GK[g]
            done, req, est = per["done"][g], per["req"][g], per["est"][g]
            out[f"s24_{pfx}_done_{gk}"]   = str(done)
            out[f"s24_{pfx}_est_{gk}"]    = str(est)
            out[f"s24_{pfx}_ratio_{gk}"]  = f"{done / req:.2%}" if req else "－"
            out[f"s24_{pfx}_target_{gk}"] = f"{done / est:.2%}" if est else "－"
    return out


# ─── 5.2 非專項(Small_Ticket)交付週期 ─────────────────────────────────────────
# 各階段起訖欄（使用者定案：等待開發/總計 起點用 Created 開卡日；平均、日曆天）
_S52_METRICS = {
    "wait_dev": ("Created",                       "Development Start Date"),
    "dev":      ("Development Start Date",         "Development End Date"),
    "wait_qa":  ("Development End Date",           "Functional Testing Start Date"),
    "qa":       ("Functional Testing Start Date",  "Functional Testing End Date"),
    "total":    ("Created",                        "New Target Delivery Date"),
}

# 5.2 非專項週期「參考重點指標」觀測值（天）。每季可微調——只改這裡，表格標籤與超標判定共用。
# 套用欄位：開發階段週期(dev)、開始測試～通過測試(qa)。
S52_OBS_THRESHOLD = 3.5


def compute_s52(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    5.2 非專項週期：母體＝本季上線的 Small_Ticket（R 落在本季）。
    各階段＝該階段兩日期差的「平均」（日曆天；同天最少 1 天）。環比＝(本季−上季)÷上季。
    """
    import pandas as pd

    def _avg(q: str, sc: str, ec: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        base = df[df["Item Type"].astype(str).str.strip() == "Small_Ticket"]
        base = _filter_by_quarter(base, "New Target Delivery Date", q)
        if base.empty or sc not in base.columns or ec not in base.columns:
            return None
        s = pd.to_datetime(base[sc], errors="coerce", format="mixed")
        e = pd.to_datetime(base[ec], errors="coerce", format="mixed")
        d = (e - s).dt.days[s.notna() & e.notna()]
        if d.empty:
            return None
        return float(d.clip(lower=1).mean())   # 同天最少 1 天

    out: dict[str, str] = {}
    any_val = False
    for key, (sc, ec) in _S52_METRICS.items():
        cv, pv = _avg(cur_q, sc, ec), _avg(prev_q, sc, ec)
        any_val = any_val or (cv is not None) or (pv is not None)
        out[f"s52_cur_{key}"]  = f"{cv:.2f}" if cv is not None else "－"
        out[f"s52_prev_{key}"] = f"{pv:.2f}" if pv is not None else "－"
        out[f"s52_qoq_{key}"]  = f"{(cv - pv) / pv:+.2%}" if (cv is not None and pv) else "－"
    return out if any_val else {}


@st.cache_data(ttl=300, show_spinner=False)
def get_s52_outliers(team: str, quarter: str) -> dict:
    """
    5.2 非專項「超出觀測值（> S52_OBS_THRESHOLD 天）」的卡片清單，供 app 展開核對。
    母體＝本季上線 Small_Ticket。兩個有觀測值的階段各自列出超標卡片（天數同「同天最少 1 天」）：
      dev＝開發階段（Development Start→Development End）、qa＝測試階段（Functional Testing Start→End）
    回傳 {"dev": [{key,name,days}, ...], "qa": [...]}，各依天數由大到小。讀不到 tab → 空清單。
    """
    import pandas as pd

    out = {"dev": [], "qa": []}
    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return out
    base = df[df["Item Type"].astype(str).str.strip() == "Small_Ticket"]
    base = _filter_by_quarter(base, "New Target Delivery Date", quarter)
    if base.empty:
        return out
    key_col = next((c for c in ["Key", "Issue key", "Issue Key"] if c in base.columns), None)
    for k in ("dev", "qa"):
        sc, ec = _S52_METRICS[k]
        if sc not in base.columns or ec not in base.columns:
            continue
        s = pd.to_datetime(base[sc], errors="coerce", format="mixed")
        e = pd.to_datetime(base[ec], errors="coerce", format="mixed")
        m = s.notna() & e.notna()
        days = (e - s).dt.days.clip(lower=1)          # 同天最少 1 天，與表格平均一致
        hit, hd = base[m & (days > S52_OBS_THRESHOLD)], days[m & (days > S52_OBS_THRESHOLD)]
        rows = [{
            "key":  str(r.get(key_col, "")).strip() if key_col else "",
            "name": str(r.get("Summary", "")).strip(),
            "days": int(dv),
        } for (_, r), dv in zip(hit.iterrows(), hd)]
        rows.sort(key=lambda x: x["days"], reverse=True)
        out[k] = rows
    return out


# ─── 四、非專項（Small_Ticket）吞吐量 ────────────────────────────────────────
def compute_s4(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    母體：本季上線的 Small_Ticket（R 落本季）中 **Issue Type ∈ {Fix, Story}**
          （使用者定案：Task/Survey/Defect 不上版、不計）。
      bug = Fix 卡片數；feature = Story 卡片數；total = bug + feature。
    人均吞吐量 = 數量 ÷ 季均人力（開發=BE+FE+iOS、測試=QA；不 ÷3）；環比=(本季−上季)÷上季。
    去年同期（YoY）無 2025 資料 → 一律「－」。
    """
    import pandas as pd

    def _period(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        base = df[df["Item Type"].astype(str).str.strip() == "Small_Ticket"]
        base = _filter_by_quarter(base, "New Target Delivery Date", q)
        issue = base["Issue Type"].astype(str).str.strip()
        cnt = {"bug": int((issue == "Fix").sum()), "feat": int((issue == "Story").sum())}
        cnt["total"] = cnt["bug"] + cnt["feat"]
        hc = get_avg_headcount(team, q)
        return {"cnt": cnt, "eng": hc.get("eng", 0.0), "qa": hc.get("qa", 0.0)}

    cur, prev = _period(cur_q), _period(prev_q)
    if cur is None and prev is None:
        return {}

    out: dict[str, str] = {}
    tpn = {"cur": {}, "prev": {}}
    for pfx, per in (("cur", cur), ("prev", prev)):
        if per is None:
            continue
        for g in ("bug", "feat", "total"):
            out[f"s4_{pfx}_{g}"] = str(per["cnt"][g])
            e = (per["cnt"][g] / per["eng"]) if per["eng"] else None
            q_ = (per["cnt"][g] / per["qa"]) if per["qa"] else None
            out[f"s4_{pfx}_eng_tp_{g}"] = f"{e:.2f}" if e is not None else "－"
            out[f"s4_{pfx}_qa_tp_{g}"]  = f"{q_:.2f}" if q_ is not None else "－"
            tpn[pfx][f"eng_{g}"] = e; tpn[pfx][f"qa_{g}"] = q_

    for metric in ("eng", "qa"):
        for g in ("bug", "feat", "total"):
            c = tpn["cur"].get(f"{metric}_{g}"); p = tpn["prev"].get(f"{metric}_{g}")
            out[f"s4_qoq_{metric}_tp_{g}"] = f"{(c - p) / p:+.2%}" if (c is not None and p) else "－"

    for g in ("bug", "feat", "total"):        # YoY：無 2025 資料
        out[f"s4_yoy_{g}"] = "－"
        out[f"s4_yoy_diff_{g}"] = "－"
    return out


# ─── 2.5 專項(Roadmap_Item)顆粒度（單個專項人天）────────────────────────────
def compute_s25(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    單個專項工作量（人天）。母體＝本季上線、**Item Type=Roadmap_Item** 的子卡（依 Issue Type）。
      研發階段(dev)=Story+Fix 工作量；研發前置準備(pre)=Survey；不涉代碼任務(nc)=Task。
      Eng=前端+後端+iOS；QA=測試工作量。
    「單個專項」= 各桶工作量 ÷ 本季上線專項數（Issue Type=Epic 且 Item Type=Roadmap_Item 的個數）。
    環比=(本季−上季)÷上季。
    """
    import pandas as pd

    def _num(s):
        try:
            return float(str(s).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0

    def _period(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        base = _filter_by_quarter(df, "New Target Delivery Date", q)
        base = base[base["Item Type"].astype(str).str.strip() == "Roadmap_Item"]
        if base.empty:
            return None
        issue = base["Issue Type"].astype(str).str.strip()
        n_proj = int((issue == "Epic").sum())
        eng = (base["Frontend Workload(day)"].map(_num)
               + base["Backend Workload(Day)"].map(_num)
               + base["IOS Workload(Day)"].map(_num))
        qa = base["Functional Testing Workload(Day)"].map(_num)

        def _buckets(wl):
            b = {"dev": float(wl[issue.isin(["Story", "Fix"])].sum()),
                 "pre": float(wl[issue == "Survey"].sum()),
                 "nc":  float(wl[issue == "Task"].sum())}
            b["total"] = b["dev"] + b["pre"] + b["nc"]
            return b

        return {"eng": _buckets(eng), "qa": _buckets(qa), "n": n_proj}

    cur, prev = _period(cur_q), _period(prev_q)
    if cur is None and prev is None:
        return {}

    out: dict[str, str] = {}
    nv = {"cur": {}, "prev": {}}
    for pfx, per in (("cur", cur), ("prev", prev)):
        if per is None:
            continue
        n = per["n"]
        for role in ("eng", "qa"):
            for k in ("dev", "pre", "nc", "total"):
                v = (per[role][k] / n) if n else None
                out[f"s25_{pfx}_{role}_{k}"] = f"{v:.2f}" if v is not None else "－"
                nv[pfx][f"{role}_{k}"] = v
    for role in ("eng", "qa"):
        for k in ("dev", "pre", "nc", "total"):
            c = nv["cur"].get(f"{role}_{k}"); p = nv["prev"].get(f"{role}_{k}")
            out[f"s25_qoq_{role}_{k}"] = f"{(c - p) / p:+.2%}" if (c is not None and p) else "－"
    return out


# ─── 2.3 設計（UED）稿輸出數 ─────────────────────────────────────────────────
def compute_s23(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    UED 稿輸出：母體＝**Mockup Complete Date 落在本季** 的項目（不綁本季是否上線；排除陳年舊 Mockup），
      分 Roadmap_Item（專項）/ Small_Ticket，專項與小卡一致。
      PRD 評審前交付率 = (Mockup 完成日 ≤ PRD/TRD Review Final Date) ÷ UED 稿輸出數
      開始開發前交付率 = (Mockup 完成日 ≤ Development Start Date)  ÷ UED 稿輸出數
      Small_Ticket 無評審 → 只算「開始開發前」。分母 0 → 「-」。
    """
    import pandas as pd

    def _sub(base, it, qs, qe):
        s = base[base["Item Type"].astype(str).str.strip() == it]
        mc = pd.to_datetime(s["Mockup Complete Date"], errors="coerce", format="mixed")
        has = mc.notna() & (mc >= qs) & (mc <= qe)   # Mockup 完成日「落在本季」才算
        total = int(has.sum())
        m, mcv = s[has], mc[has]
        rev = pd.to_datetime(m["PRD/TRD Review Final Date"], errors="coerce", format="mixed")
        dev = pd.to_datetime(m["Development Start Date"], errors="coerce", format="mixed")
        prd_cnt = int((rev.notna() & (mcv <= rev)).sum())
        dev_cnt = int((dev.notna() & (mcv <= dev)).sum())
        return {"total": total, "prd_cnt": prd_cnt, "dev_cnt": dev_cnt}

    def _period(q: str):
        df = _fetch_raw_csv(team, q)
        if df is None:
            return None
        # 【2026-07-29 使用者定案】UED 稿件不綁本季是否上線，但要「本季實際交付的 Mockup」：
        #   母體＝Mockup Complete Date 落在本季者（排除陳年舊 Mockup），專項/小卡一致。
        _s, _e = quarter_to_dates(q)
        qs, qe = pd.Timestamp(_s), pd.Timestamp(_e)
        return {"road": _sub(df, "Roadmap_Item", qs, qe), "sm": _sub(df, "Small_Ticket", qs, qe)}

    cur, prev = _period(cur_q), _period(prev_q)
    if cur is None and prev is None:
        return {}

    def _rate(cnt, total):
        return f"{cnt / total:.2%}" if total else "-"

    out: dict[str, str] = {}
    for pfx, per in (("cur", cur), ("prev", prev)):
        if per is None:
            continue
        r, s = per["road"], per["sm"]
        out[f"s23_{pfx}_total"]    = str(r["total"])
        out[f"s23_{pfx}_prd_cnt"]  = str(r["prd_cnt"])
        out[f"s23_{pfx}_prd_rate"] = _rate(r["prd_cnt"], r["total"])
        out[f"s23_{pfx}_dev_cnt"]  = str(r["dev_cnt"])
        out[f"s23_{pfx}_dev_rate"] = _rate(r["dev_cnt"], r["total"])
        out[f"s23_{pfx}_sm_total"]    = str(s["total"])
        out[f"s23_{pfx}_sm_dev_cnt"]  = str(s["dev_cnt"])
        out[f"s23_{pfx}_sm_dev_rate"] = _rate(s["dev_cnt"], s["total"])
    return out


# ─── 八、資料品質總覽 ──────────────────────────────────────────────────────────
# I~AH 共 26 個必要欄位
# 【2026-07-28 使用者定案】H「PRD of Main request or Supported request」已停用、不再必填，
#   故移出清單（不列入分母、不顯示），避免空著時誤拉低資料品質分數。
DQ_COLS = [
    "PRD/TRD Brief Date",                         # I
    "PRD/TRD Review Start Date",                  # J
    "Implementation Date",                        # K
    "Development Start Date",                     # L
    "Development End Date",                       # M
    "To Be Functional Tested Date",               # N
    "Functional Testing Start Date",              # O
    "Functional Testing End Date",                # P
    "First Target Delivery Date",                 # Q
    "New Target Delivery Date",                   # R
    "Frontend Workload(day)",                     # S
    "Backend Workload(Day)",                      # T
    "IOS Workload(Day)",                          # U
    "Functional Testing Workload(Day)",           # V
    "PRD/TRD Review Final Date",                  # W
    "Mockup Complete Date",                       # X
    "PRD/TRD Preparing Start Date",               # Y
    "PRD/TRD Internal Review End Date",           # Z
    "Item Type",                                  # AA
    "Target Beta Start Date",                     # AB
    "Created",                                    # AC
    "Mockup Preparing Start Date",                # AD
    "Role",                                       # AE
    "PRD Size",                                   # AF
    "First_smoke_on_time",                        # AG
    "First_smoke_passed",                         # AH
]


@st.cache_data(ttl=300, show_spinner=False)
def get_data_quality(team: str, quarter: str) -> dict:
    """
    回傳本季上線項目（R 欄在季度區間）的資料品質資訊。
    {
      "roadmap": pd.DataFrame,    # AA = Roadmap Item
      "small":   pd.DataFrame,    # AA = Small_Ticket
      "cols":    list[str],       # H~AH 欄位名稱
    }
    每列額外加入 "資料品質%" 欄位。
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return {"roadmap": pd.DataFrame(), "small": pd.DataFrame(), "cols": DQ_COLS}

    # 只保留 R 欄在本季的列
    filtered = _filter_by_quarter(df, "New Target Delivery Date", quarter).copy()

    # 只保留存在的 DQ 欄位（含新版封版 tab 的欄名別名）
    _DQ_ALIASES = {"PRD/TRD Review Start Date": ("PRD/TRD Review Start Date", "PRD评审时间")}
    avail_cols = []
    for c in DQ_COLS:
        real = next((x for x in _DQ_ALIASES.get(c, (c,)) if x in filtered.columns), None)
        if real:
            avail_cols.append(real)
    display_cols = (
        ["Key", "Summary", "Issue Type", "Item Type"] +
        [c for c in avail_cols if c not in ("Issue Type", "Item Type", "Key", "Summary")]
    )
    display_cols = [c for c in display_cols if c in filtered.columns]

    def _is_empty(v) -> bool:
        return str(v).strip() in ("", "nan", "NaN", "None")

    def _calc_quality(row) -> str:
        filled = sum(1 for c in avail_cols if not _is_empty(row.get(c, "")))
        pct = filled / len(avail_cols) * 100 if avail_cols else 0
        return f"{pct:.1f}%"

    filtered["資料品質%"] = filtered.apply(_calc_quality, axis=1)

    def _split(item_type: str) -> "pd.DataFrame":
        # 同時支援底線版（Roadmap_Item）和空格版（Roadmap Item）
        sub = filtered[filtered["Item Type"].astype(str).str.strip().str.replace(" ", "_") == item_type]
        return sub[["資料品質%"] + display_cols].reset_index(drop=True)

    return {
        "roadmap": _split("Roadmap_Item"),
        "small":   _split("Small_Ticket"),
        "cols":    avail_cols,
    }


# ─── 6 本季總人天（依卡片類型）────────────────────────────────────────────────
def compute_s62(team: str, quarter: str) -> dict[str, str]:
    """
    資料來源：各團隊 Raw Data tab（TEAM_GID_MAP）

    篩選：
      New Target Delivery Date (R) = 本季區間（依使用者指定以 R 認季）
      ＊不再限定 Item Type：抓本季所有上線卡片（Roadmap_Item + Small_Ticket），
        以反映當季產研單位的整體人天。

    維度（互斥分桶，避免重複計）：
      名稱是否包含Defect (CH) = "是"  → Defect
      其餘依 Issue Type (C)：Story / Fix / Task / Survey
      小計(sf) = Story + Fix
      總計     = Story + Fix + Task + Survey + Defect
      ＊Issue Type = Epic（專項(Roadmap_Item)母卡）不屬上述五類，依約定不計入（總計不含 Epic）。

    人天：
      Eng = Frontend + Backend + IOS Workload(day)（S+T+U）
      QA  = Functional Testing Workload(day)（V）

    月均人均工作天 = 總人天 ÷ 月均人力 ÷ 3
      （Eng 人力 = be+fe+ios，QA 人力 = qa，取自在職人力彙總 tab）
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return {}

    def _num(s) -> float:
        try:
            return float(str(s).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0

    # 不限 Item Type，僅以 R 欄認定本季上線
    st = _filter_by_quarter(df, "New Target Delivery Date", quarter)
    if st.empty:
        return {}

    eng_wl = (st["Frontend Workload(day)"].map(_num)
              + st["Backend Workload(Day)"].map(_num)
              + st["IOS Workload(Day)"].map(_num))
    qa_wl  = st["Functional Testing Workload(Day)"].map(_num)

    issue   = st["Issue Type"].astype(str).str.strip()
    defcol  = next((c for c in st.columns if "Defect" in c), None)
    is_def  = (st[defcol].astype(str).str.strip() == "是") if defcol else (issue == "\0")

    def _buckets(wl) -> dict[str, float]:
        nd = ~is_def
        story  = float(wl[nd & (issue == "Story")].sum())
        fix    = float(wl[nd & (issue == "Fix")].sum())
        task   = float(wl[nd & (issue == "Task")].sum())
        survey = float(wl[nd & (issue == "Survey")].sum())
        defect = float(wl[is_def].sum())
        return {
            "story": story, "fix": fix, "sf": story + fix,
            "task": task, "survey": survey, "defect": defect,
            "total": story + fix + task + survey + defect,
        }

    eng = _buckets(eng_wl)
    qa  = _buckets(qa_wl)

    hc      = get_avg_headcount(team, quarter)
    eng_div = hc.get("eng", 0.0) * 3
    qa_div  = hc.get("qa", 0.0) * 3

    out: dict[str, str] = {}
    for role, b, div in (("eng", eng, eng_div), ("qa", qa, qa_div)):
        for k in ("story", "fix", "sf", "task", "survey", "defect", "total"):
            out[f"s62_{role}_{k}"]     = f"{b[k]:.2f}"
            out[f"s62_{role}_avg_{k}"] = f"{b[k] / div:.2f}" if div else "－"
    return out


# ─── 6 隔季首月上線預覽（本季被擠到下一季首月的人天）──────────────────────────
def compute_s6_nextmonth(team: str, quarter: str) -> dict[str, str]:
    """
    輔助資訊：抓「下一季第一個月」New Target Delivery Date 落點的卡片，
    算 Eng/QA 各卡片類型人天（分桶同 compute_s62：Story/Fix/Task/Survey/Defect）。
    用途：當本季人均偏低時，說明是否因項目被封版/活動擠到隔月上線（如 618）。
    下一季首月：Q1→4月、Q2→7月、Q3→10月、Q4→次年1月。回傳 s6next_* + 月份標籤 + 卡片數。
    """
    import pandas as pd

    df = _fetch_raw_csv(team, quarter)
    y = int(quarter[:4]); qn = int(quarter[5])
    m = qn * 3 + 1
    if m > 12:
        m -= 12; y += 1
    label = f"{y}年{m}月"
    empty = {"s6next_month": label, "s6next_count": "0",
             **{f"s6next_{r}_{k}": "0.00" for r in ("eng", "qa")
                for k in ("story", "fix", "sf", "task", "survey", "defect", "total")}}
    if df is None:
        return empty

    start = pd.Timestamp(year=y, month=m, day=1)
    end   = start + pd.DateOffset(months=1)
    dates = pd.to_datetime(df["New Target Delivery Date"], errors="coerce", format="mixed")
    st = df[(dates >= start) & (dates < end)]
    if st.empty:
        return empty

    def _num(s) -> float:
        try:
            return float(str(s).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0

    eng_wl = (st["Frontend Workload(day)"].map(_num)
              + st["Backend Workload(Day)"].map(_num)
              + st["IOS Workload(Day)"].map(_num))
    qa_wl  = st["Functional Testing Workload(Day)"].map(_num)
    issue  = st["Issue Type"].astype(str).str.strip()
    defcol = next((c for c in st.columns if "Defect" in c), None)
    is_def = (st[defcol].astype(str).str.strip() == "是") if defcol else (issue == "\0")

    def _buckets(wl) -> dict[str, float]:
        nd = ~is_def
        story  = float(wl[nd & (issue == "Story")].sum())
        fix    = float(wl[nd & (issue == "Fix")].sum())
        task   = float(wl[nd & (issue == "Task")].sum())
        survey = float(wl[nd & (issue == "Survey")].sum())
        defect = float(wl[is_def].sum())
        return {"story": story, "fix": fix, "sf": story + fix,
                "task": task, "survey": survey, "defect": defect,
                "total": story + fix + task + survey + defect}

    # 卡片數只計五類（含 Defect），排除 Epic 母卡
    n_cards = int((is_def | issue.isin(["Story", "Fix", "Task", "Survey"])).sum())
    out = {"s6next_month": label, "s6next_count": str(n_cards)}
    for role, b in (("eng", _buckets(eng_wl)), ("qa", _buckets(qa_wl))):
        for k in ("story", "fix", "sf", "task", "survey", "defect", "total"):
            out[f"s6next_{role}_{k}"] = f"{b[k]:.2f}"
    return out


# ─── 5.1 專項(Roadmap_Item)交付週期 ───────────────────────────────────────────
# 各指標：key -> (起欄名, 訖欄名, 工作天?, 有去年同期?)；起訖定義由使用者確認（2026-06）
_S51_METRICS = {
    "prd":      ("PRD/TRD Preparing Start Date",     "PRD/TRD Brief Date",               False, True),
    "mock":     ("Mockup Preparing Start Date",      "Mockup Complete Date",             False, True),
    "dev":      ("PRD/TRD Brief Date",               "Development End Date",              False, True),
    "qa":       ("To Be Functional Tested Date",     "Functional Testing End Date",      False, True),
    "total":    ("PRD/TRD Preparing Start Date",     "New Target Delivery Date",         False, True),
    "prd_prep": ("PRD/TRD Preparing Start Date",     "PRD/TRD Internal Review End Date", False, False),
    "wait_rev": ("PRD/TRD Internal Review End Date", "PRD/TRD Review Final Date",         True,  False),
    "rev":      ("PRD评审时间",                       "PRD/TRD Review Final Date",         False, False),
    "res":      ("PRD/TRD Review Final Date",         "PRD/TRD Brief Date",               True,  False),
    "devp":     ("PRD/TRD Brief Date",               "Development Start Date",            True,  False),
    "dev2":     ("Development Start Date",            "To Be Functional Tested Date",     False, False),
    "qap":      ("To Be Functional Tested Date",     "Functional Testing Start Date",     True,  False),
    "qa2":      ("Functional Testing Start Date",    "Functional Testing End Date",       False, False),
}

# 各團隊 tab 欄名不一致時的同義欄（取第一個存在者）
_S51_COL_ALIASES = {
    "PRD评审时间": ("PRD评审时间", "PRD/TRD Review Start Date", "PRD評審時間"),
}


def compute_s51(team: str, cur_q: str, prev_q: str) -> dict[str, str]:
    """
    5.1 專項(Roadmap_Item)交付週期：中位數 / 平均 / 取樣數 n，一起 live。

    母體：Item Type = Roadmap_Item，且 New Target Delivery Date (R) 落在該季。
    各指標起訖欄與單位（日曆天/工作天）見 _S51_METRICS（由使用者確認）。

    中位數值會帶上樣本數，格式 "12.5 (n=4)"，讓觀看者知道背後取樣量。
    n = 該季母體中「起訖兩欄皆有有效日期」的項目數；缺欄則該指標 n=0。
    同天或負值（訖早於起）一律以 1 天計（同天最少 1 天規則）。環比以「平均」計算。
    """
    import pandas as pd
    import numpy as np

    def _col(df, name: str):
        if df is None:
            return None
        for cand in _S51_COL_ALIASES.get(name, (name,)):
            if cand in df.columns:
                return cand
        return None

    def _yoy(q: str) -> str:
        return f"{int(q[:4]) - 1}Q{q[5]}"

    # 各期讀各期的 tab（封版）；fallback 時各期皆為 lifetime tab
    period_q = {"cur": cur_q, "prev": prev_q, "yoy": _yoy(cur_q)}
    period_df: dict = {}
    for p, q in period_q.items():
        raw = _fetch_raw_csv(team, q)
        if raw is None:
            period_df[p] = None
            continue
        b = raw[(raw["Item Type"].astype(str).str.strip() == "Roadmap_Item")
                & (raw["Issue Type"].astype(str).str.strip() == "Epic")].copy()   # 專項 = Epic 母卡
        period_df[p] = _filter_by_quarter(b, "New Target Delivery Date", q)
    if all(v is None or v.empty for v in period_df.values()):
        return {}

    def _days(pdf, start_name, end_name, working) -> list:
        if pdf is None or pdf.empty:
            return []
        sc, ec = _col(pdf, start_name), _col(pdf, end_name)
        if sc is None or ec is None:
            return []
        s = pd.to_datetime(pdf[sc], errors="coerce")
        e = pd.to_datetime(pdf[ec], errors="coerce")
        m = s.notna() & e.notna()
        if not m.any():
            return []
        s, e = s[m], e[m]
        if working:
            raw = np.busday_count(s.values.astype("datetime64[D]"),
                                  e.values.astype("datetime64[D]")).astype(float)
        else:
            raw = (e - s).dt.days.astype(float).values
        # 有效交付至少呈現 1 天（同天/負值皆以 1 計，避免「同天=0」看似無工作）
        return [max(1.0, float(v)) for v in raw]

    out: dict[str, str] = {}
    for key, (sc, ec, working, has_yoy) in _S51_METRICS.items():
        periods = ("cur", "prev", "yoy") if has_yoy else ("cur", "prev")
        avg_num = {}
        for p in periods:
            vals = _days(period_df[p], sc, ec, working)
            n = len(vals)
            if n:
                avg = sum(vals) / n
                out[f"s51_{p}_{key}_avg"] = f"{avg:.1f}"
                med = float(pd.Series(vals).median())
                out[f"s51_{p}_{key}_med"] = f"{med:.1f} (n={n})"
                avg_num[p] = avg
            else:
                out[f"s51_{p}_{key}_avg"] = "－"
                out[f"s51_{p}_{key}_med"] = "－ (n=0)"
                avg_num[p] = None
        c, pv = avg_num.get("cur"), avg_num.get("prev")   # 環比以「平均」計算（非中位數）
        out[f"s51_qoq_{key}"] = f"{(c - pv) / pv:+.1%}" if (c is not None and pv) else "－"
    return out


# ─── 2.1 專項(Roadmap_Item)交付準確率 ─────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_delivery_accuracy(team: str, quarter: str) -> dict:
    """
    本季專項(Roadmap_Item)交付準確率（供 app.py 直接呼叫）。

    母體：Issue Type = Epic ＋ Item Type = Roadmap_Item ＋ R(New Target Delivery Date) 落在本季
    準時：R(New Target Delivery Date) ≤ Q(First Target Delivery Date)（如期或提早都算準時）
    未準時：R > Q（只有確實延後才算；提早/如期不算）
    延遲超過 2 週：R − Q > 14 日曆天（未準時的子集）

    回傳：{
      "total": int,
      "on_time":     {"count", "rate"(字串 %), "items":[Summary,...]},
      "not_on_time": {...},
      "delayed_2w":  {...},
    }
    """
    import pandas as pd

    empty = lambda: {"count": 0, "rate": "－", "items": []}
    result = {"total": 0, "on_time": empty(), "not_on_time": empty(), "delayed_2w": empty()}

    df = _fetch_raw_csv(team, quarter)
    if df is None:
        return result

    base = df[
        (df["Issue Type"].astype(str).str.strip() == "Epic") &
        (df["Item Type"].astype(str).str.strip() == "Roadmap_Item")
    ].copy()
    base = _filter_by_quarter(base, "New Target Delivery Date", quarter)
    total = len(base)
    if total == 0:
        return result

    q = pd.to_datetime(base["First Target Delivery Date"], errors="coerce")
    r = pd.to_datetime(base["New Target Delivery Date"],   errors="coerce")
    names = (base["Summary"] if "Summary" in base.columns else base.get("Key", pd.Series([""] * total))).astype(str)

    qn, rn    = q.dt.normalize(), r.dt.normalize()
    not_on    = q.notna() & r.notna() & (rn > qn)   # 只有 R 晚於 Q（確實延後）才算未準時
    on_time   = ~not_on                              # 如期、提早、或日期缺失 → 準時（無延後證據）
    delayed2w = q.notna() & r.notna() & ((r - q).dt.days > 14)

    def _pack(mask) -> dict:
        cnt = int(mask.sum())
        return {
            "count": cnt,
            "rate": f"{cnt / total:.1%}" if total else "－",
            "items": names[mask].tolist(),
        }

    result["total"]       = total
    result["on_time"]     = _pack(on_time)
    result["not_on_time"] = _pack(not_on)
    result["delayed_2w"]  = _pack(delayed2w)
    return result


# ─── 主要入口 ─────────────────────────────────────────────────────────────────
def load_data(
    team: str = "",
    quarter: str = DEFAULT_QUARTER,
    live: bool = False,
) -> tuple[dict[str, str], bool]:
    """
    回傳 (data_dict, is_live)
      data_dict : 所有欄位的值（live 優先 → sample fallback）
      is_live   : True = 資料來自 Google Sheets

    team    : 選擇的團隊名稱
    quarter : 選擇的季度，例如 "2026Q1"
    live    : True = 強制即時計算（略過加速快照，供「立即更新」按鈕）；
              False = 優先讀 snapshots/<季度>.json（秒開），無快照才即時算。
    """
    # 加速快照：非強制 live 時，若有當季快照直接回傳（不打 Google，秒開）
    if team and not live:
        snap = _load_snapshot(quarter)
        if snap:
            t = (snap.get("teams") or {}).get(team)
            if t and t.get("data"):
                return dict(t["data"]), bool(t.get("is_live"))

    live_data: dict[str, str] = {}
    is_live = False
    prev_q  = prev_quarter(quarter)
    # 嚴格封版：(季度, 團隊) 必須在索引才視為已封版；否則整隊顯示 DEMO（樣本）
    designated = bool(team) and ((quarter, team) in _fetch_index())

    if team and designated:
        # 一、季度發版情形（主檔「上版紀錄」tab）
        try:
            s1 = compute_s1(team, quarter, prev_q)
            if s1:
                live_data.update(s1)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 發版情形讀取失敗：{e}")

        # 2.1 團隊專項(Roadmap_Item)
        try:
            s21 = compute_s21(team, quarter, prev_q)
            if s21:
                live_data.update(s21)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ Roadmap 資料讀取失敗：{e}")

        # 七、在職人力
        try:
            s7 = compute_s7(team, quarter)
            if s7:
                live_data.update(s7)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 在職人力資料讀取失敗：{e}")

        # 2.2 產品（PM）PRD 輸出數：從 Raw Data tab 抓取（不需要 credentials）
        try:
            s22 = compute_s22(team, quarter, prev_q)
            if s22:
                live_data.update(s22)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ PRD 輸出數讀取失敗：{e}")

        # 6 本季總人天（依卡片類型）：從 Raw Data tab 抓取
        try:
            s62 = compute_s62(team, quarter)
            if s62:
                live_data.update(s62)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 6 本季總人天讀取失敗：{e}")

        # 6 隔季首月上線預覽（輔助：本季被擠到下一季首月的人天）
        try:
            s6n = compute_s6_nextmonth(team, quarter)
            if s6n:
                live_data.update(s6n)
        except Exception as e:
            st.warning(f"⚠️ 隔季首月預覽讀取失敗：{e}")

        # 5.1 專項(Roadmap_Item)交付週期：中位數 / 平均 / 取樣數 n
        try:
            s51 = compute_s51(team, quarter, prev_q)
            if s51:
                live_data.update(s51)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 5.1 交付週期讀取失敗：{e}")

        # 三、Smoke Test（首次準時 / 首次通過）
        try:
            s3smk = compute_s3_smoke(team, quarter, prev_q)
            if s3smk:
                live_data.update(s3smk)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ Smoke Test 讀取失敗：{e}")

        # 三、6/12 週交付比率表
        try:
            s3wk = compute_s3_weeks(team, quarter, prev_q)
            if s3wk:
                live_data.update(s3wk)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 6/12 週比率讀取失敗：{e}")

        # 三、完成量 & 人均吞吐量
        try:
            s3d = compute_s3_done(team, quarter, prev_q)
            if s3d:
                live_data.update(s3d)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 完成量/吞吐量讀取失敗：{e}")

        # 2.4 研測（RD & QA）完成量 & 目標達成率
        try:
            s24 = compute_s24(team, quarter, prev_q)
            if s24:
                live_data.update(s24)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 2.4 研測讀取失敗：{e}")

        # 5.2 非專項（Small_Ticket）交付週期
        try:
            s52 = compute_s52(team, quarter, prev_q)
            if s52:
                live_data.update(s52)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 5.2 非專項週期讀取失敗：{e}")

        # 四、非專項（Small_Ticket）吞吐量
        try:
            s4 = compute_s4(team, quarter, prev_q)
            if s4:
                live_data.update(s4)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 四 非專項吞吐量讀取失敗：{e}")

        # 2.5 專項(Roadmap_Item)顆粒度
        try:
            s25 = compute_s25(team, quarter, prev_q)
            if s25:
                live_data.update(s25)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 2.5 顆粒度讀取失敗：{e}")

        # 2.3 設計（UED）稿輸出數
        try:
            s23 = compute_s23(team, quarter, prev_q)
            if s23:
                live_data.update(s23)
                is_live = True
        except Exception as e:
            st.warning(f"⚠️ 2.3 UED 讀取失敗：{e}")

    if _sheets_configured() and team and designated:
        try:
            raw  = _fetch_raw(team)
            live_data.update(_compute_metrics(raw, quarter, prev_q))
            is_live = bool(live_data)
        except Exception as e:
            st.warning(f"⚠️ Google Sheets 連線失敗：{e}　→　顯示樣本資料")

    merged = dict(SAMPLE)
    merged.update(live_data)

    # 填入選擇的季度資訊
    if team:
        merged["TEAM_NAME"] = team
    if quarter:
        year, qnum = quarter[:4], quarter[5]
        merged["YEAR"]    = year
        merged["QUARTER"] = qnum
        if MOCK:
            # 展示版：表頭日期隨所選季度變動（資料截止＝季末、報告日期＝季末後一週）
            from datetime import timedelta
            _q_end = quarter_to_dates(quarter)[1]
            merged["DATA_CUTOFF_DATE"] = _q_end.strftime("%Y-%m-%d")
            merged["REPORT_DATE"] = (_q_end + timedelta(days=7)).strftime("%Y-%m-%d")

    return merged, is_live


def get(data: dict, key: str) -> str:
    """取值；key 不存在時回傳 '－'"""
    return data.get(key, "－")


# ─── 報告小助手（規則自動，主管視角摘要）──────────────────────────────────────
# 門檻見 docs/業務邏輯公式.md「報告小助手」一節
def build_report_assistant(data: dict, team: str, quarter: str) -> dict:
    """
    依各章 live 指標套規則，自動產生主管視角摘要。
    回傳 {key: {"title", "status", "good":[...], "bad":[...], "live":bool}}，key = 三/四/五/六/七
    """
    import re as _re

    def _f(key, default=0.0):
        m = _re.search(r"-?\d+\.?\d*", str(data.get(key, "")).replace(",", ""))
        return float(m.group()) if m else default

    def _n_of(key):
        m = _re.search(r"n=(\d+)", str(data.get(key, "")))
        return int(m.group(1)) if m else None

    out: dict = {}

    # 二、專項季度交付結果（2.1~2.5 全 live）
    g = {"title": "二、專項季度交付結果", "status": "", "good": [], "bad": [], "live": True}
    req = _f("s21_cur_total_req"); req_qoq = _f("s21_req_qoq")
    prd = _f("s22_cur_prd_total"); prd_qoq = _f("s22_prd_qoq_total")
    est_rate = _f("s21_cur_est_rate")
    try:
        acc = get_delivery_accuracy(team, quarter)
        tot = acc.get("total", 0)
        delayed = acc.get("delayed_2w", {}).get("count", 0)
        m = _re.search(r"\d+\.?\d*", acc.get("on_time", {}).get("rate", ""))
        ontime = float(m.group()) if (tot and m) else None
    except Exception:
        tot = 0; delayed = 0; ontime = None
    if ontime is not None:
        g["status"] = f"本季需求 {req:.0f} 項、PRD 輸出 {prd:.0f} 項；交付準時率 {ontime:.0f}%（{tot} 個專項）"
    else:
        g["status"] = f"本季需求 {req:.0f} 項、PRD 輸出 {prd:.0f} 項"
    if ontime is not None and ontime >= 80:
        g["good"].append(f"交付準時率 {ontime:.0f}%，表現佳")
    if ontime is not None and ontime < 60:
        g["bad"].append(f"交付準時率僅 {ontime:.0f}%")
    if delayed > 0:
        g["bad"].append(f"{delayed} 個專項延遲逾 2 週")
    if req_qoq > 0:
        g["good"].append(f"需求量較上季成長 {req_qoq:.0f}%")
    if prd_qoq > 0:
        g["good"].append(f"PRD 輸出較上季成長 {prd_qoq:.0f}%")
    if 0 < est_rate < 80:
        g["bad"].append(f"預估目標達成率 {est_rate:.0f}%，偏低")
    out["二"] = g

    # 三、上版專項吞吐量（6/12 週交付率 live）
    g = {"title": "三、上版專項吞吐量", "status": "", "good": [], "bad": [], "live": True}
    try:
        dw = get_delivery_weeks(team, quarter)
        total = len(dw)
        if total:
            c6 = int(dw["within_6w"].sum()); c12 = int(dw["within_12w"].sum())
            r6 = c6 / total * 100; r12 = c12 / total * 100; over12 = total - c12
            done_total = _f("s3_cur_done_total")   # 三章完成量（本季上線 Epic+Roadmap）
            if done_total and done_total > total:
                # 完成量 > 交付率母體：差額＝未填「評審定案日(W)」而無法納入 6/12 週計算者
                g["status"] = (f"本季完成 {done_total:.0f} 個專項，其中 {total} 個有評審記錄"
                               f"納入 6/12 週交付率計算；6 週 {r6:.0f}%、12 週 {r12:.0f}%")
                g["bad"].append(f"{done_total - total:.0f} 個專項未填『評審定案日(W)』、未納入交付率計算（可能漏填）")
            else:
                g["status"] = f"本季完成 {total} 個專項；6 週交付率 {r6:.0f}%、12 週 {r12:.0f}%"
            if r6 >= 70:
                g["good"].append(f"6 週交付率達 {r6:.0f}%，交付速度佳")
            if r6 < 50:
                g["bad"].append(f"6 週交付率僅 {r6:.0f}%，交付偏慢")
            if over12 > 0:
                g["bad"].append(f"{over12} 個專項交付超過 12 週")
        else:
            g["status"] = "本季無上線專項（Epic Roadmap_Item）"
    except Exception:
        g["status"] = "資料讀取失敗"
    out["三"] = g

    # 四、非專項吞吐量（live）
    g = {"title": "四、非專項吞吐量", "status": "", "good": [], "bad": [], "live": True}
    _bug = _f("s4_cur_bug"); _feat = _f("s4_cur_feat"); _tot = _f("s4_cur_total")
    g["status"] = f"本季非專項上版 {_tot:.0f} 件（bug {_bug:.0f}、feature {_feat:.0f}）"
    out["四"] = g

    # 五、交付週期（5.1 live；5.2 SAMPLE）
    g = {"title": "五、交付週期", "status": "", "good": [], "bad": [], "live": True}
    nn = _n_of("s51_cur_total_med")
    med_raw = str(data.get("s51_cur_total_med", ""))
    if nn in (None, 0) or med_raw.strip().startswith("－"):
        g["status"] = "本季整體交付週期資料不足"
    else:
        med = _f("s51_cur_total_med"); qoq = _f("s51_qoq_total")
        g["status"] = f"整體交付週期中位數 {med:.0f} 天（n={nn}）"
        if qoq <= -10:
            g["good"].append(f"整體交付週期較上季縮短 {abs(qoq):.0f}%")
        if qoq >= 10:
            g["bad"].append(f"整體交付週期較上季變長 {qoq:.0f}%")
        if nn <= 3:
            g["bad"].append(f"樣本不足（n={nn}），數值僅供參考")
    out["五"] = g

    # 六、人均工作天（live）
    g = {"title": "六、人均工作天", "status": "", "good": [], "bad": [], "live": True}
    eng = _f("s62_eng_avg_total"); qa = _f("s62_qa_avg_total")
    eng_raw = str(data.get("s62_eng_avg_total", "")).strip()
    if eng_raw.startswith("－") and qa == 0:
        g["status"] = "本季無人天資料"
    else:
        g["status"] = f"Eng 月均人均 {eng:.1f} 天、QA {qa:.1f} 天（觀測值 >11）"
        if eng >= 11:
            g["good"].append(f"Eng 人均 {eng:.1f} 天達標")
        else:
            g["bad"].append(f"Eng 人均 {eng:.1f} 天未達 11 天觀測值")
        if qa >= 11:
            g["good"].append(f"QA 人均 {qa:.1f} 天達標")
        else:
            g["bad"].append(f"QA 人均 {qa:.1f} 天未達 11 天觀測值")
    out["六"] = g

    # 七、在職人力（live）
    g = {"title": "七、在職人力", "status": "", "good": [], "bad": [], "live": True}
    pm = _f("s7_q_pm"); eng7 = _f("s7_q_be") + _f("s7_q_fe") + _f("s7_q_ios"); qa7 = _f("s7_q_qa")
    g["status"] = f"季均 PM {pm:.1f}、研發 {eng7:.1f}、QA {qa7:.1f} 人"
    try:
        cur_hc = get_avg_headcount(team, quarter)
        prev_hc = get_avg_headcount(team, prev_quarter(quarter))
        ct = sum(cur_hc.get(k, 0.0) for k in ("be", "fe", "ios", "qa", "pm"))
        pt = sum(prev_hc.get(k, 0.0) for k in ("be", "fe", "ios", "qa", "pm"))
        if pt and ct > pt:
            g["good"].append("團隊人力較上季成長")
        elif pt and ct < pt:
            g["bad"].append("團隊人力較上季減少")
    except Exception:
        pass
    if qa7 == 0:
        g["bad"].append("本季無 QA 人力")
    out["七"] = g

    return out
