#!/usr/bin/env python3
"""
Quick script to examine the attendance sheet structure.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.google_utils import get_google_sheets_service

def main():
    sheet_id = os.getenv('ATTENDANCE_SHEET_ID')
    if not sheet_id:
        print("❌ ATTENDANCE_SHEET_ID environment variable not set")
        return 1

    print(f"📊 Fetching attendance sheet: {sheet_id}")

    try:
        sheets_service = get_google_sheets_service()

        # Get sheet metadata to see all tabs
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])

        print(f"\n📋 Found {len(sheets)} sheet(s):")
        for sheet in sheets:
            sheet_title = sheet['properties']['title']
            print(f"  - {sheet_title}")

        # Fetch the first sheet's data (or you can specify a sheet name)
        first_sheet_name = sheets[0]['properties']['title'] if sheets else 'Sheet1'
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{first_sheet_name}!A1:Z100"  # Fetch first 100 rows, columns A-Z
        ).execute()

        values = result.get('values', [])

        if not values:
            print("\n❌ No data found in sheet")
            return 1

        print(f"\n📄 Sheet '{first_sheet_name}' data:")
        print(f"   Total rows: {len(values)}")

        # Print headers
        if values:
            print(f"\n🏷️  Headers (Row 1):")
            for i, header in enumerate(values[0], 1):
                print(f"   Column {i}: {header}")

        # Print first few rows as sample
        print(f"\n📝 Sample data (first 5 rows):")
        for i, row in enumerate(values[:5], 1):
            print(f"\nRow {i}:")
            for j, cell in enumerate(row):
                header = values[0][j] if j < len(values[0]) else f"Column {j+1}"
                print(f"   {header}: {cell}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
