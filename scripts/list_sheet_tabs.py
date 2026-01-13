#!/usr/bin/env python3
"""
List all tabs/sheets in the attendance spreadsheet.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config_utils import require_variable
from utils.google_utils import get_google_sheets_service

def main():
    sheet_id = require_variable('attendance_sheet_id')

    print(f"📊 Checking spreadsheet: {sheet_id}\n")

    sheets_service = get_google_sheets_service()

    # Get spreadsheet metadata
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()

    sheets = spreadsheet.get('sheets', [])

    print(f"Found {len(sheets)} sheet(s):\n")
    print("=" * 80)

    for i, sheet in enumerate(sheets, 1):
        properties = sheet.get('properties', {})
        title = properties.get('title', 'Unknown')
        sheet_id = properties.get('sheetId', 'Unknown')
        index = properties.get('index', 'Unknown')

        print(f"\n{i}. Title: {title}")
        print(f"   Sheet ID: {sheet_id}")
        print(f"   Index: {index}")

        # Get row/column counts
        grid_props = properties.get('gridProperties', {})
        rows = grid_props.get('rowCount', '?')
        cols = grid_props.get('columnCount', '?')
        print(f"   Size: {rows} rows × {cols} columns")

    print("\n" + "=" * 80)

    # Try to fetch first few rows from the first sheet to see the format
    if sheets:
        first_sheet_title = sheets[0].get('properties', {}).get('title', 'Sheet1')
        print(f"\nFetching sample data from '{first_sheet_title}'...\n")

        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{first_sheet_title}'!A1:Z30"
        ).execute()

        values = result.get('values', [])

        if values:
            print(f"First 10 rows:\n")
            for i, row in enumerate(values[:10], 1):
                print(f"Row {i}: {row[:10]}")  # Show first 10 columns
        else:
            print("No data found in sheet")

    return 0

if __name__ == "__main__":
    sys.exit(main())
