#!/usr/bin/env python3
"""
View the actual attendance data from the spreadsheet.
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

    print(f"📊 Fetching data from spreadsheet: {sheet_id}\n")

    sheets_service = get_google_sheets_service()

    # Fetch from Form Responses 1 (no quotes needed for simple names)
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Form Responses 1!A1:Z30"
    ).execute()

    values = result.get('values', [])

    print(f"Total rows fetched: {len(values)}\n")
    print("=" * 120)

    if values:
        # Show first 20 rows with full details
        for i, row in enumerate(values[:20], 1):
            print(f"\nRow {i}:")
            # Pad row to show empty columns
            padded_row = row + [''] * (max(10, len(values[0])) - len(row))
            for j, cell in enumerate(padded_row[:17], 1):  # Show up to 17 columns
                if cell:
                    # Truncate long cells
                    cell_display = cell[:100] + "..." if len(cell) > 100 else cell
                    print(f"  Col {j:2d}: {cell_display}")
    else:
        print("No data found")

    print("\n" + "=" * 120)

    return 0

if __name__ == "__main__":
    sys.exit(main())
