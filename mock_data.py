"""
mock_data.py — 合成假資料產生器（DEMO 展示版）

不連任何外部服務，全部在記憶體產生。數值以 (team, quarter) 為種子 → 每次重整、每次重啟結果都相同。
產出的 DataFrame 欄位刻意對齊原架構的 Raw Data / 人力 / 發版 / Roadmap 結構，
因此上層所有 compute_* / get_* 函式無須改動即可運作。
"""
from __future__ import annotations
import random
import zlib
from datetime import date, timedelta
import pandas as pd

from field_map import TEAM_NAMES, AVAILABLE_QUARTERS


# ── 季度工具（本地複製，避免與 data.py 循環匯入）──────────────────────────────
def _q_dates(q: str) -> tuple[date, date]:
    y, n = int(q[:4]), int(q[5])
    ms = (n - 1) * 3 + 1
    de = {1: 31, 2: 30, 3: 30, 4: 31}[n]
    return date(y, ms, 1), date(y, n * 3, de)


def _seed(*parts) -> random.Random:
    # 用 crc32 而非內建 hash()：內建字串 hash 每次啟動都會變，數字會跟著重啟跳動。
    return random.Random(zlib.crc32("|".join(map(str, parts)).encode("utf-8")))


def _prev_q(q: str) -> str:
    y, n = int(q[:4]), int(q[5])
    return f"{y - 1}Q4" if n == 1 else f"{y}Q{n - 1}"


def _data_quarters() -> list[str]:
    """要產資料的季度＝可選季度 + 最早一季的上季（供「上季」對比用，不出現在選單）。"""
    qs = list(AVAILABLE_QUARTERS)
    first_prev = _prev_q(qs[0])
    return [first_prev] + qs if first_prev not in qs else qs


_FEATURES = [
    "Checkout flow revamp", "Search relevance v2", "Notification service",
    "Data pipeline migration", "Mobile onboarding", "API rate limiting",
    "Dashboard redesign", "Payment retry logic", "Inventory sync",
    "Fraud detection model", "Report exporter", "SSO integration",
    "Cache layer upgrade", "Webhook delivery", "Audit log tooling",
    "Feature flag platform", "Image CDN rollout", "Email template engine",
    "Localization phase 2", "Recommendation engine", "Bulk import tool",
    "Realtime metrics", "Access control refactor", "Subscription billing",
]

_RAW_COLS = [
    "Key", "Summary", "Issue Type", "Item Type", "Role", "Status", "Sprint",
    "Created", "PRD Size",
    "PRD/TRD Preparing Start Date", "PRD/TRD Internal Review End Date",
    "PRD/TRD Review Start Date", "PRD/TRD Review Final Date", "PRD/TRD Brief Date",
    "Implementation Date", "Mockup Preparing Start Date", "Mockup Complete Date",
    "Development Start Date", "Development End Date", "To Be Functional Tested Date",
    "Functional Testing Start Date", "Functional Testing End Date",
    "First Target Delivery Date", "New Target Delivery Date", "Target Beta Start Date",
    "Frontend Workload(day)", "Backend Workload(Day)", "IOS Workload(Day)",
    "Functional Testing Workload(Day)", "First_smoke_on_time", "First_smoke_passed",
]


def _d(dt: date | None) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def _maybe(rng, val, p_blank):
    """以機率 p_blank 讓欄位留空（模擬漏填，讓資料品質/週期 n 有變化）。"""
    return "" if rng.random() < p_blank else val


def raw_df(team: str, quarter: str) -> pd.DataFrame:
    rng = _seed(team, quarter, "raw")
    qs, qe = _q_dates(quarter)
    span = (qe - qs).days
    rows = []
    tkey = "".join(w[0] for w in team.split())[:3].upper() or "EPX"
    kn = rng.randint(1000, 9000)

    def key():
        nonlocal kn
        kn += rng.randint(1, 9)
        return f"{tkey}-{kn}"

    # ── 專項 Epic（Roadmap_Item 母卡）──────────────────────────────────────────
    n_epic = rng.randint(10, 16)
    for _ in range(n_epic):
        # 準備排在本季偏前、上線排在本季偏後 → 中間里程碑用比例插值，確保多落在本季
        prep = qs + timedelta(days=rng.randint(0, max(1, int(span * 0.30))))
        r = qs + timedelta(days=rng.randint(int(span * 0.45), span))
        pr = max(1, (r - prep).days)

        def M(frac, jitter=2):
            return _d(prep + timedelta(days=int(pr * frac) + rng.randint(-jitter, jitter)))

        rows.append({
            "Key": key(), "Summary": rng.choice(_FEATURES),
            "Issue Type": "Epic", "Item Type": "Roadmap_Item",
            "Role": rng.choices(["Owner", "Support", ""], [0.5, 0.4, 0.1])[0],
            "Status": rng.choices(["Released", "Done", "Developing", "Blocked", "Wont Develop"],
                                  [0.55, 0.15, 0.15, 0.1, 0.05])[0],
            "Sprint": f"{team} {quarter[:4]} Sprint {quarter[4:]}-{rng.randint(1, 6)}",
            "Created": _d(prep - timedelta(days=rng.randint(20, 90))),
            "PRD Size": rng.choice(["S", "M", "L", "XL"]),
            "PRD/TRD Preparing Start Date": _d(prep),
            "PRD/TRD Internal Review End Date": _maybe(rng, M(0.18), .2),
            "PRD/TRD Review Start Date": _maybe(rng, M(0.12), .2),
            "PRD/TRD Review Final Date": _maybe(rng, M(0.28), .25),
            "PRD/TRD Brief Date": _maybe(rng, M(0.33), .25),
            "Implementation Date": _maybe(rng, M(0.38), .2),
            "Mockup Preparing Start Date": _maybe(rng, M(0.06), .45),
            "Mockup Complete Date": _maybe(rng, M(0.24), .45),
            "Development Start Date": _maybe(rng, M(0.45), .15),
            "Development End Date": _maybe(rng, M(0.78), .2),
            "To Be Functional Tested Date": _maybe(rng, M(0.80), .25),
            "Functional Testing Start Date": _maybe(rng, M(0.86), .25),
            "Functional Testing End Date": _maybe(rng, M(0.96), .2),
            # 準時：多數如期或提早（First Target >= New Target），少數延後
            "First Target Delivery Date": _d(r + timedelta(days=rng.choices([0, 3, 10, -5], [0.5, 0.2, 0.15, 0.15])[0])),
            "New Target Delivery Date": _d(r),
            "Target Beta Start Date": _maybe(rng, M(0.92), .5),
            "Frontend Workload(day)": _maybe(rng, rng.randint(1, 8), .15),
            "Backend Workload(Day)": _maybe(rng, rng.randint(1, 10), .15),
            "IOS Workload(Day)": _maybe(rng, rng.randint(0, 5), .3),
            "Functional Testing Workload(Day)": _maybe(rng, rng.randint(1, 6), .3),
            "First_smoke_on_time": rng.choices(["True", "False", ""], [0.25, 0.1, 0.65])[0],
            "First_smoke_passed": rng.choices(["True", "False", ""], [0.25, 0.1, 0.65])[0],
        })

    # ── 專項子卡（Roadmap_Item：Story/Fix/Task）──────────────────────────────
    for _ in range(rng.randint(20, 40)):
        r = qs + timedelta(days=rng.randint(3, span))
        it = rng.choices(["Story", "Fix", "Task", "Survey"], [0.5, 0.3, 0.15, 0.05])[0]
        rows.append(_child_row(rng, key(), it, "Roadmap_Item", team, quarter, r))

    # ── 非專項 Small_Ticket（Story/Fix/Task/Survey/Defect）────────────────────
    for _ in range(rng.randint(35, 60)):
        r = qs + timedelta(days=rng.randint(3, span))
        it = rng.choices(["Story", "Fix", "Task", "Survey", "Defect"], [0.4, 0.35, 0.12, 0.05, 0.08])[0]
        rows.append(_child_row(rng, key(), it, "Small_Ticket", team, quarter, r))

    return pd.DataFrame(rows, columns=_RAW_COLS)


def _child_row(rng, k, issue_type, item_type, team, quarter, r):
    created = r - timedelta(days=rng.randint(10, 60))
    dev_s = r - timedelta(days=rng.randint(6, 20))
    dev_e = dev_s + timedelta(days=rng.randint(1, 10))
    t_s = dev_e + timedelta(days=rng.randint(0, 4))
    t_e = t_s + timedelta(days=rng.randint(1, 8))
    # 部分非專項 Story 帶設計稿（2.3「小卡稿」才有資料）；多數在開發開始前交付，少數之後
    mk_s = mk_c = ""
    if item_type == "Small_Ticket" and issue_type == "Story" and rng.random() < 0.4:
        mc = dev_s - timedelta(days=rng.choices([rng.randint(1, 6), -rng.randint(1, 3)], [0.8, 0.2])[0])
        mk_s, mk_c = _d(mc - timedelta(days=rng.randint(2, 7))), _d(mc)
    return {
        "Key": k, "Summary": rng.choice(_FEATURES),
        "Issue Type": issue_type, "Item Type": item_type,
        "Role": rng.choices(["Owner", "Support", ""], [0.45, 0.45, 0.1])[0],
        "Status": rng.choices(["Released", "Done", "Developing"], [0.6, 0.2, 0.2])[0],
        "Sprint": f"{team} {quarter[:4]} Sprint {quarter[4:]}-{rng.randint(1, 6)}",
        "Created": _d(created), "PRD Size": "",
        "PRD/TRD Preparing Start Date": "", "PRD/TRD Internal Review End Date": "",
        "PRD/TRD Review Start Date": "", "PRD/TRD Review Final Date": "",
        "PRD/TRD Brief Date": "", "Implementation Date": "",
        "Mockup Preparing Start Date": mk_s, "Mockup Complete Date": mk_c,
        "Development Start Date": _maybe(rng, _d(dev_s), .1),
        "Development End Date": _maybe(rng, _d(dev_e), .15),
        "To Be Functional Tested Date": _maybe(rng, _d(dev_e), .2),
        "Functional Testing Start Date": _maybe(rng, _d(t_s), .2),
        "Functional Testing End Date": _maybe(rng, _d(t_e), .2),
        "First Target Delivery Date": _d(r), "New Target Delivery Date": _d(r),
        "Target Beta Start Date": "",
        "Frontend Workload(day)": _maybe(rng, rng.randint(1, 4), .3),
        "Backend Workload(Day)": _maybe(rng, rng.randint(1, 5), .3),
        "IOS Workload(Day)": _maybe(rng, rng.randint(0, 2), .5),
        "Functional Testing Workload(Day)": _maybe(rng, rng.randint(1, 3), .4),
        "First_smoke_on_time": "", "First_smoke_passed": "",
    }


# ── 索引（Live/DEMO 把關）：所有 (季度, 團隊) 皆視為已就緒 ─────────────────────
def index_set() -> dict:
    return {(q, t): None for q in AVAILABLE_QUARTERS for t in TEAM_NAMES}


# ── 在職人力 ──────────────────────────────────────────────────────────────────
def headcount_df() -> pd.DataFrame:
    rows = []
    for q in _data_quarters():
        y, n = int(q[:4]), int(q[5])
        for mo in range((n - 1) * 3 + 1, n * 3 + 1):
            label = f"{y}年{mo}月"
            for t in TEAM_NAMES:
                rng = _seed(t, q, mo, "hc")
                rows.append([label, t, rng.randint(2, 6), rng.randint(1, 5),
                             rng.randint(0, 3), rng.randint(1, 4), rng.randint(1, 2)])
    return pd.DataFrame(rows, columns=["Time", "Team", "BE", "FE", "iOS", "QA", "PM"])


# ── 季度發版情形 ──────────────────────────────────────────────────────────────
def release_df() -> pd.DataFrame:
    rows = []
    for q in _data_quarters():
        tstr = f"{q[:4]}年{q[4:]}"
        for t in TEAM_NAMES:
            rng = _seed(t, q, "rel")
            vals = [rng.randint(4, 8), rng.randint(3, 9), rng.randint(0, 4),
                    rng.randint(0, 3), rng.randint(0, 3), rng.randint(0, 2), rng.randint(0, 3)]
            rows.append([tstr, t, "PMO", *vals])
    cols = ["Time", "Team", "PMO", "v1", "v2", "v3", "v4", "v5", "v6", "v7"]
    return pd.DataFrame(rows, columns=cols)


# ── Roadmap 四類數字 + 項目清單（直接回傳 get_roadmap_items 的結果結構）────────
def roadmap_items(team: str, quarter: str) -> dict:
    rng = _seed(team, quarter, "rm")
    # 以 Raw Data「本季上線專項數」為基準往外推，讓 2.1 的 Roadmap 數字與 Raw 實際完成量相近
    # （兩個來源略有出入是常態，但不應差太多）。
    raw = raw_df(team, quarter)
    n_epic = int(((raw["Issue Type"] == "Epic") & (raw["Item Type"] == "Roadmap_Item")).sum())
    act = max(1, n_epic + rng.choice([-1, 0, 0, 1]))
    est = act + rng.randint(0, 4)
    total = min(len(_FEATURES), est + rng.randint(3, 6))
    feats = rng.sample(_FEATURES, k=total)
    addon = rng.randint(0, 3)

    def pack(cnt):
        items = feats[:cnt]
        o = cnt // 2
        return {"count": cnt, "items": items, "owner": o, "support": cnt - o}

    return {"total_req": pack(total), "act_done": pack(act),
            "est_done": pack(est), "addon": pack(addon)}


# ══════════════════════════════════════════════════════════════════════════════
# 每季啟動專項回顧：合成的 PMO 週報（Roadmap 總表）
# ══════════════════════════════════════════════════════════════════════════════
# 產出與原架構相同形狀的「A4:BV」原始列（第 0 列為表頭），讓 data.get_quarterly_review()
# 的規則式判斷無須改動即可運作。欄位索引需與 data.py 的 _COL_* / _WEEKLY_* 一致。
_W_NCOLS = 74
_W_NAME, _W_KEY, _W_PRIORITY, _W_GOAL = 2, 9, 5, 19
_W_STATUS, _W_RISK_INIT, _W_RISK_Q, _W_RISK_FINAL, _W_NEWDATE = 26, 27, 28, 29, 31
_W_OWNER0, _W_WK0, _W_WKN = 33, 61, 13


def _week_starts(quarter: str) -> list[date]:
    """本季 13 個週報週（每週一）。"""
    qs, _ = _q_dates(quarter)
    first = qs + timedelta(days=(7 - qs.weekday()) % 7)
    return [first + timedelta(days=7 * i) for i in range(_W_WKN)]


def _md(d: date) -> str:
    return f"{d.month}/{d.day}"


def _weekly_done(rng, weeks, quarter: str, overestimated: bool) -> tuple[dict, list[str]]:
    """已上線專項：PRD → 開發 → 測試 → 上線，上線後不再填週報。"""
    rel = rng.randint(8, 12)                       # 上線週（0-based）
    rel_day = min(weeks[rel] + timedelta(days=rng.randint(1, 3)), _q_dates(quarter)[1])
    dev_end = rel - rng.randint(2, 3)
    wk = [""] * _W_WKN
    for i in range(rel + 1):
        if i == rel:
            wk[i] = (f"已上線（{_md(rel_day)}），範圍調整後如期交付，上線後監控正常。" if overestimated
                     else f"已上線（{_md(rel_day)}），上線後監控正常，無重大缺陷回報。")
        elif i <= 1:
            wk[i] = ("PRD 評審中；跨團隊依賴項尚未確認，季初評估達標風險偏高。" if overestimated
                     else "PRD 評審完成，進入技術方案設計。")
        elif overestimated and i == 3:
            wk[i] = "經評審後縮減首期範圍（進階設定改列第二階段），跨團隊依賴項已解除。"
        elif i < dev_end:
            if rng.random() < 0.75:
                wk[i] = f"開發中，進度約 {min(95, int(100 * i / dev_end))}%，無阻塞。"
        elif i == dev_end:
            wk[i] = "開發完成，進入功能測試。"
        else:
            wk[i] = f"功能測試中，已修復 {rng.randint(2, 9)} 項缺陷，預計 {_md(rel_day)} 上線。"
    meta = {"goal": "5 上線", "status": "Released",
            "risk_init": "Dangerous" if overestimated else rng.choice(["Safe", "Safe", "At-Risk"]),
            "risk_q": "Safe", "risk_final": "Safe", "new_date": _d(rel_day)}
    return meta, wk


def _weekly_open(rng, weeks, qe: date, scenario: int) -> tuple[dict, list[str]]:
    """未上線專項的幾種典型情境（依序指派，讓回顧的三種分類都有範例）。"""
    wk = [""] * _W_WKN
    eta = qe + timedelta(days=rng.randint(10, 24))          # 落到下季初
    if scenario == 0:      # 落後但受控：有原因、有新 ETA、有共識
        wk[0] = "PRD 評審完成，進入技術方案設計。"
        for i in (2, 3, 4, 5):
            wk[i] = f"開發中，進度約 {15 * (i - 1)}%，無阻塞。"
        wk[6] = "第三方介面規格變更，需重做串接，開發延遲約 2 週。"
        wk[8] = f"已與 PM 及相關團隊確認調整後時程，新 ETA {_md(eta)}。"
        wk[10] = "開發完成，進入功能測試。"
        wk[11] = f"功能測試中，剩餘 3 項缺陷修復中；遇季末封版，已確認改於 {_md(eta)} 上線。"
        wk[12] = f"測試進度約 80%，維持 {_md(eta)} 上線；延遲風險已同步相關團隊。"
        meta = {"priority": "Highest", "goal": "5 上線", "status": "Functional Testing",
                "risk_init": "Safe", "risk_q": "Dangerous", "risk_final": "At-Risk", "new_date": _d(eta)}
    elif scenario == 1:    # 待釐清：風險欄未更新、週報停更
        wk[0] = "PRD 評審完成，進入技術方案設計。"
        wk[2] = "開發啟動。"
        wk[3] = "開發中，進度約 25%。"
        wk[4] = "開發中，進度約 40%。"
        meta = {"priority": "Highest", "goal": "5 上線", "status": "Developing",
                "risk_init": "At-Risk", "risk_q": "Please Update", "risk_final": "Please Update",
                "new_date": ""}
    elif scenario == 2:    # 本季無目標：排入下季啟動（不評落後）
        wk[1] = "需求訪談中，預計下月完成需求確認。"
        wk[5] = "資源優先支援其他專項，本季僅完成需求確認，排入下季啟動。"
        meta = {"priority": "High", "goal": "0 無(下季啟動)", "status": "To Do",
                "risk_init": "", "risk_q": "", "risk_final": "Safe", "new_date": ""}
    elif scenario == 3:    # 待釐清：P0 未啟動且週報沒有說明、季初預判落差大
        for i in range(2, _W_WKN):
            wk[i] = "-"
        meta = {"priority": "Highest", "goal": "5 上線", "status": "To Do",
                "risk_init": "Safe", "risk_q": "No Way", "risk_final": "Dangerous", "new_date": ""}
    else:                  # 進行中：本季目標為開發完成，尚在開發
        wk[1] = "PRD 評審完成，進入技術方案設計。"
        for i in range(3, _W_WKN):
            if i < _W_WKN - 1 and rng.random() < 0.7:
                wk[i] = f"開發中，進度約 {min(80, 9 * (i - 2))}%，無阻塞。"
        wk[12] = f"開發中，進度約 85%，預計 {_md(eta)} 完成開發並送測。"
        meta = {"priority": rng.choice(["High", "Medium"]), "goal": "3 開發完成", "status": "Developing",
                "risk_init": "At-Risk", "risk_q": "At-Risk", "risk_final": "Safe", "new_date": _d(eta)}
    return meta, wk


def weekly_rows(quarter: str) -> list[list[str]]:
    """合成的週報原始列（表頭 + 各隊 Owner 專項）。專項名稱與 2.1 的 Roadmap 項目一致：
    Owner 專項數 = 2.1 需求總數的 Owner 數；其中已上線數 = 2.1 實際完成的 Owner 數。"""
    weeks = _week_starts(quarter)
    _, qe = _q_dates(quarter)
    header = [""] * _W_NCOLS
    header[_W_NAME], header[_W_KEY], header[_W_PRIORITY] = "項目名稱", "解決方案卡 Key", "Priority"
    header[_W_GOAL], header[_W_STATUS] = "本季期望目標", "項目當前狀態"
    header[_W_RISK_INIT], header[_W_RISK_Q] = "季初預估達標風險", "本季目標達標風險"
    header[_W_RISK_FINAL], header[_W_NEWDATE] = "最終目標達標風險", "最新預期交付日"
    for ti, t in enumerate(TEAM_NAMES):
        header[_W_OWNER0 + ti] = t
    for i, w in enumerate(weeks):
        header[_W_WK0 + i] = f"Weekly Highlights\nW{i + 1}（{_md(w)}）"

    rows = [header]
    for ti, team in enumerate(TEAM_NAMES):
        rm = roadmap_items(team, quarter)
        feats = rm["total_req"]["items"]
        n_owner, n_done = rm["total_req"]["owner"], rm["act_done"]["owner"]
        act = rm["act_done"]["count"]
        done_names = feats[:n_done]
        open_names = feats[act:act + (n_owner - n_done)]
        rng = _seed(team, quarter, "weekly")
        tkey = "".join(w[0] for w in team.split())[:3].upper() or "EPX"
        kn = rng.randint(100, 400)

        def add(name, meta, wk):
            nonlocal kn
            kn += rng.randint(1, 9)
            row = [""] * _W_NCOLS
            row[_W_NAME], row[_W_KEY] = name, f"{tkey}PR-{kn}"
            row[_W_PRIORITY], row[_W_GOAL], row[_W_STATUS] = meta["priority"], meta["goal"], meta["status"]
            row[_W_RISK_INIT], row[_W_RISK_Q] = meta["risk_init"], meta["risk_q"]
            row[_W_RISK_FINAL], row[_W_NEWDATE] = meta["risk_final"], meta["new_date"]
            row[_W_OWNER0 + ti] = "Owner"
            row[_W_WK0:_W_WK0 + _W_WKN] = wk
            rows.append(row)

        n_p0 = max(1, (len(done_names) + 2) // 3)          # 已上線專項中約 1/3 為 P0
        for i, name in enumerate(done_names):
            meta, wk = _weekly_done(rng, weeks, quarter, overestimated=(i == 1))
            meta["priority"] = "Highest" if i < n_p0 or i == 1 else ("High" if i % 2 == 0 else "Medium")
            add(name, meta, wk)
        for i, name in enumerate(open_names):
            meta, wk = _weekly_open(rng, weeks, qe, i)
            add(name, meta, wk)
    return rows


def review_narrative(team: str, quarter: str, review: dict, metrics: dict) -> dict:
    """『團隊本季綜合回顧分析』的合成敘事：依回顧結果與報告指標套用句型，
    因此文字中的數字、專項名稱一律與畫面上的數據一致。"""
    out = {"highlights": [], "improvements": [], "clarify": []}
    if not review.get("available"):
        return out
    hi, im, cl = out["highlights"], out["improvements"], out["clarify"]
    A, c = review["catA"], review["counts"]

    def names(lst, k=3):
        s = "、".join(f"「{it['name']}」" for it in lst[:k])
        return s + ("等" if len(lst) > k else "")

    def fnum(key):
        try:
            return float(str(metrics.get(key, "")).replace("%", "").replace(",", "").strip())
        except ValueError:
            return None

    focus = review["focus"]
    judged = len(A["肯定"]) + len(A["受控追蹤"]) + len(A["待釐清"])
    if A["肯定"]:
        hi.append(f"本季評估的 {focus} 專項 {judged} 項中，已交付 {len(A['肯定'])} 項，"
                  f"含{names(A['肯定'])}，交付時程與週報資訊一致。")
    for it in review["catB"]:
        if it["gap"] < 0 and it["flag"].startswith("可接受"):
            hi.append(f"「{it['name']}」季初評估風險為 {it['risk_init']}，經範圍調整後如期上線，"
                      "週報已說明調整原因，預判落差屬可接受範圍。")
    rate = fnum("s24_cur_target_total")
    if rate is not None:
        line = (f"Roadmap 需求 {metrics.get('s21_cur_total_req')} 項、實際完成 "
                f"{metrics.get('s24_cur_done_total')} 項，預估目標達成比例 {metrics.get('s24_cur_target_total')}")
        if rate >= 80:
            hi.append(line + "，達成度良好。")
        else:
            im.append(line + "，低於 80%，建議檢視季初排程與資源配置是否過於樂觀。")
    cur, prev = fnum("s51_cur_total_avg"), fnum("s51_prev_total_avg")
    if cur and prev:
        if cur < prev:
            hi.append(f"專項整體交付週期由上季 {prev:g} 天縮短為 {cur:g} 天。")
        elif cur > prev:
            im.append(f"專項整體交付週期由上季 {prev:g} 天增加為 {cur:g} 天，建議檢視各階段等待時間。")

    for it in A["受控追蹤"]:
        tail = f"新預期交付日 {it['new_date']}，" if it["new_date"] else ""
        im.append(f"「{it['name']}」未於本季上線（狀態 {it['status']}），週報已說明原因並取得共識，"
                  f"{tail}本季風險 {it['risk_q']}，建議持續追蹤交付。")
    if c["total"] and c["done"] / c["total"] < 0.5:
        im.append(f"本隊 Owner 專項 {c['total']} 項中上線 {c['done']} 項"
                  f"（約 {round(100 * c['done'] / c['total'])}%），建議盤點未上線項目的優先順序。")

    for it in A["待釐清"]:
        if it["risk_q"] in ("Please Update", "計算錯誤", ""):
            cl.append(f"「{it['name']}」本季風險欄為「{it['risk_q'] or '空白'}」，最新週報停留在 "
                      f"{it['latest_week'] or '—'}，建議更新風險與進度，避免資訊落差。")
        else:
            cl.append(f"「{it['name']}」目標為本季上線，目前狀態 {it['status']}、本季風險 {it['risk_q']}"
                      f"（季初 {it['risk_init'] or '—'}），週報未填寫說明，建議釐清原因與後續安排。")
    return out
