"""
Monday.com GraphQL API client.
Handles fetching boards, paginating items, and parsing column values.
"""

import requests
import json
import os
import pandas as pd
from typing import Optional


class MondayClient:
    """Read-only client for the Monday.com GraphQL API (v2024-01)."""

    ENDPOINT = "https://api.monday.com/v2"

    def __init__(self, api_token: str = None):
        self.api_token = api_token or os.getenv("MONDAY_API_TOKEN")
        if not self.api_token:
            raise ValueError("Monday.com API token is required")
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01",
        }

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _execute(self, query: str) -> dict:
        """Execute a raw GraphQL query and return the data block."""
        try:
            resp = requests.post(
                self.ENDPOINT,
                json={"query": query},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            if "errors" in body:
                raise Exception(f"GraphQL error: {body['errors']}")
            return body.get("data", {})
        except requests.RequestException as exc:
            raise Exception(f"Monday.com API request failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #

    def get_board_items(self, board_id: str, limit: int = 500) -> list:
        """Fetch ALL items from a board using cursor-based pagination."""
        all_items: list = []
        cursor: Optional[str] = None

        while True:
            if cursor:
                query = f"""
                {{
                  next_items_page(limit: {limit}, cursor: "{cursor}") {{
                    cursor
                    items {{
                      id name
                      column_values {{
                        id text value
                        column {{ title type }}
                      }}
                    }}
                  }}
                }}
                """
                data = self._execute(query)
                page = data.get("next_items_page", {})
            else:
                query = f"""
                {{
                  boards(ids: [{board_id}]) {{
                    items_page(limit: {limit}) {{
                      cursor
                      items {{
                        id name
                        column_values {{
                          id text value
                          column {{ title type }}
                        }}
                      }}
                    }}
                  }}
                }}
                """
                data = self._execute(query)
                boards = data.get("boards", [])
                if not boards:
                    break
                page = boards[0].get("items_page", {})

            items = page.get("items", [])
            all_items.extend(items)
            cursor = page.get("cursor")
            if not cursor or not items:
                break

        return all_items

    def parse_item(self, item: dict) -> dict:
        """Flatten a Monday.com item into a plain dict."""
        record: dict = {"Deal Name": item["name"]}

        for col in item.get("column_values", []):
            title = col["column"]["title"]
            col_type = col["column"]["type"]
            text: str = (col.get("text") or "").strip()
            value: str = col.get("value") or ""

            if col_type == "numbers":
                try:
                    record[title] = float(text) if text else None
                except ValueError:
                    record[title] = None
            elif col_type == "date":
                record[title] = text if text else None
            elif col_type == "people":
                try:
                    val = json.loads(value) if value else {}
                    persons = val.get("personsAndTeams", [])
                    record[title] = (
                        ", ".join(p.get("name", "") for p in persons) or None
                    )
                except Exception:
                    record[title] = text or None
            else:  # status, dropdown, text, name, …
                record[title] = text if text else None

        return record

    def get_board_as_dataframe(self, board_id: str) -> pd.DataFrame:
        """Return the entire board as a pandas DataFrame."""
        items = self.get_board_items(board_id)
        records = [self.parse_item(item) for item in items]
        return pd.DataFrame(records) if records else pd.DataFrame()
