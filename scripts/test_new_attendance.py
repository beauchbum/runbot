#!/usr/bin/env python3
"""
Test script to examine the new attendance sheet format.
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

    print(f"📊 Fetching attendance sheet: {sheet_id}")

    sheets_service = get_google_sheets_service()

    # Fetch more data to understand the pattern
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range='Attendance!A1:Z30'
    ).execute()

    values = result.get('values', [])

    print(f"\nTotal rows: {len(values)}")
    print("\n" + "="*80)

    # Print all rows with clear formatting
    for i, row in enumerate(values, 1):
        print(f"\nRow {i}:")
        # Pad row to consistent length for easier viewing
        padded_row = row + [''] * (26 - len(row))
        for j, cell in enumerate(padded_row):
            if cell:  # Only print non-empty cells
                print(f"  Col {j+1:2d}: {cell}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
