# Skylark Drones — Monday.com BI Agent

A conversational Business Intelligence Agent that integrates with Monday.com to answer founder-level queries about the sales pipeline (Deals) and operational progress (Work Orders).

---

## 🏛️ Architecture Overview

```
User (Browser)
     │
     ▼
Streamlit UI  ←──────── Session Chat History
     │
     ▼
Gemini Chat SDK (gemini-3.6-flash)
     │
     ├── Tool: get_sales_pipeline_summary()       → Deals DataFrame
     ├── Tool: get_work_order_and_financial()      → Work Orders DataFrame
     ├── Tool: get_sector_performance_report(sec)  → Sector Filtered Data
     ├── Tool: get_data_quality_issues()           → Data Quality Audit
     └── Tool: get_leadership_update_report()      → Executive Report Generator
```

- **Frontend**: Streamlit Chat Interface.
- **AI Agent**: Built using native Gemini Function Calling with the new `google-genai` SDK.
- **Integration**: Monday.com API v2 (GraphQL endpoints) for dynamic board fetching.
- **Analytics Engine**: Pandas DataFrames for robust caching, date normalization, and financial math.

---

## ⚙️ Monday.com Configuration

### 1. Board Import
1. Go to Monday.com.
2. Add new board -> **Import data** -> **Excel**.
3. Upload `Deal funnel Data.xlsx` and name it **Deal Tracker**.
4. Upload `Work_Order_Tracker Data.xlsx` (select the `work order tracker` sheet) and name it **Work Order Tracker**.

### 2. Generate Developer Token
1. Click your profile picture (bottom-left) -> **Developers**.
2. Click **Developer Center** -> **API token** on the left menu.
3. Copy your personal API Token.

---

## 🚀 Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration (.env)
Create a `.env` file in the root folder (or copy `.env.example`):
```env
MONDAY_API_TOKEN=your_token_here
GEMINI_API_KEY=your_gemini_key_here
DEALS_BOARD_ID=5030971872
WORK_ORDERS_BOARD_ID=5030971902
```

### 3. Run Streamlit App
```bash
streamlit run app.py
```

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push this folder to a public **GitHub** repository.
2. Sign in to [share.streamlit.io](https://share.streamlit.io).
3. Click **New app** -> Select your Repository, Branch, and `app.py` as the main entrypoint.
4. Click **Advanced settings** -> Add the environment variables from your `.env` in the **Secrets** section.
5. Click **Deploy**. Your app will be live with a public shareable URL!
