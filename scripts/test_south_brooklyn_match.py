#!/usr/bin/env python3
"""
Test specific case: Thursday South Brooklyn should match South Brooklyn Run
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from utils.attendance_utils import parse_attendance_sheet, find_similar_runs
from utils.config_utils import require_variable

def main():
    print("Testing Thursday South Brooklyn matching\n")
    print("=" * 80)

    try:
        # Initialize OpenAI client
        openai_api_key = require_variable('openai_api_key')
        client = OpenAI(api_key=openai_api_key)

        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"\n✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        # Show what Thursday runs exist
        print("Thursday runs in attendance sheet:")
        thursday_runs = [r for r in all_runs if r['day_of_week'] == 'Thursday']
        unique_thursday_names = set(r['run_name'] for r in thursday_runs)
        for name in sorted(unique_thursday_names):
            count = sum(1 for r in thursday_runs if r['run_name'] == name)
            print(f"  - {name}: {count} occurrences")

        # Test matching
        print("\n" + "=" * 80)
        print("\nTest: 'Thursday South Brooklyn' should match attendance records")
        print("-" * 80)

        similar_runs = find_similar_runs(
            target_run_names=["Thursday South Brooklyn", "South Brooklyn"],
            target_day_of_week="Thursday",
            all_runs=all_runs,
            client=client
        )

        print(f"\n✅ Matched {len(similar_runs)} runs:")
        unique_names = set(run['run_name'] for run in similar_runs)
        for name in unique_names:
            matching = [r for r in similar_runs if r['run_name'] == name]
            print(f"  - {name}: {len(matching)} occurrences")
            for r in matching[:3]:
                print(f"    - {r['date'].strftime('%Y-%m-%d')}: {len(r['attendees'])} attendees")

        if not similar_runs:
            print("  ⚠️  No matches found!")

        print("\n" + "=" * 80)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
