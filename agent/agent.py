"""
Core Agent module.
Creates the Gemini client, configures the tools, and manages the chat session.
"""

from __future__ import annotations

import os
from google import genai
from google.genai import types
from agent.monday_client import MondayClient
from agent.tools import (
    BIBackend,
    query_pipeline_summary,
    query_work_order_summary,
    query_by_sector,
    get_data_quality_report_tool,
    generate_leadership_report,
)


class BIAgent:
    def __init__(
        self,
        monday_token: str,
        deals_board_id: str,
        work_orders_board_id: str,
        gemini_key: str,
    ):
        # 1. Initialize Monday Client and Backend
        self.monday_client = MondayClient(monday_token)
        self.backend = BIBackend(
            deals_board_id=deals_board_id,
            work_orders_board_id=work_orders_board_id,
            client=self.monday_client,
        )

        # 2. Initialize Gemini Client
        self.client = genai.Client(api_key=gemini_key)

        # 3. Read System Instructions
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "system_prompt.txt",
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_instruction = f.read()

        # 4. Pre-build the tools list using closures to capture self.backend
        self._build_tools()

    def _build_tools(self):
        """Construct the tool wrapper functions that Gemini will invoke."""

        def get_sales_pipeline_summary() -> str:
            """Retrieve a high-level summary of the sales pipeline, including total value, deal status, and sector breakdown."""
            return query_pipeline_summary(self.backend)

        def get_work_order_and_financial_summary() -> str:
            """Retrieve operational status and financial metrics like total billed, collected, and accounts receivable (AR)."""
            return query_work_order_summary(self.backend)

        def get_sector_performance_report(sector_name: str) -> str:
            """Get a detailed pipeline and execution summary for a specific business sector.

            Args:
                sector_name: The name of the sector to filter by (e.g., 'Mining', 'Powerline',
                  'Renewables').
            """
            return query_by_sector(self.backend, sector_name)

        def get_data_quality_issues() -> str:
            """Retrieve an audit of missing, inconsistent, or null data fields across the boards."""
            return get_data_quality_report_tool(self.backend)

        def get_leadership_update_report() -> str:
            """Generate a structured, comprehensive business update suitable for founders and leadership updates."""
            return generate_leadership_report(self.backend)

        # Keep references to the wrapper functions
        self.tools = [
            get_sales_pipeline_summary,
            get_work_order_and_financial_summary,
            get_sector_performance_report,
            get_data_quality_issues,
            get_leadership_update_report,
        ]

    def create_chat_session(self):
        """Create and return a new Gemini chat session with pre-configured tools."""
        return self.client.chats.create(
            model="gemini-3.5-flash",
            config=types.GenerateContentConfig(
                tools=self.tools,
                system_instruction=self.system_instruction,
                temperature=0.2,  # Low temperature for stable BI queries
            ),
        )

    def refresh_data(self):
        """Force refresh data from Monday.com."""
        self.backend.refresh_data()
