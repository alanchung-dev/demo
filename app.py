"""
app.py — 人效報告 Streamlit 主應用
執行方式：streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
from data import load_data, get, quarter_label, get_prd_items, get_public_holidays, get_data_quality, get_delivery_weeks, get_delivery_trend_monthly, get_delivery_accuracy, build_report_assistant, is_quarter_designated, get_roadmap_items, get_s51_items, get_s51_scatter, get_s3_smoke_items, get_s52_outliers, S52_OBS_THRESHOLD, frozen_date, snapshot_time
from field_map import TEAM_NAMES, AVAILABLE_QUARTERS, DEFAULT_QUARTER

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="人效報告",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 整體背景 */
.stApp { background: #F5F7FA; }

/* Sidebar */
section[data-testid="stSidebar"] > div:first-child {
    background: #1C3557;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] p { color: #D6E4F7 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }

/* 報告 Header 區塊 */
.rpt-header {
    background: linear-gradient(135deg, #1C3557 0%, #2E75B6 100%);
    color: white; border-radius: 12px; padding: 22px 28px 18px;
    margin-bottom: 20px; box-shadow: 0 4px 15px rgba(28,53,87,.22);
}
.rpt-header h2 { color: white; margin: 0 0 4px; font-size: 1.6rem; }
.rpt-header .meta { font-size: 13px; opacity: .75; margin-top: 6px; }
.live-badge {
    display:inline-block; background:#70AD47; color:white;
    border-radius:12px; padding:2px 10px; font-size:11px; font-weight:600;
}
.demo-badge {
    display:inline-block; background:#ED7D31; color:white;
    border-radius:12px; padding:2px 10px; font-size:11px; font-weight:600;
}

/* Section / Sub-section 標題 */
.sec-title {
    background: #2E75B6; color: white;
    padding: 7px 16px; border-radius: 6px;
    font-size: 15px; font-weight: 700; margin: 18px 0 8px;
}
.sub-title {
    background: #5B9BD5; color: white;
    padding: 5px 14px; border-radius: 5px;
    font-size: 13px; font-weight: 600; margin: 12px 0 6px;
}

/* 表格 */
.rpt-tbl {
    width: 100%; border-collapse: collapse;
    font-size: 12.5px; margin-bottom: 14px;
}
.rpt-tbl th {
    background: #D6E4F7; color: #1C3557;
    font-weight: 700; padding: 7px 10px;
    text-align: center; border: 1px solid #BFBFBF;
    font-size: 12px; white-space: pre-wrap; line-height: 1.4;
}
.rpt-tbl td { padding: 6px 10px; border: 1px solid #BFBFBF; vertical-align: middle; }
.rpt-tbl .r0 td { background: #FFFFFF; }
.rpt-tbl .r1 td { background: #EAF3FB; }
.rpt-tbl .ref td {
    background: #FFF2CC; color: #7F7F7F;
    font-style: italic; font-size: 11.5px;
}
.rpt-tbl td.lbl { text-align: left; font-weight: 500; }
.rpt-tbl td.val { text-align: center; }

/* 觀察 / 議題 / 定義區塊 */
.block-label {
    font-size: 13px; font-weight: 700; color: #1C3557;
    margin: 14px 0 4px;
}
.obs-box {
    background: #F2F2F2; border-left: 5px solid #1C3557;
    padding: 12px 16px; border-radius: 0 8px 8px 0;
    margin-bottom: 6px; font-size: 13px; line-height: 1.75;
    white-space: pre-wrap;
}
.foc-box {
    background: #F2F2F2; border-left: 5px solid #ED7D31;
    padding: 12px 16px; border-radius: 0 8px 8px 0;
    margin-bottom: 10px; font-size: 13px; line-height: 1.75;
    white-space: pre-wrap;
}
.def-box {
    background: #EAF3FB; border: 1px solid #D6E4F7;
    padding: 14px 18px; border-radius: 8px;
    margin: 10px 0; font-size: 12px; line-height: 1.85;
}
.def-box b { color: #1C3557; }

/* Metric card */
.m-wrap { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.m-card {
    background: white; border-radius: 8px; padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.08); border-top: 3px solid #2E75B6;
    text-align: center; min-width: 110px; flex: 1;
}
.m-label { font-size: 11px; color: #7F7F7F; margin-bottom: 4px; }
.m-value { font-size: 24px; font-weight: 700; color: #1C3557; }
.m-delta { font-size: 11px; color: #7F7F7F; }

/* 參考資料連結 card */
.ref-card {
    background: white; border-radius: 8px; padding: 14px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.07); margin-bottom: 10px;
    display: flex; align-items: center; gap: 16px;
    border-left: 4px solid #2E75B6;
}
.ref-card .ref-title { font-weight: 600; color: #1C3557; font-size: 14px; }
.ref-card .ref-link { color: #2E75B6; font-size: 13px; word-break: break-all; }

/* 報告小助手卡片 */
.assist-box {
    border-left:4px solid #2E75B6; background:#F2F7FC; border-radius:6px;
    padding:10px 14px; margin:8px 0 12px; color:#1C3557;
}
.assist-row {
    margin:6px 0; padding:8px 12px; border-left:3px solid #2E75B6;
    background:#F7FAFD; border-radius:4px; color:#1C3557;
}
.astat { color:#555; }

</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def sec(text):
    st.markdown(f'<div class="sec-title">{text}</div>', unsafe_allow_html=True)

def sub(text):
    st.markdown(f'<div class="sub-title">{text}</div>', unsafe_allow_html=True)

def tbl(headers: list[str], rows: list[tuple]) -> str:
    """
    渲染 HTML 表格
    rows: list of (type, [cells])
      type: 'D'=奇數行, 'A'=偶數行(藍底), 'R'=參考基準(黃底)
    """
    h = ['<table class="rpt-tbl"><thead><tr>']
    for hd in headers:
        h.append(f'<th>{hd}</th>')
    h.append('</tr></thead><tbody>')
    for i, (rt, cells) in enumerate(rows):
        cls = 'ref' if rt == 'R' else f'r{i % 2}'
        h.append(f'<tr class="{cls}">')
        for j, c in enumerate(cells):
            td_cls = 'lbl' if j == 0 else 'val'
            h.append(f'<td class="{td_cls}">{c if c is not None else ""}</td>')
        h.append('</tr>')
    h.append('</tbody></table>')
    return ''.join(h)

def show_tbl(headers, rows):
    st.markdown(tbl(headers, rows), unsafe_allow_html=True)

def obs_focus(obs: str, focus: str):
    st.markdown('<div class="block-label">📋 現況觀察與說明</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="obs-box">{obs}</div>', unsafe_allow_html=True)
    st.markdown('<div class="block-label">🎯 關注重點與議題</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="foc-box">{focus}</div>', unsafe_allow_html=True)

def defbox(content: str):
    with st.expander("💡 數據指標定義", expanded=False):
        st.markdown(f'<div class="def-box">{content}</div>', unsafe_allow_html=True)

def render_assistant(block):
    """單一章節的『報告小助手』區塊（放在數據指標定義上方）"""
    if not block:
        return
    good = "".join(f"<li>{x}</li>" for x in block.get("good", [])) or "<li style='color:#9AA5B1'>—</li>"
    bad  = "".join(f"<li>{x}</li>" for x in block.get("bad", []))  or "<li style='color:#9AA5B1'>—</li>"
    st.markdown(
        '<div class="assist-box">'
        '<b>📌 報告小助手</b><br>'
        f'<b>季度狀況：</b>{block["status"]}'
        '<div style="margin-top:6px"><b style="color:#70AD47">✨ 亮點</b>'
        f'<ul style="margin:2px 0 6px 20px;padding:0">{good}</ul>'
        '<b style="color:#C00000">⚠️ 待改善</b>'
        f'<ul style="margin:2px 0 0 20px;padding:0">{bad}</ul></div></div>',
        unsafe_allow_html=True,
    )

def render_assistant_summary(assistant: dict):
    """🏠 概覽：彙整三~七章的報告小助手"""
    if not assistant:
        st.caption("請先在側邊欄選擇團隊，以顯示各章報告小助手總結")
        return
    parts = []
    for key in ("二", "三", "四", "五", "六", "七"):
        b = assistant.get(key)
        if not b:
            continue
        good = "／".join(b["good"]) or "—"
        bad  = "／".join(b["bad"]) or "—"
        parts.append(
            '<div class="assist-row">'
            f'<b>{b["title"]}</b>　<span class="astat">{b["status"]}</span><br>'
            f'<span style="color:#70AD47">✨ {good}</span>　'
            f'<span style="color:#C00000">⚠️ {bad}</span></div>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)

def num(v: str, default: float = 0.0) -> float:
    """字串轉浮點數，處理 '無'、'－'、'%'、'-' 等無效值"""
    try:
        return float(str(v).replace("%", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return default


CHART_COLORS = {
    "cur":     "#2E75B6",
    "prev":    "#9DC3E6",
    "accent":  "#ED7D31",
    "green":   "#70AD47",
    "red":     "#FF4B4B",
    "owner":   "#2E75B6",
    "support": "#9DC3E6",
    "total":   "#1C3557",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="sans-serif", size=12, color="#1C3557"),
    margin=dict(l=10, r=10, t=36, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(gridcolor="#E8EDF2", zerolinecolor="#E8EDF2"),
    yaxis=dict(gridcolor="#E8EDF2", zerolinecolor="#E8EDF2"),
)


def bar_chart(categories, series: list[dict], title="", horizontal=False, height=280):
    """
    series: [{"name": "本季", "values": [...], "color": "#..."}]
    """
    fig = go.Figure()
    orientation = "h" if horizontal else "v"
    for s in series:
        x, y = (s["values"], categories) if horizontal else (categories, s["values"])
        fig.add_trace(go.Bar(
            name=s["name"], x=x, y=y,
            orientation=orientation,
            marker_color=s.get("color", CHART_COLORS["cur"]),
            text=[f"{v}" if v else "" for v in s["values"]],
            textposition="outside" if not horizontal else "auto",
        ))
    fig.update_layout(**CHART_LAYOUT, title_text=title, height=height, barmode="group")
    return fig


def metric_row(items: list[tuple]):
    """
    items: [(label, value, delta, direction), ...]
      direction: "up_good"  → 上升是好事（需求量、完成數）
                 "down_good"→ 下降是好事（交付週期）
                 "target"   → 與固定目標比（人天）
                 None       → 純顯示，不上色
    delta 格式: "上季 X" 或 "目標 > 11 天" 或 "預期 X"
    """
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, delta = item[0], item[1], item[2]
        direction = item[3] if len(item) > 3 else None

        # 計算箭頭與顏色
        arrow = ""
        delta_color = "#7F7F7F"
        value_color = "#1C3557"   # 預設深藍（正常）
        try:
            cur_v = float(str(value).replace("%", "").replace(",", "").strip())
            if direction in ("up_good", "down_good"):
                prev_v = float(str(delta).replace("上季", "").replace("%", "").replace(",", "").strip())
                diff = cur_v - prev_v
                if diff > 0:
                    arrow = " ↑"
                    is_good = direction == "up_good"
                elif diff < 0:
                    arrow = " ↓"
                    is_good = direction == "down_good"
                else:
                    is_good = True
                delta_color = "#70AD47" if is_good else "#FF4B4B"
                value_color = "#1C3557" if is_good else "#FF4B4B"
            elif direction == "target":
                target_v = float(str(delta).replace("目標 >", "").replace("目標>", "").replace("天", "").strip())
                is_good = cur_v >= target_v
                delta_color = "#70AD47" if is_good else "#FF4B4B"
                value_color = "#1C3557" if is_good else "#FF4B4B"
        except (ValueError, TypeError):
            pass

        with col:
            st.markdown(
                f'<div class="m-card">'
                f'<div class="m-label">{label}</div>'
                f'<div class="m-value" style="color:{value_color}">{value}{arrow}</div>'
                f'<div class="m-delta" style="color:{delta_color}">{delta}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─── Team + Quarter selector（需在 load_data 之前）──────────────────────────
# 在 sidebar 建立下拉選單；若 TEAM_NAMES 為空則進入純 DEMO 模式
with st.sidebar:
    if TEAM_NAMES:
        selected_team = st.selectbox(
            "🏢 選擇團隊",
            options=TEAM_NAMES,
            key="team_selector",
        )
    else:
        selected_team = ""
        st.markdown(
            '<div style="color:#FFC107;font-size:12px;margin-bottom:4px;">'
            '⚙️ 請在 field_map.py 填入 TEAM_NAMES</div>',
            unsafe_allow_html=True,
        )

    selected_quarter = st.selectbox(
        "📅 選擇季度",
        options=AVAILABLE_QUARTERS,
        index=AVAILABLE_QUARTERS.index(DEFAULT_QUARTER),
        key="quarter_selector",
    )
    st.markdown("---")


# ─── Load data ────────────────────────────────────────────────────────────────
# 平時讀加速快照（秒開）；使用者按「立即更新」時對本隊強制即時計算（一次性）
_force_live = st.session_state.pop("_force_live", False)
data, is_live = load_data(selected_team, selected_quarter, live=_force_live)
designated = is_quarter_designated(selected_team, selected_quarter)
g = lambda key: get(data, key)
n = lambda key, d=0.0: num(get(data, key), d)
assistant = build_report_assistant(data, selected_team, selected_quarter) if selected_team else {}
YEAR = g("YEAR"); QUARTER = g("QUARTER")
TEAM = selected_team or g("TEAM_NAME")
QUARTER_LABEL = quarter_label(selected_quarter)   # e.g. "2026 Q1"

# 第七章月份標籤：依所選季度動態計算實際月份（Q1→1/2/3、Q2→4/5/6…），
# 與 data.compute_s7 的 month_start=(qnum-1)*3+1 對齊，避免寫死成 1/2/3 月。
_s7_qn   = int(QUARTER) if str(QUARTER).isdigit() else 1
_s7_year = int(YEAR) if str(YEAR).isdigit() else 0
def _s7_ym(offset: int) -> tuple[int, int]:
    m = (_s7_qn - 1) * 3 + 1 + offset
    return _s7_year + (m - 1) // 12, (m - 1) % 12 + 1
S7_MONTHS_LONG  = [f"{_s7_ym(i)[0]} 年 {_s7_ym(i)[1]} 月" for i in range(3)]  # 2026 年 4 月
S7_MONTHS_SHORT = [f"{_s7_ym(i)[0]}/{_s7_ym(i)[1]}月"     for i in range(3)]  # 2026/4月


# ─── Sidebar（接續已開啟的 with 區塊之後繼續渲染）─────────────────────────────
with st.sidebar:
    st.markdown(f"### 📊 {TEAM}")
    st.markdown(f"**{QUARTER_LABEL} 人效報告**")
    st.markdown("---")
    section = st.radio(
        "章節導覽",
        options=[
            "🏠 報告概覽",
            "一、季度發版情形",
            "二、專項 (Roadmap_Item) 季度交付結果",
            "三、上版專項 (Roadmap_Item) 上版吞吐量",
            "四、非專項吞吐量",
            "五、交付週期",
            "六、人均工作天",
            "七、在職人力",

            "八、資料品質總覽",
            "九、參考資料",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    badge = '<span class="live-badge">● LIVE</span>' if is_live else '<span class="demo-badge">● DEMO 模式</span>'
    st.markdown(badge, unsafe_allow_html=True)
    _snap_t = snapshot_time(selected_quarter)
    if is_live and _snap_t and not _force_live:
        st.caption(f"📸 資料快照：{_snap_t}")
    elif is_live:
        st.caption("資料每 5 分鐘自動更新")
    elif selected_team and not designated:
        st.caption(f"「{selected_team} {selected_quarter}」尚無資料，\n顯示樣本資料")
    else:
        st.caption("未連接 Google Sheets，\n顯示樣本資料")
    st.caption("🧪 這是作品集展示版，資料為合成假資料（不連任何外部服務）。")


# ─── Report Header ────────────────────────────────────────────────────────────
badge_html = (
    '<span class="live-badge">● DEMO — 合成範例資料（作品集展示版）</span>'
    if is_live else
    (f'<span class="demo-badge">● DEMO — 「{selected_team} {selected_quarter}」尚無資料（樣本資料）</span>'
     if selected_team and not designated else
     '<span class="demo-badge">● DEMO 樣本資料</span>')
)
_frozen_on = frozen_date(selected_quarter)
_frozen_meta = f' &nbsp;｜&nbsp; 🔒 封版日：{_frozen_on}' if _frozen_on else ""
st.markdown(
    f'<div class="rpt-header">'
    f'<h2>📊 {TEAM} — 人效報告</h2>'
    f'{badge_html}'
    f'<div class="meta">'
    f'{QUARTER_LABEL} &nbsp;｜&nbsp; '
    f'報告日期：{g("REPORT_DATE")} &nbsp;｜&nbsp; '
    f'資料截止：{g("DATA_CUTOFF_DATE")}'
    f'{_frozen_meta}'
    f'</div></div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# 報告概覽
# ══════════════════════════════════════════════════════════════════════════════
if section == "🏠 報告概覽":
    st.markdown("### 📌 報告小助手總結（各章重點）")
    render_assistant_summary(assistant)
    st.markdown("---")

    st.markdown("### 本季重點數字")

    metric_row([
        ("本季需求總數量",         g("s21_cur_total_req"),   f"上季 {g('s21_prev_total_req')}",   "up_good"),
        ("本季實際完成需求量",     g("s24_cur_done_total"),  f"上季 {g('s24_prev_done_total')}",  "up_good"),
        ("本季非專項上版需求數",   g("s4_cur_total"),         f"上季 {g('s4_prev_total')}",         "up_good"),
        ("常規版本發版次數",       g("s1_cur_normal_freq"),  f"上季 {g('s1_prev_normal_freq')}",  "up_good"),
        ("專項(Roadmap_Item)整體交付週期（天）", g("s51_cur_total_avg"),   f"上季 {g('s51_prev_total_avg')}",   "down_good"),
    ])

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        sec("本季概況")
        show_tbl(
            ["指標", "本季", "上季"],
            [
                ("D", ["Roadmap 需求總數",          g("s21_cur_total_req"),    g("s21_prev_total_req")]),
                ("A", ["本季預估完成數量",           g("s21_cur_est_done"),     g("s21_prev_est_done")]),
                ("D", ["實際完成需求量",             g("s24_cur_done_total"),   g("s24_prev_done_total")]),
                ("A", ["預估目標達成比例",           g("s24_cur_target_total"), g("s24_prev_target_total")]),
                ("D", ["非專項上版需求數",           g("s4_cur_total"),         g("s4_prev_total")]),
                ("A", ["常規發版次數",               g("s1_cur_normal_freq"),   g("s1_prev_normal_freq")]),
                ("D", ["非專項 Small_Ticket交付平均週期(天)", g("s52_cur_total"),        g("s52_prev_total")]),
            ],
        )
    with col2:
        sec("在職人力快覽")
        show_tbl(
            ["月份", "PM", "BE", "FE", "iOS", "QA", "比例"],
            [
                ("D", [S7_MONTHS_SHORT[0], g("s7_m1_pm"), g("s7_m1_be"), g("s7_m1_fe"), g("s7_m1_ios"), g("s7_m1_qa"), g("s7_m1_ratio")]),
                ("A", [S7_MONTHS_SHORT[1], g("s7_m2_pm"), g("s7_m2_be"), g("s7_m2_fe"), g("s7_m2_ios"), g("s7_m2_qa"), g("s7_m2_ratio")]),
                ("D", [S7_MONTHS_SHORT[2], g("s7_m3_pm"), g("s7_m3_be"), g("s7_m3_fe"), g("s7_m3_ios"), g("s7_m3_qa"), g("s7_m3_ratio")]),
                ("R", [f"{QUARTER_LABEL} 季均", g("s7_q_pm"), g("s7_q_be"), g("s7_q_fe"), g("s7_q_ios"), g("s7_q_qa"), g("s7_q_ratio")]),
            ],
        )

    # ── 本季公眾假期（工作日） ────────────────────────────────────────────────
    st.markdown("---")
    holidays_data = get_public_holidays(selected_quarter)
    tw_h = holidays_data.get("TW", [])
    hk_h = holidays_data.get("HK", [])
    cn_h = holidays_data.get("CN", [])

    col_tw, col_hk, col_cn = st.columns(3)
    with col_tw:
        sec(f"TW 辦公室 — 本季工作日假期 {len(tw_h)} 天")
        if tw_h:
            show_tbl(
                ["日期", "假期名稱"],
                [("D" if i % 2 == 0 else "A", [d.strftime("%Y-%m-%d (%a)"), name])
                 for i, (d, name) in enumerate(tw_h)],
            )
        else:
            st.caption("本季無工作日假期")
    with col_hk:
        sec(f"HK 辦公室 — 本季工作日假期 {len(hk_h)} 天")
        if hk_h:
            show_tbl(
                ["日期", "假期名稱"],
                [("D" if i % 2 == 0 else "A", [d.strftime("%Y-%m-%d (%a)"), name])
                 for i, (d, name) in enumerate(hk_h)],
            )
        else:
            st.caption("本季無工作日假期")
    with col_cn:
        sec(f"CN 辦公室 — 本季工作日假期 {len(cn_h)} 天")
        if cn_h:
            show_tbl(
                ["日期", "假期名稱"],
                [("D" if i % 2 == 0 else "A", [d.strftime("%Y-%m-%d (%a)"), name])
                 for i, (d, name) in enumerate(cn_h)],
            )
        else:
            st.caption("本季無工作日假期")
    st.caption("📌 資料來源：[python-holidays](https://python-holidays.readthedocs.io/)。僅計算週一至週五的假期。")


# ══════════════════════════════════════════════════════════════════════════════
# 一、季度發版情形
# ══════════════════════════════════════════════════════════════════════════════
elif section == "一、季度發版情形":
    st.caption("以「版本」維度觀測整季度發版情況，藉由常規更版次數，了解該產品線的迭代速度與能力外，也能觀察 Hotfix / Fastlane 版本頻率，作為產出提升的反指標參考之一。")
    st.caption("🏢 主要關注部門：研發部門、測試部門")

    # ── 分組長條圖：各版本類型 本季 vs 上季 ────────────────────────────────────
    release_cats = ["常規發版", "Hotfix", "Fastlane Bug", "Fastlane Feature", "版本回滾", "延遲上版"]
    release_cur  = [n("s1_cur_normal_freq"), n("s1_cur_hotfix"), n("s1_cur_fl_bug"),
                    n("s1_cur_fl_feat"), n("s1_cur_rollback"), n("s1_cur_delay")]
    release_prev = [n("s1_prev_normal_freq"), n("s1_prev_hotfix"), n("s1_prev_fl_bug"),
                    n("s1_prev_fl_feat"), n("s1_prev_rollback"), n("s1_prev_delay")]
    fig1 = bar_chart(
        release_cats,
        [{"name": f"{QUARTER_LABEL} 本季", "values": release_cur,  "color": CHART_COLORS["cur"]},
         {"name": "上季",                  "values": release_prev, "color": CHART_COLORS["prev"]}],
        title="發版各類型數量比較", height=300,
    )
    st.plotly_chart(fig1, use_container_width=True)

    metric_row([
        ("本季常規發版次數", g("s1_cur_normal_freq"), f"預期 {g('s1_cur_plan_freq')} 次"),
        ("本季 Hotfix",      g("s1_cur_hotfix"),      f"上季 {g('s1_prev_hotfix')}"),
        ("Fastlane（Bug）",  g("s1_cur_fl_bug"),      f"上季 {g('s1_prev_fl_bug')}"),
        ("Fastlane（Feature）", g("s1_cur_fl_feat"),  f"上季 {g('s1_prev_fl_feat')}"),
        ("版本回滾數",       g("s1_cur_rollback"),    f"上季 {g('s1_prev_rollback')}"),
        ("常規版本延遲上版", g("s1_cur_delay"),       f"上季 {g('s1_prev_delay')}"),
    ])

    col1, col2 = st.columns([3, 1])
    with col1:
        sub("發版次數")
        show_tbl(
            ["", "預期常規\n版本頻率", "常規版本\n頻率", "Hotfix\n發版數", "Fastlane\nBug 發版數", "Fastlane\nFeature &\nEnhancement 發版數"],
            [
                ("D", ["本季實際數量", g("s1_cur_plan_freq"), g("s1_cur_normal_freq"), g("s1_cur_hotfix"), g("s1_cur_fl_bug"), g("s1_cur_fl_feat")]),
                ("A", ["上季實際數量", g("s1_prev_plan_freq"), g("s1_prev_normal_freq"), g("s1_prev_hotfix"), g("s1_prev_fl_bug"), g("s1_prev_fl_feat")]),
            ],
        )
    with col2:
        sub("版本異常")
        show_tbl(
            ["", "版本回滾數", "延遲上版"],
            [
                ("D", ["本季", g("s1_cur_rollback"), g("s1_cur_delay")]),
                ("A", ["上季", g("s1_prev_rollback"), g("s1_prev_delay")]),
            ],
        )

    defbox(
        "<b>預期常規版本頻率：</b>團隊本季預計的發版頻率數量，不考慮國定假日、特殊封版狀況。<br>"
        "<b>常規版本頻率：</b>團隊實際常規上版的「頻率」；在常規發版頻率中完成部署的任何專案，頻率計算為一次。<br>"
        "<b>Hotfix：</b>為修復最高緊急度的線上問題，目標是問題提報當天必須修復，通常版本裡僅會有一張 Jira 卡。<br>"
        "<b>Fastlane Bug fix：</b>嚴重度次之的線上問題，目標也是在下一次常規發版前儘速解決。<br>"
        "<b>Fastlane Feature & Enhancement：</b>因改動範圍大，為降低上版後的風險與影響範圍，另安排時間做發版。<br>"
        "<b>資料來源：</b>發版紀錄來源表（依季度、團隊對應）。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 二、專項 (Roadmap_Item) 季度交付結果
# ══════════════════════════════════════════════════════════════════════════════
elif section == "二、專項 (Roadmap_Item) 季度交付結果":
    st.caption("了解團隊在專項(Roadmap_Item)部分的基本交付情況與目標管理結果，包含「產品」、「設計」、「研發」、「測試」各個環節。")
    st.caption("🏢 主要關注部門：商務 / 產品 / 設計 / 研發 / 測試")

    tab1, tab2, tab3, tab4 = st.tabs(["2.1 團隊專項(Roadmap_Item)交付樣貌", "2.2 產品（PM）", "2.3 設計（UED）", "2.4 研測 + 2.5 顆粒度"])

    with tab1:
        (col1,) = st.columns(1)
        with col1:
            metric_row([
                ("本季需求總數量",    g("s21_cur_total_req"),  f"環比 {g('s21_req_qoq')}"),
                ("本季預估完成數量",  g("s21_cur_est_done"),   f"目標達成率 {g('s21_cur_est_rate')}"),
                ("本季插件需求數量",  g("s21_cur_addon"),      f"環比 {g('s21_addon_qoq')}"),
            ])
            # ── 需求量 vs 預估完成量 長條圖 ──────────────────────────────────
            fig21 = bar_chart(
                ["需求總數量", "預估完成數量", "插件需求數量"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s21_cur_total_req"), n("s21_cur_est_done"), n("s21_cur_addon")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s21_prev_total_req"), n("s21_prev_est_done"), n("s21_prev_addon")], "color": CHART_COLORS["prev"]}],
                title="2.1 團隊專項(Roadmap_Item)交付樣貌", height=260,
            )
            st.plotly_chart(fig21, use_container_width=True)
            show_tbl(
                ["指標", "本季", "上季"],
                [
                    ("D", ["需求總數量",         g("s21_cur_total_req"),  g("s21_prev_total_req")]),
                    ("A", ["需求季度環比增長",   g("s21_req_qoq"),        "—"]),
                    ("D", ["實際完成數量（主幹 Raw；括號為 Roadmap 檔）",
                           f'{g("s21_cur_act_done")}（Roadmap {g("s21_cur_act_done_rm")}）',
                           f'{g("s21_prev_act_done")}（Roadmap {g("s21_prev_act_done_rm")}）']),
                    ("D", ["預估完成數量",        g("s21_cur_est_done"),   g("s21_prev_est_done")]),
                    ("A", ["預估目標達成比例",   g("s21_cur_est_rate"),   g("s21_prev_est_rate")]),
                    ("R", ["參考重點指標數據",   "100%",                  "100%"]),
                    ("D", ["插件需求數量",        g("s21_cur_addon"),      g("s21_prev_addon")]),
                    ("A", ["插件需求季度環比增長",g("s21_addon_qoq"),     "—"]),
                ],
            )

            # ── 🔍 Roadmap 檔對照（輔助確認）；僅已封版團隊顯示 ──────────────────
            if designated:
                rm = get_roadmap_items(selected_team, selected_quarter)
                sub("🔍 Roadmap 檔對照（輔助）— 展開逐項核對")
                st.caption("主表「實際完成量」以 Raw Data 為主幹；此處為 PMO Roadmap 檔的數字與項目，供交叉確認差異來源。")
                for _k, _lbl in [("total_req", "需求總數量"), ("act_done", "實際完成數量"),
                                 ("est_done", "預估完成數量"), ("addon", "插件需求數量")]:
                    _items = rm[_k]["items"]
                    with st.expander(f"{_lbl}（{rm[_k]['count']} 項）"):
                        if _items:
                            show_tbl(["#", "項目名稱"],
                                     [("D" if i % 2 == 0 else "A", [str(i + 1), nm])
                                      for i, nm in enumerate(_items)])
                        else:
                            st.caption("無項目")

            # ── 專項(Roadmap_Item)交付準確率 ──────────────────────────────────
            sub("專項 (Roadmap_Item) 交付準確率")
            if selected_team:
                acc = get_delivery_accuracy(selected_team, selected_quarter)
                if acc["total"] == 0:
                    st.caption("本季無 Epic Roadmap_Item 上線項目")
                else:
                    show_tbl(
                        ["指標", "項目數", "比例"],
                        [
                            ("D", ["本季整體上線項目", str(acc["total"]), "100%"]),
                            ("A", [f'<span style="color:{CHART_COLORS["green"]}">準時上線</span>',      str(acc["on_time"]["count"]),     acc["on_time"]["rate"]]),
                            ("D", [f'<span style="color:{CHART_COLORS["red"]}">未準時</span>',          str(acc["not_on_time"]["count"]), acc["not_on_time"]["rate"]]),
                            ("A", [f'<span style="color:{CHART_COLORS["red"]}">延遲超過 2 週</span>',    str(acc["delayed_2w"]["count"]),  acc["delayed_2w"]["rate"]]),
                        ],
                    )

                    def _names_tbl(items):
                        if items:
                            show_tbl(["#", "項目名稱"],
                                     [("D" if i % 2 == 0 else "A", [str(i + 1), nm]) for i, nm in enumerate(items)])
                        else:
                            st.caption("無")

                    c_ok, c_no, c_late = st.columns(3)
                    with c_ok:
                        sub(f"✅ 準時上線（{acc['on_time']['count']}）")
                        _names_tbl(acc["on_time"]["items"])
                    with c_no:
                        sub(f"⚠️ 未準時（{acc['not_on_time']['count']}）")
                        _names_tbl(acc["not_on_time"]["items"])
                    with c_late:
                        sub(f"🔴 延遲超過 2 週（{acc['delayed_2w']['count']}）")
                        _names_tbl(acc["delayed_2w"]["items"])
            else:
                st.caption("請先在側邊欄選擇團隊")

    with tab2:
        # ── 2.2 PRD 輸出數 & 評審數：Owner / Support / Total 本季 vs 上季 ──
        col_c, col_t = st.columns(2)
        with col_c:
            fig22_prd = bar_chart(
                ["Owner", "Support", "Total"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s22_cur_prd_owner"), n("s22_cur_prd_support"), n("s22_cur_prd_total")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s22_prev_prd_owner"), n("s22_prev_prd_support"), n("s22_prev_prd_total")], "color": CHART_COLORS["prev"]}],
                title="PRD 輸出數", height=250,
            )
            st.plotly_chart(fig22_prd, use_container_width=True)
        with col_t:
            fig22_rev = bar_chart(
                ["Owner", "Support", "Total"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s22_cur_rev_owner"), n("s22_cur_rev_support"), n("s22_cur_rev_total")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s22_prev_rev_owner"), n("s22_prev_rev_support"), n("s22_prev_rev_total")], "color": CHART_COLORS["prev"]}],
                title="PRD 評審數", height=250,
            )
            st.plotly_chart(fig22_rev, use_container_width=True)
        show_tbl(
            ["指標", "負責主導角色\n(Owner)", "支援/協作角色\n(Support)", "總數"],
            [
                ("D", ["本季 PRD 輸出數",        g("s22_cur_prd_owner"),  g("s22_cur_prd_support"),  g("s22_cur_prd_total")]),
                ("A", ["上季 PRD 輸出數",        g("s22_prev_prd_owner"), g("s22_prev_prd_support"), g("s22_prev_prd_total")]),
                ("D", ["PRD 輸出數環比",         g("s22_prd_qoq_owner"),  "—",                       g("s22_prd_qoq_total")]),
                ("A", ["本季 PRD 評審數",        g("s22_cur_rev_owner"),  g("s22_cur_rev_support"),  g("s22_cur_rev_total")]),
                ("D", ["上季 PRD 評審數",        g("s22_prev_rev_owner"), g("s22_prev_rev_support"), g("s22_prev_rev_total")]),
                ("A", ["PRD 評審數環比",         g("s22_rev_qoq_owner"),  "—",                       g("s22_rev_qoq_total")]),
                ("D", ["本季 PM 人均 PRD 輸出量",g("s22_cur_avg_owner"),  g("s22_cur_avg_support"),  g("s22_cur_avg_total")]),
                ("A", ["上季 PM 人均 PRD 輸出量",g("s22_prev_avg_owner"), g("s22_prev_avg_support"), g("s22_prev_avg_total")]),
                ("D", ["產品人均 PRD 輸出量環比",g("s22_avg_qoq_owner"),  "—",                       g("s22_avg_qoq_total")]),
            ],
        )
        # ── 本季通過項目清單 ──────────────────────────────────────────────────
        if selected_team:
            prd_items = get_prd_items(selected_team, selected_quarter)
            col_out, col_rev = st.columns(2)
            with col_out:
                sub(f"本季 PRD 輸出通過項目（{len(prd_items['output'])} 項）")
                if prd_items["output"]:
                    rows_out = [("D" if i % 2 == 0 else "A", [str(i+1), name])
                                for i, name in enumerate(prd_items["output"])]
                    show_tbl(["#", "項目名稱"], rows_out)
                else:
                    st.caption("本季無 PRD 輸出通過項目")
            with col_rev:
                sub(f"本季 PRD 評審通過項目（{len(prd_items['review'])} 項）")
                if prd_items["review"]:
                    rows_rev = [("D" if i % 2 == 0 else "A", [str(i+1), name])
                                for i, name in enumerate(prd_items["review"])]
                    show_tbl(["#", "項目名稱"], rows_rev)
                else:
                    st.caption("本季無 PRD 評審通過項目")

    with tab3:
        # ── 2.3 UED 稿輸出數：專項(Roadmap_Item) & Small_Ticket 本季 vs 上季 ──────────────
        col_c, col_t = st.columns(2)
        with col_c:
            fig23_main = bar_chart(
                ["總數", "PRD 評審前交付", "開始開發前交付"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s23_cur_total"), n("s23_cur_prd_cnt"), n("s23_cur_dev_cnt")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s23_prev_total"), n("s23_prev_prd_cnt"), n("s23_prev_dev_cnt")], "color": CHART_COLORS["prev"]}],
                title="UED 稿輸出數（專項(Roadmap_Item)）", height=260,
            )
            st.plotly_chart(fig23_main, use_container_width=True)
        with col_t:
            fig23_sm = bar_chart(
                ["總數", "開始開發前交付"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s23_cur_sm_total"), n("s23_cur_sm_dev_cnt")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s23_prev_sm_total"), n("s23_prev_sm_dev_cnt")], "color": CHART_COLORS["prev"]}],
                title="UED 稿輸出數（Small_Ticket）", height=260,
            )
            st.plotly_chart(fig23_sm, use_container_width=True)
        show_tbl(
            ["", "總數", "PRD 評審前\n交付個數", "PRD 評審前\n交付率（%）", "開始開發前\n交付數", "開始開發前\n交付率（%）"],
            [
                ("D", ["本季 UED 稿輸出數（專項(Roadmap_Item)）",g("s23_cur_total"),     g("s23_cur_prd_cnt"),  g("s23_cur_prd_rate"),  g("s23_cur_dev_cnt"),  g("s23_cur_dev_rate")]),
                ("R", ["參考重點指標數據",          "—",                   "—",                   "100.00%",              "—",                   "—"]),
                ("A", ["上季 UED 稿輸出數（專項(Roadmap_Item)）",g("s23_prev_total"),    g("s23_prev_prd_cnt"), g("s23_prev_prd_rate"), g("s23_prev_dev_cnt"), g("s23_prev_dev_rate")]),
                ("D", ["季度環比（%）",             "—",                   "—",                   "—",                    "—",                   "—"]),
                ("A", ["本季 UED 稿輸出數（Small_Ticket）",g("s23_cur_sm_total"),  "無評審",              "無評審",               g("s23_cur_sm_dev_cnt"),g("s23_cur_sm_dev_rate")]),
                ("D", ["上季 UED 稿輸出數（Small_Ticket）",g("s23_prev_sm_total"), "無評審",              "無評審",               g("s23_prev_sm_dev_cnt"),g("s23_prev_sm_dev_rate")]),
                ("A", ["季度環比（%）",             "—",                   "—",                   "—",                    "—",                   "—"]),
            ],
        )

    with tab4:
        sub("2.4 研測（RD & QA）交付結果及目標達成率")
        col1, col2 = st.columns(2)
        with col1:
            # ── 完成量 Owner/Support 分組長條 ──────────────────────────────
            fig24 = bar_chart(
                ["Owner", "Support", "Total"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s24_cur_done_owner"), n("s24_cur_done_support"), n("s24_cur_done_total")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s24_prev_done_owner"), n("s24_prev_done_support"), n("s24_prev_done_total")], "color": CHART_COLORS["prev"]}],
                title="研測實際完成需求量", height=260,
            )
            st.plotly_chart(fig24, use_container_width=True)
            show_tbl(
                ["指標", "負責主導角色\n(Owner)", "支援/協作角色\n(Support)", "總計"],
                [
                    ("D", ["本季預估完成數量",     g("s24_cur_est_owner"),    g("s24_cur_est_support"),    g("s24_cur_est_total")]),
                    ("A", ["本季實際完成需求量",   g("s24_cur_done_owner"),   g("s24_cur_done_support"),   g("s24_cur_done_total")]),
                    ("D", ["本季實際交付比例",     g("s24_cur_ratio_owner"),  g("s24_cur_ratio_support"),  g("s24_cur_ratio_total")]),
                    ("A", ["本季預估目標達成比例", g("s24_cur_target_owner"), g("s24_cur_target_support"), g("s24_cur_target_total")]),
                    ("D", ["上季預估完成數量",     g("s24_prev_est_owner"),   g("s24_prev_est_support"),   g("s24_prev_est_total")]),
                    ("A", ["上季實際完成需求量",   g("s24_prev_done_owner"),  g("s24_prev_done_support"),  g("s24_prev_done_total")]),
                    ("D", ["上季實際交付比例",     g("s24_prev_ratio_owner"), g("s24_prev_ratio_support"), g("s24_prev_ratio_total")]),
                    ("A", ["上季預估目標達成比例", g("s24_prev_target_owner"),g("s24_prev_target_support"),g("s24_prev_target_total")]),
                ],
            )
        with col2:
            sub("2.5 專項(Roadmap_Item)顆粒度補充（人天）")
            # ── Eng / QA 單個專項(Roadmap_Item)工作量：各階段 本季 vs 上季 ─────────────────
            fig25_eng = bar_chart(
                ["研發階段", "研發前置準備", "不涉代碼任務", "總計"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s25_cur_eng_dev"),  n("s25_cur_eng_pre"),  n("s25_cur_eng_nc"),  n("s25_cur_eng_total")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s25_prev_eng_dev"), n("s25_prev_eng_pre"), n("s25_prev_eng_nc"), n("s25_prev_eng_total")], "color": CHART_COLORS["prev"]}],
                title="單個專項(Roadmap_Item) Eng 工作量（人天）", height=220,
            )
            st.plotly_chart(fig25_eng, use_container_width=True)
            fig25_qa = bar_chart(
                ["研發階段", "研發前置準備", "不涉代碼任務", "總計"],
                [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s25_cur_qa_dev"),  n("s25_cur_qa_pre"),  n("s25_cur_qa_nc"),  n("s25_cur_qa_total")],  "color": CHART_COLORS["cur"]},
                 {"name": "上季",                  "values": [n("s25_prev_qa_dev"), n("s25_prev_qa_pre"), n("s25_prev_qa_nc"), n("s25_prev_qa_total")], "color": CHART_COLORS["prev"]}],
                title="單個專項(Roadmap_Item) QA 工作量（人天）", height=220,
            )
            st.plotly_chart(fig25_qa, use_container_width=True)
            show_tbl(
                ["指標", "研發階段", "研發前置\n準備作業", "不涉及代碼\n改動任務", "總計"],
                [
                    ("D", ["本季單個專項(Roadmap_Item) Eng 工作量", g("s25_cur_eng_dev"),  g("s25_cur_eng_pre"),  g("s25_cur_eng_nc"),  g("s25_cur_eng_total")]),
                    ("A", ["上季單個專項(Roadmap_Item) Eng 工作量", g("s25_prev_eng_dev"), g("s25_prev_eng_pre"), g("s25_prev_eng_nc"), g("s25_prev_eng_total")]),
                    ("D", ["Eng 工作量季度環比增長",  g("s25_qoq_eng_dev"),  g("s25_qoq_eng_pre"),  g("s25_qoq_eng_nc"),  g("s25_qoq_eng_total")]),
                    ("A", ["本季單個專項(Roadmap_Item) QA 工作量",  g("s25_cur_qa_dev"),   g("s25_cur_qa_pre"),   g("s25_cur_qa_nc"),   g("s25_cur_qa_total")]),
                    ("D", ["上季單個專項(Roadmap_Item) QA 工作量",  g("s25_prev_qa_dev"),  g("s25_prev_qa_pre"),  g("s25_prev_qa_nc"),  g("s25_prev_qa_total")]),
                    ("A", ["QA 工作量季度環比增長",   g("s25_qoq_qa_dev"),   g("s25_qoq_qa_pre"),   g("s25_qoq_qa_nc"),   g("s25_qoq_qa_total")]),
                ],
            )

    render_assistant(assistant.get("二"))
    defbox(
        # ── 【2.1 團隊專項(Roadmap_Item)交付樣貌】───────────────────────────
        "<b>【2.1 團隊專項(Roadmap_Item)交付樣貌】（live）</b>來源：<b>實際完成量＝Raw Data 主幹</b>；<b>需求總／預估完成／插件＝外部 PMO Roadmap Risk Assessment 檔</b>（與下方「項目明細」同源）。採 PMO 權威表公式但<b>全報告不分重要性 High</b>，故數字大於 PMO 官方 High 版；各季欄位不同見 docs。<br>"
        "・<b>需求總數量：</b>角色 Owner/Support、<b>本季期望目標(U 欄)含「上線」</b>、且狀態未排除的專項數。<br>"
        "・<b>實際完成數量（主幹＝Raw Data）：</b>本季實際上線的 Epic + Roadmap_Item（R 落本季）數，與交付準確率母體、三章完成量一致；括號內為 PMO Roadmap 檔的實際完成數當輔助（下方「🔍 Roadmap 檔對照」可展開逐項核）。<br>"
        "・<b>預估完成數量：</b>季初風險評估=Safe、<b>本季期望目標(U 欄)含「上線」</b>的專項數。<br>"
        "・<b>預估目標達成比例：</b>實際完成數量(Raw) ÷ 預估完成數量(Roadmap)（預估完成為 0 時顯示「－」）。<br>"
        "・<b>插件需求數量：</b>本季新加入 Roadmap 的插件（插件欄=Y）專項數。<br>"
        "・<b>交付準確率：</b>準時＝R(New Target Delivery Date) ≤ Q(First Target Delivery Date)（如期或提早都算準時）；未準時＝R > Q（只有確實延後才算，提早不列入）；延遲超過 2 週＝R − Q > 14 日曆天（未準時子集）；比例＝各類項目數 ÷ 整體上線項目數。<br>"
        "・<b>環比</b>＝(本季−上季)÷上季；已封版季度（如 2026Q1）的 2.1 數據已凍結為快照、不再變動，表頭顯示「🔒 封版日」。<br>"
        # ── 【2.2 產品（PM）】────────────────────────────────────────────────
        "<b>【2.2 產品（PM）】（live）</b>來源 Raw Data（母體 Issue Type=Epic、PRD Size∈S/M/L/XL），分 Owner/Support。<br>"
        "・<b>PRD 輸出數：</b>季度內 PM 針對此團隊專項(Roadmap_Item)所輸出的產品規格書（依 Z 欄認季），不限形式；非專項不計。<br>"
        "・<b>PRD 評審數：</b>季度內 PMO 針對團隊主導項目完成之產品規格書舉辦的評審會議（依 W 欄認季）。<br>"
        "・<b>PM 人均 PRD 輸出量：</b>專項(Roadmap_Item) PRD 輸出數 ÷ 本季產品經理季均人數。<br>"
        # ── 【2.3 設計（UED）】──────────────────────────────────────────────
        "<b>【2.3 設計（UED）】（live）</b>母體＝<b>Mockup 完成日（Mockup Complete Date）落在本季</b>的項目（<b>不綁本季是否上線</b>，只計本季實際交付的 Mockup、排除陳年舊卡；專項／Small_Ticket 一致）。<br>"
        "・<b>PRD 評審前交付率：</b>Mockup 完成日 ≤ PRD/TRD Review Final Date ÷ 稿輸出數。<br>"
        "・<b>開始開發前交付率：</b>Mockup 完成日 ≤ Development Start Date ÷ 稿輸出數；Small_Ticket 無評審 → 只算開始開發前。<br>"
        # ── 【2.4 研測（RD & QA）】──────────────────────────────────────────
        "<b>【2.4 研測（RD & QA）】（live）</b>實際完成需求量＝三章完成量（本季上線 Epic+Roadmap，依角色）；預估完成＝2.1 預估完成（Safe＋本季期望目標含上線）依角色；實際交付比例＝實際完成 ÷ 需求總(2.1)；預估目標達成比例＝實際完成 ÷ 預估完成。<br>"
        # ── 【2.5 顆粒度】───────────────────────────────────────────────────
        "<b>【2.5 顆粒度】（live）</b>本季上線 Item Type=Roadmap_Item 子卡工作量：研發階段=Story+Fix、前置準備=Survey、不涉代碼=Task；Eng=前後端+iOS、QA=測試；÷ 本季上線專項數(Epic 個數)＝單個專項人天；環比=(本季−上季)÷上季。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 三、上版專項 (Roadmap_Item) 上版吞吐量
# ══════════════════════════════════════════════════════════════════════════════
elif section == "三、上版專項 (Roadmap_Item) 上版吞吐量":
    st.caption("以「成本管理」視角，觀測每個團隊的總人數與專項(Roadmap_Item)吞吐量比例，進而設定吞吐目標。Director 層級以下的人力皆會被認列為團隊成本。")
    st.caption("🏢 主要關注部門：研發部門、測試部門")

    tab1, tab2, tab3 = st.tabs(["完成量 & 吞吐量", "Smoke Test", "6/12 周交付率"])

    with tab1:
        # ── 人均吞吐量：Eng / QA 本季 vs 上季 ──────────────────────────────
        fig3_tp = bar_chart(
            ["Eng Owner", "Eng Support", "Eng Total", "QA Owner", "QA Support", "QA Total"],
            [{"name": f"{QUARTER_LABEL} 本季",
              "values": [n("s3_cur_eng_tp_owner"), n("s3_cur_eng_tp_support"), n("s3_cur_eng_tp_total"),
                         n("s3_cur_qa_tp_owner"),  n("s3_cur_qa_tp_support"),  n("s3_cur_qa_tp_total")],
              "color": CHART_COLORS["cur"]},
             {"name": "上季",
              "values": [n("s3_prev_eng_tp_owner"), n("s3_prev_eng_tp_support"), n("s3_prev_eng_tp_total"),
                         n("s3_prev_qa_tp_owner"),  n("s3_prev_qa_tp_support"),  n("s3_prev_qa_tp_total")],
              "color": CHART_COLORS["prev"]}],
            title="專項(Roadmap_Item)季度人均吞吐量（Eng / QA）", height=300,
        )
        st.plotly_chart(fig3_tp, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            sub("實際完成需求量")
            show_tbl(
                ["", "負責主導角色\n(Owner)", "支援/協作角色\n(Support)", "總計"],
                [
                    ("D", ["本季 實際完成需求量", g("s3_cur_done_owner"),  g("s3_cur_done_support"),  g("s3_cur_done_total")]),
                    ("A", ["本季 實際完成比例",   g("s3_cur_ratio_owner"), g("s3_cur_ratio_support"), g("s3_cur_ratio_total")]),
                    ("D", ["上季 實際完成需求量", g("s3_prev_done_owner"), g("s3_prev_done_support"), g("s3_prev_done_total")]),
                    ("A", ["上季 實際完成比例",   g("s3_prev_ratio_owner"),g("s3_prev_ratio_support"),g("s3_prev_ratio_total")]),
                ],
            )
            sub("開發季度人均吞吐量")
            show_tbl(
                ["", "Owner", "Support", "總計"],
                [
                    ("D", ["本季開發季度人均吞吐量",   g("s3_cur_eng_tp_owner"),  g("s3_cur_eng_tp_support"),  g("s3_cur_eng_tp_total")]),
                    ("A", ["上季開發季度人均吞吐量",   g("s3_prev_eng_tp_owner"), g("s3_prev_eng_tp_support"), g("s3_prev_eng_tp_total")]),
                    ("D", ["開發人均吞吐量季度環比增長",g("s3_qoq_eng_tp_owner"),  g("s3_qoq_eng_tp_support"),  g("s3_qoq_eng_tp_total")]),
                ],
            )
        with col2:
            sub("測試季度人均吞吐量")
            show_tbl(
                ["", "Owner", "Support", "總計"],
                [
                    ("D", ["本季測試季度人均吞吐量",   g("s3_cur_qa_tp_owner"),  g("s3_cur_qa_tp_support"),  g("s3_cur_qa_tp_total")]),
                    ("A", ["上季測試季度人均吞吐量",   g("s3_prev_qa_tp_owner"), g("s3_prev_qa_tp_support"), g("s3_prev_qa_tp_total")]),
                    ("D", ["測試人均吞吐量季度環比增長",g("s3_qoq_qa_tp_owner"),  g("s3_qoq_qa_tp_support"),  g("s3_qoq_qa_tp_total")]),
                ],
            )
    
    with tab2:
        show_tbl(
            ["", "Owner", "Support", "總計"],
            [
                ("D", ["本季 Smoke Test 準時數量",    g("s3_cur_smk_ot_o"),  g("s3_cur_smk_ot_s"),  g("s3_cur_smk_ot_t")]),
                ("A", ["本季 Smoke Test 準時比例",    g("s3_cur_smk_ot_ro"), g("s3_cur_smk_ot_rs"), g("s3_cur_smk_ot_rt")]),
                ("D", ["上季 Smoke Test 準時數量",    g("s3_prev_smk_ot_o"), g("s3_prev_smk_ot_s"), g("s3_prev_smk_ot_t")]),
                ("A", ["上季 Smoke Test 準時比例",    g("s3_prev_smk_ot_ro"),g("s3_prev_smk_ot_rs"),g("s3_prev_smk_ot_rt")]),
                ("D", ["本季 Smoke Test 首次通過數",  g("s3_cur_smk_fp_o"),  g("s3_cur_smk_fp_s"),  g("s3_cur_smk_fp_t")]),
                ("A", ["本季 Smoke Test 首次通過比例",g("s3_cur_smk_fp_ro"), g("s3_cur_smk_fp_rs"), g("s3_cur_smk_fp_rt")]),
                ("D", ["上季 Smoke Test 首次通過數",  g("s3_prev_smk_fp_o"), g("s3_prev_smk_fp_s"), g("s3_prev_smk_fp_t")]),
                ("A", ["上季 Smoke Test 首次通過比例",g("s3_prev_smk_fp_ro"),g("s3_prev_smk_fp_rs"),g("s3_prev_smk_fp_rt")]),
            ],
        )

        # ── 本季 Smoke Test 母體逐項清單（供核對）─────────────────────────────
        if selected_team:
            smk_items = get_s3_smoke_items(selected_team, selected_quarter)
            n_counted = sum(1 for i in smk_items if i["counted"])
            with st.expander(f"🔍 本季 Smoke Test 項目明細（母體 {len(smk_items)} 項，有填＝列入計算 {n_counted} 項）"):
                if not smk_items:
                    st.caption("本季無 Epic Roadmap_Item 上線項目，或該 tab 無 Smoke 欄位")
                else:
                    def _mk(v):  # True→✅、False→❌、空白→—
                        return "✅" if v == "True" else ("❌" if v == "False" else "—")
                    show_tbl(
                        ["#", "項目名稱", "角色", "首次準時", "首次通過", "列入計算"],
                        [("D" if idx % 2 == 0 else "A",
                          [str(idx + 1), it["name"], it["role"],
                           _mk(it["on_time"]), _mk(it["passed"]),
                           "✔" if it["counted"] else "－（空白不計）"])
                         for idx, it in enumerate(smk_items)],
                    )
                    st.caption("「列入計算」＝該項至少一個 Smoke 欄位有填（非空）；空白項不計入比例分母。準時/通過比例＝該組 ✅ 數 ÷ 該組有填數。")

    with tab3:
        show_tbl(
            ["", "Owner", "Support", "總計"],
            [
                ("D", ["本季項目啟動後 6 周交付比率", g("s3_cur_6w_o"),   g("s3_cur_6w_s"),   g("s3_cur_6w_t")]),
                ("A", ["上季項目啟動後 6 周交付比率", g("s3_prev_6w_o"),  g("s3_prev_6w_s"),  g("s3_prev_6w_t")]),
                ("D", ["6 周交付比率對比",            g("s3_diff_6w_o"),  g("s3_diff_6w_s"),  g("s3_diff_6w_t")]),
                ("A", ["本季項目啟動後 12 周交付比率",g("s3_cur_12w_o"),  g("s3_cur_12w_s"),  g("s3_cur_12w_t")]),
                ("D", ["上季項目啟動後 12 周交付比率",g("s3_prev_12w_o"), g("s3_prev_12w_s"), g("s3_prev_12w_t")]),
                ("A", ["12 周交付比率對比",           g("s3_diff_12w_o"), g("s3_diff_12w_s"), g("s3_diff_12w_t")]),
            ],
        )

        # ── 本季實際交付項目清單（W → R 日曆天）─────────────────────────────
        if selected_team:
            dw = get_delivery_weeks(selected_team, selected_quarter)
            if dw.empty:
                st.caption("本季無可計算 PRD 評審→上線天數的 Epic 項目（需 W 欄有值）")
            else:
                total   = len(dw)
                cnt_6w  = int(dw["within_6w"].sum())
                cnt_12w = int(dw["within_12w"].sum())

                # ── 近 6 個月 6/12 週交付率月份趨勢折線圖 ───────────────────
                trend_df = get_delivery_trend_monthly(selected_team, selected_quarter, n_months=6)

                fig_trend = go.Figure()
                if not trend_df.empty:
                    months_x = trend_df["month_label"].tolist()
                    totals = trend_df["total"].tolist()
                    # total=0 的月份（當月無上線 Epic）斷線不顯示資料點
                    _gap = lambda col: [c if t else None for c, t in zip(trend_df[col].tolist(), totals)]
                    y6, y12 = _gap("cnt_6w"), _gap("cnt_12w")
                    yt = [t if t else None for t in totals]
                    fig_trend.add_trace(go.Scatter(
                        x=months_x, y=y6,
                        mode="lines+markers+text", name="6 週內交付數",
                        line=dict(color=CHART_COLORS["green"], width=2.5),
                        marker=dict(size=9, symbol="circle"),
                        text=[f"{v:.0f}" if v is not None else "－" for v in y6],
                        textposition="bottom center", connectgaps=False,
                    ))
                    fig_trend.add_trace(go.Scatter(
                        x=months_x, y=y12,
                        mode="lines+markers+text", name="12 週內交付數",
                        line=dict(color=CHART_COLORS["accent"], width=2.5, dash="dot"),
                        marker=dict(size=9, symbol="diamond"),
                        text=[f"{v:.0f}" if v is not None else "－" for v in y12],
                        textposition="top center", connectgaps=False,
                    ))
                    fig_trend.add_trace(go.Scatter(
                        x=months_x, y=yt,
                        mode="lines+markers", name="當月上線總數",
                        line=dict(color="#9AA5B1", width=1.5, dash="dash"),
                        marker=dict(size=6), connectgaps=False,
                    ))
                fig_trend.update_layout(**CHART_LAYOUT, height=300,
                                        title_text="近 6 個月 6 / 12 週交付數趨勢（Epic Roadmap_Item）")
                fig_trend.update_layout(yaxis=dict(title="項目數", rangemode="tozero",
                                                   dtick=1, tickformat="d", gridcolor="#E8EDF2"))
                st.caption("⚠️ 無上線 Epic Roadmap_Item 的月份不顯示資料點（折線中斷）")
                st.plotly_chart(fig_trend, use_container_width=True)
                # 趨勢長條圖
                fig_dw = go.Figure()
                colors = []
                for _, row in dw.iterrows():
                    d = row["calendar_days"]
                    colors.append(
                        CHART_COLORS["green"]  if d <= 42 else
                        CHART_COLORS["accent"] if d <= 84 else
                        CHART_COLORS["red"]
                    )
                labels = dw["Summary"].str[:30] + "…" if (dw["Summary"].str.len() > 30).any() else dw["Summary"]
                fig_dw.add_trace(go.Bar(
                    x=labels, y=dw["calendar_days"],
                    marker_color=colors,
                    text=dw["calendar_days"].astype(str) + " 天",
                    textposition="outside",
                ))
                fig_dw.add_hline(y=42, line_dash="dash", line_color=CHART_COLORS["green"],
                                  annotation_text="6 週（42 天）", annotation_position="right",
                                  annotation_font_color=CHART_COLORS["green"])
                fig_dw.add_hline(y=84, line_dash="dot",  line_color=CHART_COLORS["accent"],
                                  annotation_text="12 週（84 天）", annotation_position="right",
                                  annotation_font_color=CHART_COLORS["accent"])
                fig_dw.update_layout(
                    **CHART_LAYOUT, height=320,
                    title_text=f"PRD 評審 → 上線日曆天（綠≤6週 / 橘≤12週 / 紅>12週）",
                    yaxis_title="日曆天", showlegend=False,
                )
                st.plotly_chart(fig_dw, use_container_width=True)

                # 分群顯示項目清單
                col6, col12, col_over = st.columns(3)
                with col6:
                    sub(f"✅ 6 週內交付（{cnt_6w} / {total}）")
                    rows6 = dw[dw["within_6w"]][["Summary","calendar_days","PRD/TRD Review Final Date","New Target Delivery Date"]]
                    if rows6.empty:
                        st.caption("無")
                    else:
                        show_tbl(["項目名稱","天數","PRD 評審","上線日"],
                            [("D" if i%2==0 else "A",
                              [r["Summary"][:40], f'{int(r["calendar_days"])} 天',
                               str(r["PRD/TRD Review Final Date"])[:10],
                               str(r["New Target Delivery Date"])[:10]])
                             for i, (_, r) in enumerate(rows6.iterrows())])
                with col12:
                    sub(f"🟡 6～12 週交付（{cnt_12w - cnt_6w} / {total}）")
                    rows12 = dw[dw["within_12w"] & ~dw["within_6w"]][["Summary","calendar_days","PRD/TRD Review Final Date","New Target Delivery Date"]]
                    if rows12.empty:
                        st.caption("無")
                    else:
                        show_tbl(["項目名稱","天數","PRD 評審","上線日"],
                            [("D" if i%2==0 else "A",
                              [r["Summary"][:40], f'{int(r["calendar_days"])} 天',
                               str(r["PRD/TRD Review Final Date"])[:10],
                               str(r["New Target Delivery Date"])[:10]])
                             for i, (_, r) in enumerate(rows12.iterrows())])
                with col_over:
                    sub(f"🔴 12 週以上（{total - cnt_12w} / {total}）")
                    rows_over = dw[~dw["within_12w"]][["Summary","calendar_days","PRD/TRD Review Final Date","New Target Delivery Date"]]
                    if rows_over.empty:
                        st.caption("無")
                    else:
                        show_tbl(["項目名稱","天數","PRD 評審","上線日"],
                            [("D" if i%2==0 else "A",
                              [r["Summary"][:40], f'{int(r["calendar_days"])} 天',
                               str(r["PRD/TRD Review Final Date"])[:10],
                               str(r["New Target Delivery Date"])[:10]])
                             for i, (_, r) in enumerate(rows_over.iterrows())])

    render_assistant(assistant.get("三"))
    defbox(
        "<b>實際完成需求量（live）：</b>本季上線的 Epic + Roadmap_Item（R 落本季，不分重要性），依角色 Owner/Support/Total(=O+S)。<b>完成比例</b>＝完成量 ÷ 需求總數量(2.1，同角色)。<br>"
        "<b>開發/測試季度人均吞吐量（live）：</b>完成量 ÷ 季均人力（開發=BE+FE+iOS、測試=QA；不再 ÷3）；環比=(本季−上季)÷上季。<br>"
        "<b>Smoke Test（live）：</b>母體＝本季上線的 Epic + Roadmap_Item（R 欄落在本季）。<b>準時數量/比例</b>＝ First_smoke_on_time = True 的數 ÷ 該組有填(非空)的數；<b>首次通過數量/比例</b>＝ First_smoke_passed = True 同理。分 Owner / Support / Total(=Owner+Support)；無母體顯示「－」。表格下方「🔍 本季 Smoke Test 項目明細」可展開逐項核對母體、每項的首次準時/通過值、及是否列入計算（空白不計入分母）。<br>"
        "<b>項目啟動後 N 周交付：</b>以 PRD 評審會議後 N 周且於本季上線的項目作統計。<br>"
        "<b>環比：</b>= (本期 − 上期) ÷ 上期 × 100%<br>"
        "<b>📐 6/12 週交付率計算（live）</b><br>"
        "・分母：R 欄落在當期、Issue Type=Epic、Item Type=Roadmap_Item，且同時有 W 欄與 R 欄日期、R−W≥0 的項目數。<br>"
        "・分子（6 週）= 分母中 R−W ≤ 42 天；分子（12 週）= R−W ≤ 84 天。<br>"
        "・交付率 = 分子 ÷ 分母 × 100%（分母為 0 不顯示）；缺 W 欄日期不計入分母。<br>"
        "・近 6 個月趨勢圖顯示「各月**實際交付數**」：6 週內交付數、12 週內交付數、當月上線總數（當月無上線 Epic 則斷線）。<br>"
        "・O/S/T 比率表：同母體，依 Role 拆 Owner/Support/Total(全體)，本季/上季各算 6、12 週比率，「對比」=本季−上季（百分點）。<br>"
        "<b>※ Smoke Test 資料稀疏（只有少數上線項目有 smoke 記錄），數字偏小屬正常。</b>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 四、非專項吞吐量
# ══════════════════════════════════════════════════════════════════════════════
elif section == "四、非專項吞吐量":
    st.caption("以「成本管理」視角，觀測每個團隊的總人數與「非專項」吞吐量是否符合效益，通常為「維運」需求。")
    st.caption("🏢 主要關注部門：研發部門、測試部門")

    # ── 非專項上版需求數：本季 vs 上季 vs 去年同期 ──────────────────────────
    fig4 = bar_chart(
        ["Bug", "Feature & Enhancement", "總計"],
        [{"name": f"{QUARTER_LABEL} 本季", "values": [n("s4_cur_bug"),  n("s4_cur_feat"),  n("s4_cur_total")],  "color": CHART_COLORS["cur"]},
         {"name": "上季",                  "values": [n("s4_prev_bug"), n("s4_prev_feat"), n("s4_prev_total")], "color": CHART_COLORS["prev"]},
         {"name": "去年同期",              "values": [n("s4_yoy_bug"),  n("s4_yoy_feat"),  n("s4_yoy_total")],  "color": CHART_COLORS["accent"]}],
        title="非專項上版需求數（本季 / 上季 / 去年同期）", height=300,
    )
    st.plotly_chart(fig4, use_container_width=True)

    sub("實際上版需求數")
    show_tbl(
        ["", "Bug", "Feature & Tech Enhancement", "總計"],
        [
            ("D", ["本季 實際上版需求數",     g("s4_cur_bug"),      g("s4_cur_feat"),      g("s4_cur_total")]),
            ("A", ["上季 實際上版需求數",     g("s4_prev_bug"),     g("s4_prev_feat"),     g("s4_prev_total")]),
            ("D", ["去年同期 實際上版需求數", g("s4_yoy_bug"),      g("s4_yoy_feat"),      g("s4_yoy_total")]),
            ("R", ["同期比較 YOY",            g("s4_yoy_diff_bug"), g("s4_yoy_diff_feat"), g("s4_yoy_diff_total")]),
        ],
    )
    col1, col2 = st.columns(2)
    with col1:
        sub("開發季度人均吞吐量（非專項）")
        show_tbl(
            ["", "Bug", "Feature &\nTech Enhancement", "總計"],
            [
                ("D", ["本季開發季度人均吞吐量",   g("s4_cur_eng_tp_bug"),  g("s4_cur_eng_tp_feat"),  g("s4_cur_eng_tp_total")]),
                ("A", ["上季開發季度人均吞吐量",   g("s4_prev_eng_tp_bug"), g("s4_prev_eng_tp_feat"), g("s4_prev_eng_tp_total")]),
                ("D", ["開發人均吞吐量季度環比增長",g("s4_qoq_eng_tp_bug"),  g("s4_qoq_eng_tp_feat"),  g("s4_qoq_eng_tp_total")]),
            ],
        )
    with col2:
        sub("測試季度人均吞吐量（非專項）")
        show_tbl(
            ["", "Bug\n預排｜緊急插件", "Feature\n預排｜緊急插件", "總計"],
            [
                ("D", ["本季測試季度人均吞吐量",   g("s4_cur_qa_tp_bug"),  g("s4_cur_qa_tp_feat"),  g("s4_cur_qa_tp_total")]),
                ("A", ["上季測試季度人均吞吐量",   g("s4_prev_qa_tp_bug"), g("s4_prev_qa_tp_feat"), g("s4_prev_qa_tp_total")]),
                ("D", ["測試人均吞吐量季度環比增長",g("s4_qoq_qa_tp_bug"),  g("s4_qoq_qa_tp_feat"),  g("s4_qoq_qa_tp_total")]),
            ],
        )

    render_assistant(assistant.get("四"))
    defbox(
        "<b>非專項：</b>項目複雜程度低，大多毋須經過 PRD 評審、技術評審等環節，基本上一個團隊能自行閉環作業。<br>"
        "<b>預排 vs 緊急插件：</b>前者是每雙週 Refinement 過程排入處理的維運項目；後者為緊急插件，除了需緊急調派人力處理，可能影響預排項目的交付量外，也大多走非常規上版流程。<br>"
        "<b>📐 計算（live）：</b>母體＝本季上線 Small_Ticket；<b>bug=Fix 卡</b>、<b>feature=Story 卡</b>（Task/Survey/Defect 不計）。人均吞吐量＝數量÷季均人力（開發=BE+FE+iOS、測試=QA），環比=(本季−上季)÷上季。<b>去年同期無 2025 資料，顯「－」。</b>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 五、交付週期
# ══════════════════════════════════════════════════════════════════════════════
elif section == "五、交付週期":
    st.caption("藉由「需求交付週期」指標，了解每個專項(Roadmap_Item)、非專項需求從產品準備階段到進入研發階段後的平均處理週期（日曆天）。")
    st.caption("🏢 主要關注部門：產品 / 研發 / 測試")

    tab1, tab2 = st.tabs(["5.1 專項(Roadmap_Item)週期（Roadmap_Item）", "5.2 非專項週期（Small_Ticket）"])

    with tab1:
        # ── Gantt 式堆疊橫條：專項(Roadmap_Item)各階段累積時間軸 ─────────────────────────
        # 每個色塊 = 一個階段，從前一階段結尾接續，讓人看出瓶頸在哪
        gantt_stages = [
            ("PRD/TRD 準備",  "s51_{}_prd_prep_avg", "#1C3557"),
            ("等待評審",      "s51_{}_wait_rev_avg", "#2E75B6"),
            ("評審",          "s51_{}_rev_avg",       "#5B9BD5"),
            ("等待研發測試資源進場",  "s51_{}_res_avg",       "#9DC3E6"),
            ("開發準備",      "s51_{}_devp_avg",      "#70AD47"),
            ("實際開發",      "s51_{}_dev2_avg",      "#4EA321"),
            ("測試準備",      "s51_{}_qap_avg",       "#ED7D31"),
            ("實際測試",      "s51_{}_qa2_avg",       "#C45F10"),
        ]
        rows = [
            (f"{QUARTER_LABEL} 本季", "cur"),
            ("上季",                  "prev"),
        ]
        fig5 = go.Figure()
        bases = {row_label: 0.0 for row_label, _ in rows}
        for stage_name, key_tmpl, color in gantt_stages:
            y_vals, base_vals, text_vals = [], [], []
            for row_label, period in rows:
                v = n(key_tmpl.format(period))
                base_vals.append(bases[row_label])
                y_vals.append(v)
                text_vals.append(f"{v:.1f}天" if v > 0 else "")
                bases[row_label] += v
            fig5.add_trace(go.Bar(
                name=stage_name,
                y=[r for r, _ in rows],
                x=y_vals,
                base=base_vals,
                orientation="h",
                marker_color=color,
                text=text_vals,
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=11),
            ))
        fig5.update_layout(
            **CHART_LAYOUT,
            barmode="overlay",
            height=290,
            title_text="專項(Roadmap_Item)交付流程時間軸（日曆天，平均值）",
            xaxis_title="累積日曆天",
        )
        fig5.update_layout(
            legend=dict(orientation="h", yanchor="top", y=-0.55, xanchor="left", x=0),
            margin=dict(b=120),
            xaxis=dict(title=dict(standoff=6)),
        )
        st.plotly_chart(fig5, use_container_width=True)

        sub("整體交付週期（日曆天）")
        show_tbl(
            ["指標", "本季\n平均", "本季\n中位數", "上季\n平均", "上季\n中位數", "去年同期\n平均", "去年同期\n中位數", "季度\n環比"],
            [
                ("D", ["需求文檔定稿週期（PRD/TRD）", g("s51_cur_prd_avg"), g("s51_cur_prd_med"), g("s51_prev_prd_avg"), g("s51_prev_prd_med"), g("s51_yoy_prd_avg"), g("s51_yoy_prd_med"), g("s51_qoq_prd")]),
                ("A", ["需求 Mockup 定稿週期",         g("s51_cur_mock_avg"),g("s51_cur_mock_med"),g("s51_prev_mock_avg"),g("s51_prev_mock_med"),g("s51_yoy_mock_avg"),g("s51_yoy_mock_med"),g("s51_qoq_mock")]),
                ("D", ["開發完成週期",                 g("s51_cur_dev_avg"), g("s51_cur_dev_med"), g("s51_prev_dev_avg"), g("s51_prev_dev_med"), g("s51_yoy_dev_avg"), g("s51_yoy_dev_med"), g("s51_qoq_dev")]),
                ("A", ["測試完成週期",                 g("s51_cur_qa_avg"),  g("s51_cur_qa_med"),  g("s51_prev_qa_avg"),  g("s51_prev_qa_med"),  g("s51_yoy_qa_avg"),  g("s51_yoy_qa_med"),  g("s51_qoq_qa")]),
                ("D", ["整體交付週期",                 g("s51_cur_total_avg"),g("s51_cur_total_med"),g("s51_prev_total_avg"),g("s51_prev_total_med"),g("s51_yoy_total_avg"),g("s51_yoy_total_med"),g("s51_qoq_total")]),
            ],
        )

        # ── 散點圖補充：各專項各階段實際天數（每點=一個專項；▲最高 ◆平均 ▼最低，不畫箱型樞紐）──
        if designated:
            _sc = get_s51_scatter(selected_team, selected_quarter)
            fig5s = go.Figure()
            for _lbl in ["需求文檔定稿", "Mockup 定稿", "開發完成", "測試完成", "整體交付"]:
                _days = [p["days"] for p in _sc.get(_lbl, [])]
                _nm   = [p["name"] for p in _sc.get(_lbl, [])]
                if not _days:
                    continue
                # 個別專項點（隱藏箱體與上下樞紐，只留點）
                fig5s.add_trace(go.Box(
                    y=_days, name=_lbl, boxpoints="all", jitter=0.5, pointpos=0,
                    fillcolor="rgba(0,0,0,0)", line=dict(color="rgba(0,0,0,0)"),
                    marker=dict(color=CHART_COLORS["cur"], size=8),
                    text=_nm,
                    hovertemplate="%{text}<br>%{y:.0f} 天<extra>" + _lbl + "</extra>",
                ))
                # 最高 / 平均 / 最低 標記
                _mx, _mn, _mean = max(_days), min(_days), sum(_days) / len(_days)
                fig5s.add_trace(go.Scatter(
                    x=[_lbl, _lbl, _lbl], y=[_mx, _mean, _mn], mode="markers",
                    marker=dict(symbol=["triangle-up", "diamond", "triangle-down"],
                                color=["#C45F10", CHART_COLORS["accent"], "#70AD47"], size=13),
                    hovertext=[f"最高 {_mx:.0f} 天", f"平均 {_mean:.1f} 天", f"最低 {_mn:.0f} 天"],
                    hovertemplate="%{hovertext}<extra></extra>", showlegend=False,
                ))
            fig5s.update_layout(**CHART_LAYOUT, height=320, showlegend=False,
                                title_text="各專項交付週期分布（每點=一個專項；▲最高 ◆平均 ▼最低）",
                                yaxis_title="天")
            st.plotly_chart(fig5s, use_container_width=True)
            st.caption("每個點是一個專項（Epic）的實際天數；標記為各階段最高／平均／最低。出現極端值時平均易被 outlier 拉動，建議搭配中位數判讀。")

        col1, col2 = st.columns(2)
        with col1:
            sub("PRD/TRD 準備與評審週期")
            show_tbl(
                ["指標", "本季\n平均", "本季\n中位數", "上季\n平均", "上季\n中位數", "季度\n環比"],
                [
                    ("D", ["PRD/TRD 準備週期（日曆天）",   g("s51_cur_prd_prep_avg"),g("s51_cur_prd_prep_med"),g("s51_prev_prd_prep_avg"),g("s51_prev_prd_prep_med"),g("s51_qoq_prd_prep")]),
                    ("A", ["等待 PRD/TRD 評審週期（工作天）",g("s51_cur_wait_rev_avg"),g("s51_cur_wait_rev_med"),g("s51_prev_wait_rev_avg"),g("s51_prev_wait_rev_med"),g("s51_qoq_wait_rev")]),
                    ("D", ["PRD/TRD 評審週期（日曆天）",   g("s51_cur_rev_avg"),     g("s51_cur_rev_med"),     g("s51_prev_rev_avg"),     g("s51_prev_rev_med"),     g("s51_qoq_rev")]),
                    ("A", ["等待研發測試資源進場（工作天）",   g("s51_cur_res_avg"),     g("s51_cur_res_med"),     g("s51_prev_res_avg"),     g("s51_prev_res_med"),     g("s51_qoq_res")]),
                ],
            )
        with col2:
            sub("開發 / 測試週期")
            show_tbl(
                ["指標", "本季\n平均", "本季\n中位數", "上季\n平均", "上季\n中位數", "季度\n環比"],
                [
                    ("D", ["開發準備平均週期（工作天）",g("s51_cur_devp_avg"),g("s51_cur_devp_med"),g("s51_prev_devp_avg"),g("s51_prev_devp_med"),g("s51_qoq_devp")]),
                    ("A", ["實際開發平均週期（日曆天）",g("s51_cur_dev2_avg"),g("s51_cur_dev2_med"),g("s51_prev_dev2_avg"),g("s51_prev_dev2_med"),g("s51_qoq_dev2")]),
                    ("D", ["測試準備平均週期（工作天）",g("s51_cur_qap_avg"), g("s51_cur_qap_med"), g("s51_prev_qap_avg"), g("s51_prev_qap_med"), g("s51_qoq_qap")]),
                    ("A", ["實際測試平均週期（日曆天）",g("s51_cur_qa2_avg"), g("s51_cur_qa2_med"), g("s51_prev_qa2_avg"), g("s51_prev_qa2_med"), g("s51_qoq_qa2")]),
                ],
            )

        # ── 本季專項項目明細（5.1 母體：Item Type=Roadmap_Item、本季 R）──────────
        if designated:
            s51_items = get_s51_items(selected_team, selected_quarter)
            with st.expander(f"本季專項 (Roadmap_Item) 項目（{len(s51_items)} 項）"):
                if s51_items:
                    show_tbl(["#", "項目名稱", "上線日"],
                             [("D" if i % 2 == 0 else "A", [str(i + 1), it["name"], it["date"]])
                              for i, it in enumerate(s51_items)])
                else:
                    st.caption("本季無專項項目")

    with tab2:
        # ── Gantt 式堆疊橫條：非專項 Small_Ticket各階段累積時間軸 ────────────────────
        sm_gantt_stages = [
            ("等待開發（卡片創建→開始開發）", "s52_{}_wait_dev", "#1C3557"),
            ("開發階段",                      "s52_{}_dev",      "#2E75B6"),
            ("等待測試",                      "s52_{}_wait_qa",  "#ED7D31"),
            ("測試階段",                      "s52_{}_qa",       "#C45F10"),
        ]
        rows52 = [
            (f"{QUARTER_LABEL} 本季", "cur"),
            ("上季",                  "prev"),
        ]
        fig52 = go.Figure()
        bases = {row_label: 0.0 for row_label, _ in rows52}
        for stage_name, key_tmpl, color in sm_gantt_stages:
            y_vals, base_vals, text_vals = [], [], []
            for row_label, period in rows52:
                v = n(key_tmpl.format(period))
                base_vals.append(bases[row_label])
                y_vals.append(v)
                text_vals.append(f"{v:.1f}天" if v > 0 else "")
                bases[row_label] += v
            fig52.add_trace(go.Bar(
                name=stage_name,
                y=[r for r, _ in rows52],
                x=y_vals,
                base=base_vals,
                orientation="h",
                marker_color=color,
                text=text_vals,
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=11),
            ))
        fig52.update_layout(
            **CHART_LAYOUT,
            barmode="overlay",
            height=270,
            title_text="非專項 Small_Ticket交付流程時間軸（日曆天）",
            xaxis_title="累積日曆天",
        )
        fig52.update_layout(
            legend=dict(orientation="h", yanchor="top", y=-0.6, xanchor="left", x=0),
            margin=dict(b=120),
            xaxis=dict(title=dict(standoff=6)),
        )
        st.plotly_chart(fig52, use_container_width=True)
        show_tbl(
            ["", "開卡～開始開發\n（日曆天）", "開發階段週期\n（日曆天）", "等待測試週期\n（工作天）", "開始測試～通過測試\n（日曆天）", "交付平均週期\n（日曆天）"],
            [
                ("D", ["本季",          g("s52_cur_wait_dev"),  g("s52_cur_dev"),  g("s52_cur_wait_qa"),  g("s52_cur_qa"),  g("s52_cur_total")]),
                ("A", ["上季",          g("s52_prev_wait_dev"), g("s52_prev_dev"), g("s52_prev_wait_qa"), g("s52_prev_qa"), g("s52_prev_total")]),
                ("R", ["參考重點指標",  "—",                   f"< {S52_OBS_THRESHOLD:g} 天",  "—",       f"< {S52_OBS_THRESHOLD:g} 天",  "—"]),
                ("D", ["季度環比增長",  g("s52_qoq_wait_dev"),  g("s52_qoq_dev"),  g("s52_qoq_wait_qa"),  g("s52_qoq_qa"),  g("s52_qoq_total")]),
            ],
        )

        # ── 超出觀測值（> 觀測值天）的卡片清單，供點開核對 ──────────────────────
        if designated:
            _out = get_s52_outliers(selected_team, selected_quarter)
            _nd, _nq = len(_out["dev"]), len(_out["qa"])
            with st.expander(f"🔍 超出觀測值（> {S52_OBS_THRESHOLD:g} 天）的項目（開發階段 {_nd}、測試階段 {_nq}）"):
                def _otbl(rows, stage_label):
                    sub(f"{stage_label}（{len(rows)}）")
                    if rows:
                        show_tbl(["#", "卡號", "項目名稱", "天數"],
                                 [("D" if i % 2 == 0 else "A",
                                   [str(i + 1), r["key"], r["name"], f'{r["days"]} 天'])
                                  for i, r in enumerate(rows)])
                    else:
                        st.caption("無")
                _otbl(_out["dev"], "開發階段週期")
                _otbl(_out["qa"], "開始測試～通過測試")

    render_assistant(assistant.get("五"))
    defbox(
        "<b>平均值、中位數：</b>因每個專項(Roadmap_Item)的顆粒度不同，為避免極值產生偏誤，同時提供「平均值」與「中位數」供參考。<br>"
        "<b>中位數的 (n=x)：</b>x 為該指標背後的取樣項目數（起訖兩日期皆有值者）。本季 Roadmap 項目少、具備完整日期者更少，n 偏小時數值波動大，請以 n 判讀可信度。<br>"
        "<b>每個有效交付（起訖兩日期皆有值）至少以 1 天計：同天或訖早於起者一律呈現 1 天，避免「同天 = 0」看似無工作。</b><br>"
        "<b>📏「整體交付週期（日曆天）」各列起訖欄（皆日曆天，起訖兩日期皆有值才納入）：</b><br>"
        "・<b>需求文檔定稿週期（PRD/TRD）：</b>PRD/TRD Preparing Start Date → PRD/TRD Brief Date。<br>"
        "・<b>需求 Mockup 定稿週期：</b>Mockup Preparing Start Date → Mockup Complete Date。<br>"
        "・<b>開發完成週期：</b>PRD/TRD Brief Date → Development End Date。<br>"
        "・<b>測試完成週期：</b>To Be Functional Tested Date → Functional Testing End Date。<br>"
        "・<b>整體交付週期：</b>PRD/TRD Preparing Start Date → New Target Delivery Date（含頭到尾的整段）。<br>"
        "<b>📏「PRD/TRD 準備與評審週期」各列起訖欄（起訖兩日期皆有值才納入）：</b><br>"
        "・<b>PRD/TRD 準備週期（日曆天）：</b>PRD/TRD Preparing Start Date → PRD/TRD Internal Review End Date。<br>"
        "・<b>等待 PRD/TRD 評審週期（工作天）：</b>PRD/TRD Internal Review End Date → PRD/TRD Review Final Date（排除週末）。<br>"
        "・<b>PRD/TRD 評審週期（日曆天）：</b>PRD/TRD Review Start Date（跨隊或作 PRD评审时间）→ PRD/TRD Review Final Date。<br>"
        "・<b>等待研發測試資源進場（工作天）：</b>PRD/TRD Review Final Date → PRD/TRD Brief Date（排除週末）。<br>"
        "<b>📏「開發 / 測試週期」各列起訖欄（起訖兩日期皆有值才納入）：</b><br>"
        "・<b>開發準備平均週期（工作天）：</b>PRD/TRD Brief Date → Development Start Date（排除週末）。<br>"
        "・<b>實際開發平均週期（日曆天）：</b>Development Start Date → To Be Functional Tested Date。<br>"
        "・<b>測試準備平均週期（工作天）：</b>To Be Functional Tested Date → Functional Testing Start Date（排除週末）。<br>"
        "・<b>實際測試平均週期（日曆天）：</b>Functional Testing Start Date → Functional Testing End Date。<br>"
        "<b>非專項 Small_Ticket等待資源週期：</b>以 Jira 卡片創建日期做計算（Jira History 紀錄中的卡片創建日）。<br>"
        "<b>📐 5.1 計算邏輯（live）</b><br>"
        "・母體：<b>專項母卡（Issue Type=Epic ＋ Item Type=Roadmap_Item）</b>、R 欄落在該季；子卡(Story/Fix/Task)是實際工作卡、不算專項，不納入。<br>"
        "・各指標 = 起訖兩日期相減（日曆天=日期差；工作天=排除週末），同天或負值一律以 1 天計（有效交付最少 1 天）；輸出平均、中位數(n)、環比(以平均)。<br>"
        "・整體交付週期表下方「散點圖」列出每個專項各階段實際天數（▲最高 ◆平均 ▼最低），用以判讀平均是否被 outlier 影響。<br>"
        "<b>5.2 非專項週期（live）：</b>母體＝本季上線 Small_Ticket；各階段取兩日期差的平均（日曆天，同天最少 1 天）。起點「等待開發／總計」用卡片創建日(Created)；環比=(本季−上季)÷上季。<br>"
        f"・<b>參考重點指標（觀測值 {S52_OBS_THRESHOLD:g} 天）：</b>套用於「開發階段週期」與「開始測試～通過測試」兩欄（單張卡片該階段 > {S52_OBS_THRESHOLD:g} 天即算超標）。表格下方「🔍 超出觀測值的項目」可展開，列出超標卡號＋名稱＋天數（依天數由大到小），供點開核對是哪些卡拖慢。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 六、人均工作天
# ══════════════════════════════════════════════════════════════════════════════
elif section == "六、人均工作天":
    st.caption("作為監控用途，計算目前研發人力投入在實際開發、測試的工作時間，若未達到預期，須進一步了解影響人均工作天的原因。")
    st.caption("🏢 主要關注部門：開發部門、測試部門　　⚡ 參考重點指標：> 11 天")

    st.markdown("#### 6 本季總人天（依卡片類型）")

    # ── 對比長條圖：Eng vs QA 月均人均工作天（總計）vs 11 天基準 ────────────
    val_eng = n("s62_eng_avg_total")
    val_qa  = n("s62_qa_avg_total")

    fig62 = go.Figure()
    fig62.add_trace(go.Bar(
        x=["Eng 月均人均工作天", "QA 月均人均工作天"],
        y=[val_eng, val_qa],
        marker_color=[CHART_COLORS["cur"], CHART_COLORS["support"]],
        text=[f"{val_eng:.2f} 天", f"{val_qa:.2f} 天"],
        textposition="outside",
        width=0.4,
    ))
    fig62.add_hline(
        y=11, line_dash="dash", line_color=CHART_COLORS["green"],
        annotation_text="參考重點指標 11 天",
        annotation_position="top right",
        annotation_font_color=CHART_COLORS["green"],
    )
    fig62.update_layout(
        **CHART_LAYOUT,
        height=300,
        title_text=f"{QUARTER_LABEL} 各卡片類型月均人均工作天（總計）",
        yaxis_title="人天",
        yaxis_range=[0, max(val_eng, val_qa, 11) * 1.3],
        showlegend=False,
    )
    st.plotly_chart(fig62, use_container_width=True)

    # ── 圓餅圖：各卡片類型人天比例（Eng 左 / QA 右）─────────────────────────
    pie_labels = ["Story", "Fix", "Task", "Survey", "Defect"]
    pie_colors = ["#1C3557", "#2E75B6", "#70AD47", "#ED7D31", "#9DC3E6"]
    eng_pie = [n("s62_eng_story"), n("s62_eng_fix"), n("s62_eng_task"), n("s62_eng_survey"), n("s62_eng_defect")]
    qa_pie  = [n("s62_qa_story"),  n("s62_qa_fix"),  n("s62_qa_task"),  n("s62_qa_survey"),  n("s62_qa_defect")]

    fig62_pie = go.Figure()
    # Eng 圓餅（左）
    fig62_pie.add_trace(go.Pie(
        labels=pie_labels, values=eng_pie,
        name="Eng", domain=dict(x=[0, 0.46]),
        marker_colors=pie_colors, hole=0.4, sort=False,
        title=dict(text=f"Eng<br>{n('s62_eng_total'):.1f} 天", font=dict(size=13)),
        textinfo="percent", textposition="inside",
        hovertemplate="%{label}<br>%{value:.2f} 天<br>%{percent}<extra></extra>",
    ))
    # QA 圓餅（右）
    fig62_pie.add_trace(go.Pie(
        labels=pie_labels, values=qa_pie,
        name="QA", domain=dict(x=[0.54, 1]),
        marker_colors=pie_colors, hole=0.4, sort=False,
        title=dict(text=f"QA<br>{n('s62_qa_total'):.1f} 天", font=dict(size=13)),
        textinfo="percent", textposition="inside",
        hovertemplate="%{label}<br>%{value:.2f} 天<br>%{percent}<extra></extra>",
        showlegend=False,
    ))
    fig62_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=320,
        title_text=f"{QUARTER_LABEL} 各卡片類型人天比例（Eng / QA）",
        font=dict(family="sans-serif", size=12, color="#1C3557"),
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig62_pie, use_container_width=True)

    show_tbl(
        ["指標", "Story", "Fix", "小計\n(Story+Fix)", "Task", "Survey", "Defect", "總計"],
        [
            ("D", ["Eng 總人天（BE+FE+iOS 加總）", g("s62_eng_story"),    g("s62_eng_fix"),    g("s62_eng_sf"),    g("s62_eng_task"),    g("s62_eng_survey"),    g("s62_eng_defect"),    g("s62_eng_total")]),
            ("A", ["Eng 月均人均工作天",           g("s62_eng_avg_story"),g("s62_eng_avg_fix"),g("s62_eng_avg_sf"),g("s62_eng_avg_task"),g("s62_eng_avg_survey"),g("s62_eng_avg_defect"),g("s62_eng_avg_total")]),
            ("D", ["QA 總人天",                    g("s62_qa_story"),     g("s62_qa_fix"),     g("s62_qa_sf"),     g("s62_qa_task"),     g("s62_qa_survey"),     g("s62_qa_defect"),     g("s62_qa_total")]),
            ("A", ["QA 月均人均工作天",            g("s62_qa_avg_story"), g("s62_qa_avg_fix"), g("s62_qa_avg_sf"), g("s62_qa_avg_task"), g("s62_qa_avg_survey"), g("s62_qa_avg_defect"), g("s62_qa_avg_total")]),
        ],
    )

    # ── 輔助表：隔季首月上線預覽（本季被擠到下一季首月的人天）────────────────────
    _nq_y = int(YEAR) if str(YEAR).isdigit() else 0
    _nq_m = (int(QUARTER) if str(QUARTER).isdigit() else 1) * 3 + 1
    if _nq_m > 12:
        _nq_m -= 12; _nq_y += 1
    _nextmon = g("s6next_month") if g("s6next_month") not in ("", "－") else f"{_nq_y}年{_nq_m}月"
    _nextcnt = g("s6next_count")
    sub(f"🔎 隔季首月（{_nextmon}）上線預覽 — 輔助參考")
    st.caption(
        f"抓 **{_nextmon}** 預計上線（New Target Delivery Date 落在該月）的卡片人天。"
        f"此數字若偏大，代表許多項目因封版／活動（如 618）等因素排到隔月上線，"
        f"本季人均偏低並非團隊未投入。共 {_nextcnt} 張卡片。"
    )
    show_tbl(
        ["指標", "Story", "Fix", "小計\n(Story+Fix)", "Task", "Survey", "Defect", "總計"],
        [
            ("D", [f"Eng 人天（{_nextmon}）", g("s6next_eng_story"), g("s6next_eng_fix"), g("s6next_eng_sf"), g("s6next_eng_task"), g("s6next_eng_survey"), g("s6next_eng_defect"), g("s6next_eng_total")]),
            ("A", [f"QA 人天（{_nextmon}）",  g("s6next_qa_story"),  g("s6next_qa_fix"),  g("s6next_qa_sf"),  g("s6next_qa_task"),  g("s6next_qa_survey"),  g("s6next_qa_defect"),  g("s6next_qa_total")]),
        ],
    )

    render_assistant(assistant.get("六"))
    defbox(
        "<b>本季總人天（依卡片類型）：</b>以 New Target Delivery Date 認定本季上線的所有卡片（不限 Item Type，含 Roadmap_Item 與 Small_Ticket），"
        "依 Issue Type 拆為 Story / Fix / Task / Survey，名稱含 Defect 者歸入 Defect（互斥分桶，不重複計）。"
        "Issue Type = Epic（專項(Roadmap_Item)母卡）不屬上述類別，不計入總計。<br>"
        "<b>Eng 人天</b> = 前端 + 後端 + iOS 工作量；<b>QA 人天</b> = 測試工作量。<br>"
        "<b>月均人均工作天</b> = 總人天 ÷ 月均人力 ÷ 3（Eng 人力 = BE+FE+iOS，QA 人力 = QA，取自在職人力彙總）。<br>"
        "<b>🔎 隔季首月上線預覽（輔助）：</b>抓「下一季第一個月」（Q1→4月、Q2→7月、Q3→10月、Q4→次年1月）New Target Delivery Date 落點的卡片人天，"
        "分桶同上（Story/Fix/Task/Survey/Defect）。用途：當本季人均偏低時，若此數字偏大，代表項目因封版／活動（如 618）被擠到隔月上線，非團隊未投入。<br>"
        "<b>參考重點指標數據：</b>以 11 天作為參考基準值，表示團隊人均工作天表現正常。若無則需要請 PMO 說明可能的原因情況。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 七、在職人力
# ══════════════════════════════════════════════════════════════════════════════
elif section == "七、在職人力":
    st.caption("🏢 主要關注部門：HRBP / 管理層")
    st.caption("Director 層級以下皆計入，並會根據管理職同事給出的精力配比做計算。")

    # ── 折線圖：各月人力走勢 ────────────────────────────────────────────────
    months = S7_MONTHS_SHORT
    roles  = [("PM", "s7_{}_pm", "#ED7D31"), ("BE", "s7_{}_be", "#2E75B6"),
              ("FE", "s7_{}_fe", "#70AD47"), ("QA", "s7_{}_qa", "#9DC3E6")]
    fig7 = go.Figure()
    for role_name, key_tmpl, color in roles:
        # 缺月（來源未填）→ None，讓折線斷點，不要畫成 0
        vals = [num(g(key_tmpl.format(m)), None) if str(g(key_tmpl.format(m))).strip() not in ("", "－")
                else None for m in ("m1", "m2", "m3")]
        fig7.add_trace(go.Scatter(
            x=months, y=vals, mode="lines+markers+text",
            name=role_name, line=dict(color=color, width=2),
            marker=dict(size=8),
            text=[f"{v:.2f}" if v is not None else "" for v in vals], textposition="top center",
        ))
    fig7.update_layout(**CHART_LAYOUT, height=300, title_text="在職人力月份走勢（人數）")
    st.plotly_chart(fig7, use_container_width=True)

    show_tbl(
        ["月份", "產品經理\nPM", "後端\nBE", "前端\nFE", "iOS App", "測試\nQA", "產品 : 開發 : 測試\n人數比"],
        [
            ("D", [S7_MONTHS_LONG[0], g("s7_m1_pm"), g("s7_m1_be"), g("s7_m1_fe"), g("s7_m1_ios"), g("s7_m1_qa"), g("s7_m1_ratio")]),
            ("A", [S7_MONTHS_LONG[1], g("s7_m2_pm"), g("s7_m2_be"), g("s7_m2_fe"), g("s7_m2_ios"), g("s7_m2_qa"), g("s7_m2_ratio")]),
            ("D", [S7_MONTHS_LONG[2], g("s7_m3_pm"), g("s7_m3_be"), g("s7_m3_fe"), g("s7_m3_ios"), g("s7_m3_qa"), g("s7_m3_ratio")]),
            ("R", [f"{QUARTER_LABEL} 季均",g("s7_q_pm"),  g("s7_q_be"),  g("s7_q_fe"),  g("s7_q_ios"),  g("s7_q_qa"),  g("s7_q_ratio")]),
        ],
    )
    render_assistant(assistant.get("七"))
    defbox(
        "<b>計算說明：</b>除了 Director 層級，其餘管理職人力皆會被認列為團隊的人力成本，並會根據管理職同事給出的精力配比做計算。<br>"
        "<b>新加入、離職的同事</b>會按照實際服務比例做計算。<br>"
        "<b>本季有投入團隊的主導 / 協作項目 PRD 的產品經理</b>皆會列入計算。<br>"
        "<b>📐 計算邏輯（live）</b><br>"
        "・來源在職人力彙總 tab，以 A 欄月份×B 欄團隊取值：C=BE、D=FE、E=iOS、F=QA、G=PM。<br>"
        "・月份依所選季度動態對應（Q1→1/2/3 月、Q2→4/5/6 月…）。<br>"
        "・比例 = PM:(BE+FE+iOS):QA（以 PM=1）；季均 = 該季有資料月份的平均（來源未填的月份留空、不計入）。<br>"
        "・此處季均人力即全報告「人均」指標的共用分母（Eng 人力=BE+FE+iOS、QA 人力=QA）。"
    )



# ══════════════════════════════════════════════════════════════════════════════
# 八、資料品質總覽
# ══════════════════════════════════════════════════════════════════════════════
elif section == "八、資料品質總覽":
    st.caption("以本季上線項目（R 欄在本季區間）為範圍，檢視 H～AH 共 27 個必要欄位的填寫完整度。")
    st.caption(f"🏢 團隊：{selected_team or '請選擇團隊'}　　📅 季度：{QUARTER_LABEL}")

    if not selected_team:
        st.warning("請先在側邊欄選擇團隊")
    else:
        dq = get_data_quality(selected_team, selected_quarter)
        import pandas as pd

        def _render_dq_table(df: "pd.DataFrame", label: str):
            if df.empty:
                st.caption(f"{label}：本季無上線項目")
                return

            # Issue Type 篩選器
            all_types = sorted(df["Issue Type"].astype(str).unique()) if "Issue Type" in df.columns else []
            selected_types = st.multiselect(
                f"{label} — Issue Type 篩選",
                options=all_types,
                default=all_types,
                key=f"dq_filter_{label}",
            )
            filtered_df = df[df["Issue Type"].astype(str).isin(selected_types)] if selected_types else df

            if filtered_df.empty:
                st.caption("無符合條件的項目")
                return

            # 標題列：項目數 + 平均資料品質
            quality_vals = filtered_df["資料品質%"].str.replace("%", "").astype(float)
            avg_q = quality_vals.mean()
            color = "red" if avg_q < 50 else "#1C3557"
            st.markdown(
                f'<div class="sub-title">{label}｜{len(filtered_df)} 項目　平均資料品質：'
                f'<span style="color:{color};font-weight:700">{avg_q:.1f}%</span></div>',
                unsafe_allow_html=True,
            )

            # 用 Styler 標紅空白欄位
            def _style_row(row):
                styles = []
                for col in row.index:
                    val = str(row[col]).strip()
                    is_empty = val in ("", "nan", "NaN", "None")
                    is_quality = col == "資料品質%"
                    if is_quality:
                        try:
                            pct = float(val.replace("%", ""))
                            styles.append("color:red;font-weight:700" if pct < 50 else "color:#1C3557;font-weight:700")
                        except ValueError:
                            styles.append("")
                    elif is_empty:
                        styles.append("color:red;background-color:#FFF0F0")
                    else:
                        styles.append("")
                return styles

            styled = filtered_df.style.apply(_style_row, axis=1)
            st.dataframe(styled, use_container_width=True, height=400)

        tab_rm, tab_sm = st.tabs(["📋 Roadmap Item", "🎫 Small_Ticket"])
        with tab_rm:
            _render_dq_table(dq["roadmap"], "Roadmap Item")
        with tab_sm:
            _render_dq_table(dq["small"], "Small_Ticket")

    defbox(
        "<b>資料品質%：</b>該項目已填欄位數 ÷ 26 必填欄位 × 100%。<br>"
        "<b>📐 計算邏輯（live）</b><br>"
        "・母體：R 欄落在本季的上線項目，分 Roadmap_Item / Small_Ticket 兩頁呈現。<br>"
        "・檢查 I～AH 共 26 個必填欄位的完整度（H「PRD of Main request or Supported request」已停用、不列入）；空白欄位於表中標紅。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 九、參考資料
# ══════════════════════════════════════════════════════════════════════════════
elif section == "九、參考資料":
    refs = [
        ("📊 人效看板（Raw Data）", g("s9_link_dashboard")),
        (f"📁 {QUARTER_LABEL} Raw Data",  g("s9_link_raw_data")),
        ("🔗 Roadmap / Jira",       g("s9_link_jira")),
        ("📎 其他補充資料",         g("s9_link_other")),
    ]
    for title, link in refs:
        st.markdown(
            f'<div class="ref-card">'
            f'<div class="ref-title">{title}</div>'
            f'<div class="ref-link">{link}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.caption(f"📌 附註：以上數據來源若有疑問，請洽 PMO / 數據負責人。　資料截止日期：{g('DATA_CUTOFF_DATE')}")
