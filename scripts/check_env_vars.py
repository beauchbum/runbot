#!/usr/bin/env python3
"""
Check environment variable values.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config_utils import require_variable, get_variable

def main():
    print("=" * 80)
    print("Environment Variables Check")
    print("=" * 80)

    # Check attendance sheet ID
    try:
        attendance_sheet_id = require_variable('attendance_sheet_id')
        print(f"\nattendance_sheet_id: {attendance_sheet_id}")
    except Exception as e:
        print(f"\n❌ Error getting attendance_sheet_id: {e}")

    # Check calendar document ID
    try:
        calendar_doc_id = require_variable('calendar_document_id')
        print(f"calendar_document_id: {calendar_doc_id}")
    except Exception as e:
        print(f"❌ Error getting calendar_document_id: {e}")

    print("\n" + "=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
