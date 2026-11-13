"""
field_map.py — DEMO 展示版設定檔

⚠️ 這是「去識別化 + 假資料」的公開展示版：
   - 不連任何 Google Sheet、不需憑證。
   - 所有團隊名、ID 皆為虛構。
   - MOCK=True 時，資料由 mock_data.py 合成產生。
"""

# ── DEMO 開關 ────────────────────────────────────────────────────────────────
MOCK = True   # True = 使用合成假資料（離線，公開展示用）

# ── 團隊（虛構）────────────────────────────────────────────────────────────────
# 展示版只放 1 個團隊；要多放幾隊，往這個清單加名稱即可（假資料會自動產生）。
TEAM_NAMES: list[str] = [
    "Team Aurora",
]

# ── 可選季度 ──────────────────────────────────────────────────────────────────
# 展示版放 2 季；每季的「上季」對比資料由 mock_data 自動補齊。
AVAILABLE_QUARTERS: list[str] = ["2026Q2", "2026Q3"]
DEFAULT_QUARTER = "2026Q3"

# ── 以下為原架構所需的設定名稱；DEMO 版皆為空/虛值（MOCK 模式不會用到）──────────
SHEET_ID = "DEMO"
CREDENTIALS_FILE = "credentials.json"     # DEMO 不存在此檔、也不會讀取
FIELD_MAP: dict = {}
TEAM_GID_MAP: dict[str, int] = {}
METRIC_DEFS: list = []
ROADMAP_GID_MAP: dict[str, int] = {}
INDEX_GID = 0
ROADMAP_FILE_MAP: dict[str, str] = {}
ROADMAP_INDEX_GID = None
RAW_TAB_NAME_PATTERNS: tuple = ()
RELEASE_GID = 0
FROZEN_QUARTERS: dict[str, str] = {}      # DEMO 不做封版
