"""
Tools for the Business Intelligence Agent.
These tools fetch data from Monday.com, clean it, and perform calculations.
Since the datasets are small (~350 deals, ~170 work orders), we load them into
DataFrames to perform complex filtering, aggregation, and cross-board analysis.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from agent.monday_client import MondayClient
from agent.data_cleaner import (
    clean_deals_df,
    clean_work_orders_df,
    format_inr,
    get_data_quality_report,
)


class BIBackend:
    """Helper backend to fetch and cache cleaned datasets from Monday.com."""

    def __init__(self, deals_board_id: str, work_orders_board_id: str, client: MondayClient):
        self.deals_board_id = deals_board_id
        self.work_orders_board_id = work_orders_board_id
        self.client = client
        self._deals_cache: pd.DataFrame | None = None
        self._work_orders_cache: pd.DataFrame | None = None
        self._deals_quality: dict = {}
        self._work_orders_quality: dict = {}

    def refresh_data(self):
        """Fetch fresh data from Monday.com and clean it."""
        try:
            raw_deals = self.client.get_board_as_dataframe(self.deals_board_id)
            self._deals_cache, self._deals_quality = clean_deals_df(raw_deals)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch/clean Deals board: {e}")

        try:
            raw_wo = self.client.get_board_as_dataframe(self.work_orders_board_id)
            self._work_orders_cache, self._work_orders_quality = clean_work_orders_df(raw_wo)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch/clean Work Orders board: {e}")

    def get_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get the cached DataFrames or refresh if empty."""
        if self._deals_cache is None or self._work_orders_cache is None:
            self.refresh_data()
        return self._deals_cache, self._work_orders_cache

    def get_quality_report(self) -> str:
        """Generate a data quality issues report."""
        return get_data_quality_report(self._deals_quality, self._work_orders_quality)


# Define the tools we want to make available to the agent.
def query_pipeline_summary(backend: BIBackend) -> str:
    """Summarize the sales pipeline (total value, stage counts, and sector distribution)."""
    try:
        deals_df, _ = backend.get_data()
        if deals_df.empty:
            return "No deal data found on the board."

        total_val = deals_df["Masked Deal value"].sum()
        status_counts = deals_df["Deal Status"].value_counts().to_dict()
        stage_counts = deals_df["Deal Stage"].value_counts().to_dict()

        # Sector breakdown
        sector_summary = (
            deals_df.groupby("Sector/service")["Masked Deal value"]
            .agg(["sum", "count"])
            .sort_values(by="sum", ascending=False)
        )
        sector_lines = []
        for sector, row in sector_summary.iterrows():
            sector_lines.append(
                f"- **{sector}**: {format_inr(row['sum'])} ({int(row['count'])} deals)"
            )

        report = f"""
### Sales Pipeline Summary
- **Total Pipeline Value**: {format_inr(total_val)}
- **Total Deals**: {len(deals_df)}

#### Deals by Status:
{chr(10).join(f"- {status}: {count}" for status, count in status_counts.items())}

#### Top Sectors by Value:
{chr(10).join(sector_lines)}
"""
        return report.strip()
    except Exception as e:
        return f"Error executing query_pipeline_summary: {str(e)}"


def query_work_order_summary(backend: BIBackend) -> str:
    """Summarize the work order tracker (execution status, overdue, and billing stats)."""
    try:
        _, wo_df = backend.get_data()
        if wo_df.empty:
            return "No work order data found on the board."

        exec_status = wo_df["Execution Status"].value_counts().to_dict()

        # Overdue work orders
        overdue_df = wo_df[wo_df.get("Is Overdue", False)]
        overdue_count = len(overdue_df)

        # Financial totals
        amount_col = "Amount in Rupees (Excl of GST) (Masked)"
        billed_col = "Billed Value in Rupees (Excl of GST.) (Masked)"
        collected_col = "Collected Amount in Rupees (Incl of GST.) (Masked)"
        ar_col = "Amount Receivable (Masked)"

        total_amount = wo_df[amount_col].sum() if amount_col in wo_df.columns else 0
        total_billed = wo_df[billed_col].sum() if billed_col in wo_df.columns else 0
        total_collected = wo_df[collected_col].sum() if collected_col in wo_df.columns else 0
        total_ar = wo_df[ar_col].sum() if ar_col in wo_df.columns else 0

        report = f"""
### Work Order Execution & Financial Summary
- **Total Work Orders**: {len(wo_df)}
- **Overdue Work Orders**: {overdue_count} at risk

#### Execution Status Breakdown:
{chr(10).join(f"- {status}: {count}" for status, count in exec_status.items())}

#### Financial Status:
- **Total Value of Work Orders**: {format_inr(total_amount)}
- **Total Billed to Date**: {format_inr(total_billed)} ({((total_billed/total_amount)*100 if total_amount else 0):.1f}% of total)
- **Total Collected**: {format_inr(total_collected)}
- **Accounts Receivable (AR)**: {format_inr(total_ar)}
"""
        return report.strip()
    except Exception as e:
        return f"Error executing query_work_order_summary: {str(e)}"


def query_by_sector(backend: BIBackend, sector_name: str) -> str:
    """Filter both deals and work orders by a specific sector (e.g. 'Mining', 'Powerline')."""
    try:
        deals_df, wo_df = backend.get_data()
        sector_clean = sector_name.strip().title()

        # Deals
        s_deals = deals_df[deals_df["Sector/service"].str.title() == sector_clean] if "Sector/service" in deals_df.columns else pd.DataFrame()
        # Work Orders
        s_wo = wo_df[wo_df["Sector"].str.title() == sector_clean] if "Sector" in wo_df.columns else pd.DataFrame()

        deal_val = s_deals["Masked Deal value"].sum() if not s_deals.empty else 0
        wo_val = s_wo["Amount in Rupees (Excl of GST) (Masked)"].sum() if not s_wo.empty else 0

        report = f"""
### Sector Report: {sector_clean}

#### Pipeline (Deals)
- **Deals Count**: {len(s_deals)}
- **Total Pipeline Value**: {format_inr(deal_val)}
- **Deals by Stage**:
{s_deals["Deal Stage"].value_counts().to_string() if not s_deals.empty else "No deals"}

#### Execution (Work Orders)
- **Work Orders Count**: {len(s_wo)}
- **Total Work Order Value**: {format_inr(wo_val)}
- **Execution Status Breakdown**:
{s_wo["Execution Status"].value_counts().to_string() if not s_wo.empty else "No work orders"}
"""
        return report.strip()
    except Exception as e:
        return f"Error executing query_by_sector: {str(e)}"


def get_data_quality_report_tool(backend: BIBackend) -> str:
    """Get the active list of data quality issues across both boards."""
    report = backend.get_quality_report()
    return f"### Data Quality Audit Report\n\n{report}"


def generate_leadership_report(backend: BIBackend) -> str:
    """Generate a high-level summary suitable for leadership/founder updates."""
    try:
        deals_df, wo_df = backend.get_data()

        # Pipeline stats
        pipeline_val = deals_df["Masked Deal value"].sum()
        won_deals = deals_df[deals_df["Deal Status"] == "Won"]
        won_val = won_deals["Masked Deal value"].sum()

        # Work order execution stats
        wo_total = wo_df["Amount in Rupees (Excl of GST) (Masked)"].sum()
        wo_billed = wo_df["Billed Value in Rupees (Excl of GST.) (Masked)"].sum()
        wo_collected = wo_df["Collected Amount in Rupees (Incl of GST.) (Masked)"].sum()
        wo_ar = wo_df["Amount Receivable (Masked)"].sum()

        overdue_wo = wo_df[wo_df.get("Is Overdue", False)]

        # Top 3 sectors by Deal Value
        top_sectors = (
            deals_df.groupby("Sector/service")["Masked Deal value"]
            .sum()
            .sort_values(ascending=False)
            .head(3)
        )
        sector_lines = [f"1. **{s}**: {format_inr(val)}" for s, val in top_sectors.items()]

        report = f"""
# Leadership Update — Business Intelligence

## 1. Sales & Pipeline Health
- **Total Open Pipeline**: {format_inr(pipeline_val)} across {len(deals_df)} deals.
- **Deals Won**: {len(won_deals)} deals totaling {format_inr(won_val)}.
- **Top 3 Industries by Pipeline**:
  {chr(10).join(f"  {line}" for line in sector_lines)}

## 2. Operations & Execution
- **Work Orders Under Management**: {len(wo_df)} projects.
- **Overdue / At-Risk Projects**: {len(overdue_wo)} projects require immediate attention.
- **Execution Health**:
  - Completed: {len(wo_df[wo_df["Execution Status"] == "Completed"])}
  - Ongoing / Executed: {len(wo_df[wo_df["Execution Status"].isin(["Ongoing", "Executed until current month"])])}
  - Stalled / Paused: {len(wo_df[wo_df["Execution Status"] == "Pause / struck"])}

## 3. Financial Performance & Cash Collection
- **Total Portfolio Value**: {format_inr(wo_total)}
- **Invoiced/Billed Value**: {format_inr(wo_billed)} ({((wo_billed / wo_total) * 100 if wo_total else 0):.1f}% Billed)
- **Collected Value**: {format_inr(wo_collected)} ({((wo_collected / wo_billed) * 100 if wo_billed else 0):.1f}% Collection Rate against Billed)
- **Outstanding Accounts Receivable (AR)**: {format_inr(wo_ar)}

---
*Note: This report is generated dynamically from monday.com boards. Data quality audits are computed automatically to flag missing records.*
"""
        return report.strip()
    except Exception as e:
        return f"Error generating leadership report: {str(e)}"
