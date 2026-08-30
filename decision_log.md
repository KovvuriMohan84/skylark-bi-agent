# Decision Log: Monday.com Business Intelligence Agent

## 1. Key Assumptions Made
- **Board Schema consistency**: We assumed that Monday.com boards would be imported directly from the provided excel sheets. As a result, we query columns using the titles present in the original sheets (e.g., `Masked Deal value`, `Close Date (A)`, `Amount in Rupees (Excl of GST) (Masked)`).
- **Data Completeness**: Excel files contain missing/blank dates and amounts. We assumed that filling numeric missing values with `NaN` (unbilled/unassigned) and dates with `NaT` is cleaner than trying to impute them, which would skew metrics like "average deal value" or "collection rates". We explicitly tell the LLM to highlight these missing values as "data quality issues".
- **Currency formatting**: India-centric workspace. We assumed Rupees formatted as Lakhs/Crores are much more readable for leadership updates than long scientific notation or plain integers.

## 2. Technical Trade-Offs Chosen
- **GraphQL Pagination vs. Dynamic In-Memory Queries**: 
  - *Trade-off*: Exposing complex filters (like SQL where clauses) via GraphQL is extremely hard to build, slow, and prone to schema-mismatch errors. 
  - *Decision*: Since the datasets are small (~350 Deals, ~170 Work Orders), we fetch all columns and items in one paginated call when the session initializes. We cache this data into a Pandas DataFrame. The agent tools query this DataFrame using Pandas.
  - *Why*: This ensures 100% accurate data aggregations, support for complex groupings (like sector breakdowns or quarter math), and execution speed in under 1 second.
- **Gemini Native Function Calling over LangChain/ReAct**:
  - *Trade-off*: LangChain has high library overhead and slow parsing.
  - *Decision*: We used the official `google-genai` SDK's native function calling (`gemini-3.6-flash`).
  - *Why*: It's exceptionally fast, native to the model, handles multiple tool-call requests in parallel, and eliminates parsing errors.
- **Streamlit Community Cloud vs. Custom Web App**:
  - *Trade-off*: Building a custom React/Node.js app would take much longer to set up and deploy.
  - *Decision*: Streamlit frontend.
  - *Why*: Speed of development, free hosting, and automatic responsive rendering for screens.

## 3. Interpretation of "Leadership Updates"
We interpreted "preparing data for leadership updates" as a tool that generates a highly-structured executive summary report:
1. **Sales & Pipeline**: Total open funnel, top sectors, and won value.
2. **Operations & Risk**: Overdue work orders, stalled execution status.
3. **Cashflow**: Total portfolio value, percentage billed, collection rate, and outstanding Accounts Receivable (AR).

This saves leaders from opening spreadsheet details and gives them the high-level health of the company in one click.

## 4. What We'd Do Differently With More Time
- **Vector DB for Semantic Search**: If boards contained thousands of free-text comments or chat logs, we would use a vector database (like Chroma/Pinecone) to search those first.
- **Auto-Sync Webhooks**: Implement monday.com webhooks so the cached data refreshes automatically whenever a board cell is updated, rather than requiring manual clicks.
- **Write Actions**: Support adding notes or updating statuses back to Monday.com directly from the chat conversation.
