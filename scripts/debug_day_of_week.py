#!/usr/bin/env python3
"""
Debug script to examine day of week parsing for attendance sheet entries.
"""

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import parse_attendance_sheet

def main():
    print("📊 Debugging day of week parsing...\n")
    print(f"Current date: {datetime.now().strftime('%Y-%m-%d %A')}\n")
    print("=" * 80)

    try:
        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"\n✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        if not all_runs:
            print("⚠️  No runs found")
            return 1

        # Group by day of week
        from collections import defaultdict
        runs_by_day = defaultdict(list)
        for run in all_runs:
            runs_by_day[run['day_of_week']].append(run)

        print("=" * 80)
        print("\nRuns grouped by day of week:\n")

        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            if day in runs_by_day:
                runs = runs_by_day[day]
                print(f"\n{day} ({len(runs)} runs):")
                for run in runs:
                    print(f"  - {run['date'].strftime('%Y-%m-%d')}: {run['run_name']} ({len(run['attendees'])} attendees)")

        # Show all unique run names
        print("\n" + "=" * 80)
        print("\nAll unique run names in attendance sheet:\n")
        unique_names = sorted(set(run['run_name'] for run in all_runs))
        for name in unique_names:
            # Count occurrences
            count = sum(1 for run in all_runs if run['run_name'] == name)
            # Find which days
            days = set(run['day_of_week'] for run in all_runs if run['run_name'] == name)
            print(f"  - {name}: {count} occurrences on {', '.join(sorted(days))}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
