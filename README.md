# Team Efficiency Report — Dashboard (Demo)

> 一個以 **Streamlit + Plotly** 打造的「團隊人效季度報告」互動式儀表板。
> 本 repo 為**展示版(demo)**:所有資料皆為**合成假資料**、不連任何外部服務、團隊與專案名皆為虛構。
> 展示範圍:**1 個團隊 × 2 個季度**(2026 Q2、Q3);需以 **Google 帳號登入**(不限網域)才能查看。

**🔗 Live demo:** _(部署後填入 Streamlit Community Cloud 連結)_

---

## 這個專案在做什麼

把原本散落在試算表、需要人工彙整的季度團隊效能數據,自動化成一份**多團隊、多季度、九章節**的互動報告(展示版只放 1 隊 2 季):

| 章節 | 內容 |
|---|---|
| 一、發版情形 | 常規/Hotfix/Fastlane/回滾/延遲上版次數 |
| 二、專項交付結果 | 需求總量、實際/預估完成、交付準確率、PM PRD、UED、研測、顆粒度 |
| 三、上版吞吐量 | 完成量、人均吞吐量、6/12 週交付率、Smoke Test |
| 四、非專項吞吐量 | Small_Ticket bug/feature 產出與人均 |
| 五、交付週期 | PRD→上線各階段週期(平均/中位數/環比) |
| 六、人均工作天 | 各卡片類型人天、月均人均 |
| 七、在職人力 | 各職能人數與比例 |
| 八、資料品質 | 每張卡必填欄位完整度 |
| 九、參考資料 | 連結彙整 |

## 技術亮點

- **資料工程**:單一資料抓取層 → 15+ 個指標計算函式,同一份資料驅動全部章節。
- **效能設計**:快照(snapshot)機制 —— 預先算好序列化,開啟由「即時計算」降為「秒開」。
- **資料品質治理**:每張卡必填欄位健檢、跨源交叉驗證(主幹 vs 對照)。
- **可讀性**:每章內建「💡 數據指標定義」,把公式攤在報告裡,降低前線理解門檻。
- **自動洞察**:規則式「報告小助手」自動標出亮點/待改善(無 AI 成本)。
- **視覺化**:Plotly 多型態圖表 + 深淺色主題。

## 技術棧
`Python` · `Streamlit` · `Plotly` · `pandas` / `numpy`

## 本機執行
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 再填入 Google OAuth 設定
streamlit run app.py
```

沒有 `.streamlit/secrets.toml` 的 `[auth]` 設定時,畫面會停在「登入尚未設定」(刻意設計:不會退回成免登入)。

## Google 登入設定(不限網域)

1. Google Cloud Console → Google Auth Platform → **Audience**:User type 選 **External**,Publishing status 設為 **In production**。
   (Internal 只允許自己組織的帳號;Testing 狀態只有列入 Test users 的帳號能登入。)
2. **Clients** → 建一組 OAuth 2.0 Client(Web application),在「已授權的重新導向 URI」加入:
   - `http://localhost:8501/oauth2callback`(本機)
   - `https://<展示站網址>/oauth2callback`(部署後)
3. 把 `client_id`、`client_secret`、`redirect_uri`、`cookie_secret` 填進 `.streamlit/secrets.toml`(本機)與 Streamlit Cloud 的 Secrets(線上)。範本見 `.streamlit/secrets.toml.example`。
4. 只要 `openid`、`email`、`profile` 這三個基本範圍,不需要 Google 審核。

要限制誰能看:在 `auth.py` 填 `ALLOWED_EMAILS` 或 `ALLOWED_DOMAINS`;兩者留空 = 任何 Google 帳號都能登入。

## 調整展示範圍

- 團隊與季度:`field_map.py` 的 `TEAM_NAMES`、`AVAILABLE_QUARTERS`、`DEFAULT_QUARTER`。加名稱或季度即可,假資料會自動產生。
- 假資料以「團隊 + 季度」為種子,每次重整、重啟數字都相同;要換一批數字就改 `mock_data.py` 的產生規則。

## 檔案結構
```
app.py         # Streamlit 版面與各章節呈現
auth.py        # Google 登入閘門(不限網域,可選白名單)
data.py        # 資料抓取層 + 指標計算(compute_*/get_*)
field_map.py   # 設定(團隊、季度、DEMO 開關)
mock_data.py   # 合成假資料產生器(展示用)
.streamlit/secrets.toml.example   # 登入設定範本(真正的 secrets.toml 不進 repo)
```

---

> ⚠️ 此為去識別化的展示版本。原生產版本連接內部資料源並包含資料品質治理與自動化流程,不在此公開。
