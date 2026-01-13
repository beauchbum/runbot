#!/usr/bin/env python3
"""
Test script to verify nudge identification logic with the updated parser.
"""

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from utils.attendance_utils import (
    parse_attendance_sheet,
    find_similar_runs,
    identify_nudge_candidates
)
from utils.config_utils import require_variable

def main():
    print("📊 Testing nudge identification logic...\n")

    try:
        # Initialize OpenAI client
        openai_api_key = require_variable('openai_api_key')
        client = OpenAI(api_key=openai_api_key)

        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        if not all_runs:
            print("⚠️  No runs found - cannot test nudge logic")
            return 1

        # Test with a sample run
        # Let's use "Saturday Queens" on Saturday as a test case
        # Simulate that Action Network might call it something slightly different
        test_action_network_name = "Queens Saturday Run"
        test_calendar_name = "Saturday Queens Loop"
        test_day_of_week = "Saturday"

        print("=" * 80)
        print(f"\nTest Case: Finding similar runs to '{test_action_network_name}' or '{test_calendar_name}' on {test_day_of_week}s\n")

        # Find similar runs (using LLM matching)
        similar_runs = find_similar_runs(
            target_run_names=[test_action_network_name, test_calendar_name],
            target_day_of_week=test_day_of_week,
            all_runs=all_runs,
            client=client
        )

        print(f"\n✅ Found {len(similar_runs)} similar runs")

        if similar_runs:
            print("\nSimilar runs:")
            for run in similar_runs[:5]:  # Show first 5
                print(f"  - {run['run_name']} on {run['date'].strftime('%Y-%m-%d')} ({len(run['attendees'])} attendees)")

            # Test nudge candidate identification
            eastern_tz = ZoneInfo("America/New_York")
            current_time = datetime.now(eastern_tz)

            print("\n" + "=" * 80)
            print(f"\nIdentifying nudge candidates for upcoming '{test_action_network_name}' / '{test_calendar_name}'...\n")

            candidates = identify_nudge_candidates(
                target_run_names=[test_action_network_name, test_calendar_name],
                target_day_of_week=test_day_of_week,
                current_time=current_time,
                all_runs=all_runs,
                client=client,
                max_candidates=10
            )

            print(f"\n✅ Identified {len(candidates)} nudge candidates")

            if candidates:
                print("\nTop nudge candidates:")
                for i, candidate in enumerate(candidates[:10], 1):
                    print(f"\n{i}. {candidate['name']}")
                    print(f"   Last attended: {candidate['last_attendance'].strftime('%Y-%m-%d')}")
                    print(f"   Total attendance: {candidate['attendance_count']}x")
                    print(f"   Days since last: {candidate['days_since_last']} days")
            else:
                print("   No candidates identified (all attendees may be regulars)")

        return 0

    except Exception as e:
        print(f"❌ Error testing nudge logic: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
