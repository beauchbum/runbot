#!/usr/bin/env python3
"""
Test script to demonstrate fuzzy matching with multiple runs on the same day.
"""

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import (
    parse_attendance_sheet,
    find_similar_runs,
)

def main():
    print("📊 Testing fuzzy matching with multiple runs on same day...\n")

    try:
        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        if not all_runs:
            print("⚠️  No runs found - cannot test")
            return 1

        # Find dates with multiple runs
        from collections import defaultdict
        runs_by_date = defaultdict(list)
        for run in all_runs:
            runs_by_date[run['date'].date()].append(run)

        dates_with_multiple = [(date, runs) for date, runs in runs_by_date.items() if len(runs) > 1]

        if dates_with_multiple:
            print("=" * 80)
            print(f"\nFound {len(dates_with_multiple)} date(s) with multiple runs:\n")
            for date, runs in dates_with_multiple[:3]:  # Show first 3
                print(f"{date.strftime('%Y-%m-%d %A')}:")
                for run in runs:
                    print(f"  - {run['run_name']} ({len(run['attendees'])} attendees)")
            print()
        else:
            print("⚠️  No dates with multiple runs found\n")

        # Test Case 1: Test with a varied name for a Friday run
        print("=" * 80)
        print("\nTest Case 1: Fuzzy matching for Friday PP loop\n")
        print("Scenario: Action Network event called 'Friday PP Loop' and calendar says 'Friday PP loop'")
        print("Should match attendance entries for 'Friday PP loop' but not 'Friday PP Loop' (case variations)\n")

        test_names_1 = ["Friday PP Loop", "Friday PP loop"]
        similar_runs_1 = find_similar_runs(
            target_run_names=test_names_1,
            target_day_of_week="Friday",
            all_runs=all_runs
        )
        print(f"\n✅ Found {len(similar_runs_1)} similar runs")
        if similar_runs_1:
            print("\nMatched runs:")
            for run in similar_runs_1[:5]:
                print(f"  - {run['run_name']} on {run['date'].strftime('%Y-%m-%d')} ({len(run['attendees'])} attendees)")

        # Test Case 2: Test with very different names that should still match
        print("\n" + "=" * 80)
        print("\nTest Case 2: Fuzzy matching with different name variations\n")
        print("Scenario: Action Network event called 'LES Tuesday' and calendar says 'LES Tuesdays'")
        print("Should match 'LES Tuesdays' from attendance sheet\n")

        test_names_2 = ["LES Tuesday", "LES Tuesdays"]
        similar_runs_2 = find_similar_runs(
            target_run_names=test_names_2,
            target_day_of_week="Tuesday",
            all_runs=all_runs
        )
        print(f"\n✅ Found {len(similar_runs_2)} similar runs")
        if similar_runs_2:
            print("\nMatched runs:")
            for run in similar_runs_2[:5]:
                print(f"  - {run['run_name']} on {run['date'].strftime('%Y-%m-%d')} ({len(run['attendees'])} attendees)")

        # Test Case 3: Test with names that should NOT match
        print("\n" + "=" * 80)
        print("\nTest Case 3: Names that should NOT match on same day\n")
        print("Scenario: Looking for 'Saturday Queens' should not match 'Saturday Manhattan' (if it exists)\n")

        test_names_3 = ["Saturday Queens", "Queens Saturday"]
        similar_runs_3 = find_similar_runs(
            target_run_names=test_names_3,
            target_day_of_week="Saturday",
            all_runs=all_runs
        )
        print(f"\n✅ Found {len(similar_runs_3)} similar runs")
        if similar_runs_3:
            print("\nMatched runs:")
            for run in similar_runs_3[:10]:
                print(f"  - {run['run_name']} on {run['date'].strftime('%Y-%m-%d')} ({len(run['attendees'])} attendees)")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
