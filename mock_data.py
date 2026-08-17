"""
mock_data.py — 合成假資料產生器（DEMO / 作品集版）

不連任何外部服務，全部在記憶體產生。數值以 (team, quarter) 為種子 → 每次重整結果穩定。
產出的 DataFrame 欄位刻意對齊原架構的 Raw Data / 人力 / 發版 / Roadmap 結構，
因此上層所有 compute_* / get_* 函式無須改動即可運作。
"""
from __future__ import annotations
import random
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
    return random.Random(abs(hash("|".join(map(str, parts)))) % (2**32))


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
        "Mockup Preparing Start Date": "", "Mockup Complete Date": "",
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
    for q in AVAILABLE_QUARTERS:
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
    for q in AVAILABLE_QUARTERS:
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
    feats = rng.sample(_FEATURES, k=min(len(_FEATURES), rng.randint(14, 20)))
    total = len(feats)
    est = rng.randint(max(4, total - 8), total - 2)
    act = rng.randint(max(3, est - 4), est)
    addon = rng.randint(0, 3)

    def pack(cnt):
        items = feats[:cnt]
        o = cnt // 2
        return {"count": cnt, "items": items, "owner": o, "support": cnt - o}

    return {"total_req": pack(total), "act_done": pack(act),
            "est_done": pack(est), "addon": pack(addon)}
