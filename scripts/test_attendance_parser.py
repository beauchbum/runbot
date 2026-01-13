#!/usr/bin/env python3
"""
Test script to verify the updated attendance sheet parser.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import parse_attendance_sheet

def main():
    print("📊 Testing attendance sheet parser with new format...\n")

    try:
        runs = parse_attendance_sheet()

        print(f"\n✅ Successfully parsed {len(runs)} runs\n")
        print("=" * 80)

        if runs:
            print("\nSample of parsed runs:")
            for i, run in enumerate(runs[:5], 1):  # Show first 5 runs
                print(f"\n{i}. Run: {run['run_name']}")
                print(f"   Date: {run['date'].strftime('%Y-%m-%d %A')}")
                print(f"   Attendees ({len(run['attendees'])}): {', '.join(run['attendees'][:8])}")
                if len(run['attendees']) > 8:
                    print(f"   ... and {len(run['attendees']) - 8} more")

            print("\n" + "=" * 80)
            print("\nRuns by day of week:")
            from collections import Counter
            day_counts = Counter(run['day_of_week'] for run in runs)
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                if day in day_counts:
                    print(f"   {day}: {day_counts[day]} runs")

            print("\n" + "=" * 80)
            print("\nRun name distribution:")
            run_name_counts = Counter(run['run_name'] for run in runs)
            for name, count in run_name_counts.most_common(10):
                print(f"   {name}: {count} occurrences")
        else:
            print("⚠️  No runs parsed - check sheet format")

        return 0

    except Exception as e:
        print(f"❌ Error testing parser: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
