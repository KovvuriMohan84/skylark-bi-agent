"""
Data cleaning and normalisation for the two Monday.com boards.

Handles:
- Inconsistent / missing date strings  → pd.Timestamp / NaT
- Missing numeric values               → NaN + quality report
- Sector / status casing               → Title-cased strings
- Derived columns (Quarter, Is Overdue)
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime
from typing import Tuple


# ------------------------------------------------------------------ #
#  Date helpers                                                        #
# ------------------------------------------------------------------ #

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
    "%d-%m-%Y", "%Y/%m/%d",
    "%d %b %Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y",
]


def _parse_date(raw) -> pd.Timestamp:
    """Try every known format; return NaT on failure."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return pd.NaT
    s = str(raw).strip()
    if not s:
        return pd.NaT
    for fmt in _DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(s, fmt))
        except ValueError:
            pass
    try:
        return pd.Timestamp(s)
    except Exception:
        return pd.NaT


# ------------------------------------------------------------------ #
#  Currency helper                                                     #
# ------------------------------------------------------------------ #

def format_inr(value) -> str:
    """Format a numeric value as Indian Rupees (Lakhs / Crores)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if pd.isna(v):
        return "N/A"
    if v >= 1e7:
        return f"₹{v / 1e7:.2f} Cr"
    if v >= 1e5:
        return f"₹{v / 1e5:.2f} L"
    return f"₹{v:,.0f}"


# ------------------------------------------------------------------ #
#  Deals board                                                         #
# ------------------------------------------------------------------ #

def clean_deals_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Normalise the deals DataFrame and return (clean_df, quality_issues)."""
    if df.empty:
        return df, {}

    issues: dict = {}

    # --- dates ---
    for col in ["Close Date (A)", "Tentative Close Date", "Created Date"]:
        if col in df.columns:
            pre_null = df[col].isna().sum()
            df[col] = df[col].apply(_parse_date)
            new_null = df[col].isna().sum()
            gap = new_null - pre_null
            if gap > 0:
                issues[col] = f"{gap} date(s) could not be parsed"

    # --- numeric ---
    if "Masked Deal value" in df.columns:
        n = df["Masked Deal value"].isna().sum()
        if n:
            issues["Masked Deal value"] = f"{n} records missing deal value"

    # --- string normalisation ---
    for col in ["Sector/service", "Deal Status", "Deal Stage",
                "Closure Probability", "Product deal", "Owner code"]:
        if col in df.columns:
            df[col] = df[col].str.strip()

    if "Sector/service" in df.columns:
        df["Sector/service"] = df["Sector/service"].str.title()

    # --- derived ---
    if "Tentative Close Date" in df.columns:
        df["Quarter"] = (
            df["Tentative Close Date"]
            .dt.to_period("Q")
            .astype(str)
        )

    return df, issues


# ------------------------------------------------------------------ #
#  Work-Orders board                                                   #
# ------------------------------------------------------------------ #

def clean_work_orders_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Normalise the work-orders DataFrame and return (clean_df, quality_issues)."""
    if df.empty:
        return df, {}

    issues: dict = {}

    # Rename the 'name' column to something unambiguous
    if "Deal Name" in df.columns:
        df = df.rename(columns={"Deal Name": "Work Order Name"})

    # --- dates ---
    for col in [
        "Data Delivery Date", "Date of PO/LOI",
        "Probable Start Date", "Probable End Date", "Last invoice date",
    ]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_date)

    # --- financial quality report (don't modify values) ---
    financial_cols = [
        "Amount in Rupees (Excl of GST) (Masked)",
        "Billed Value in Rupees (Excl of GST.) (Masked)",
        "Collected Amount in Rupees (Incl of GST.) (Masked)",
        "Amount Receivable (Masked)",
        "Amount to be billed in Rs. (Exl. of GST) (Masked)",
    ]
    for col in financial_cols:
        if col in df.columns:
            n = df[col].isna().sum()
            if n:
                short = col.split("(")[0].strip()
                issues[short] = f"{n} missing values"

    # --- string normalisation ---
    if "Sector" in df.columns:
        df["Sector"] = df["Sector"].str.strip().str.title()
    if "Execution Status" in df.columns:
        df["Execution Status"] = df["Execution Status"].str.strip()
    if "Billing Status" in df.columns:
        df["Billing Status"] = df["Billing Status"].str.strip()

    # --- derived: is_overdue ---
    if "Probable End Date" in df.columns and "Execution Status" in df.columns:
        today = pd.Timestamp.now()
        df["Is Overdue"] = (
            df["Probable End Date"].notna()
            & (df["Probable End Date"] < today)
            & (~df["Execution Status"].isin(["Completed"]))
        )

    return df, issues


# ------------------------------------------------------------------ #
#  Quality report                                                      #
# ------------------------------------------------------------------ #

def get_data_quality_report(deals_issues: dict, wo_issues: dict) -> str:
    lines: list[str] = []

    if deals_issues:
        lines.append("**Deals Board:**")
        for field, msg in deals_issues.items():
            lines.append(f"  - {field}: {msg}")

    if wo_issues:
        lines.append("**Work Orders Board:**")
        for field, msg in wo_issues.items():
            lines.append(f"  - {field}: {msg}")

    if not lines:
        return "no significant issues"

    return "\n".join(lines)
