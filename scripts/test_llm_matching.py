#!/usr/bin/env python3
"""
Test LLM-based matching to verify it can distinguish between different run types.
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
    print("Testing LLM-based run matching\n")
    print("=" * 80)

    try:
        # Initialize OpenAI client
        openai_api_key = require_variable('openai_api_key')
        client = OpenAI(api_key=openai_api_key)

        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"\n✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        # Test Case 1: Should match Queens Loop but NOT Queens R2C
        print("\n" + "=" * 80)
        print("\nTest 1: Queens Saturday Run should match 'Saturday Queens Loop' but NOT 'Queens R2C'")
        print("-" * 80)

        similar_runs_1 = find_similar_runs(
            target_run_names=["Queens Saturday Run", "Saturday Queens Loop"],
            target_day_of_week="Saturday",
            all_runs=all_runs,
            client=client
        )

        print(f"\nMatched {len(similar_runs_1)} runs:")
        unique_names_1 = set(run['run_name'] for run in similar_runs_1)
        for name in unique_names_1:
            count = sum(1 for r in similar_runs_1 if r['run_name'] == name)
            print(f"  - {name}: {count} occurrences")

        # Test Case 2: Should match Tuesday Chinatown runs
        print("\n" + "=" * 80)
        print("\nTest 2: Tuesday Chinatown should match 'Tuesday Chinatown Office Loop' but NOT 'North Brooklyn Run'")
        print("-" * 80)

        similar_runs_2 = find_similar_runs(
            target_run_names=["Tuesday Chinatown", "Chinatown Office Loop"],
            target_day_of_week="Tuesday",
            all_runs=all_runs,
            client=client
        )

        print(f"\nMatched {len(similar_runs_2)} runs:")
        unique_names_2 = set(run['run_name'] for run in similar_runs_2)
        for name in unique_names_2:
            count = sum(1 for r in similar_runs_2 if r['run_name'] == name)
            print(f"  - {name}: {count} occurrences")

        # Test Case 3: Should match Friday PP Loop
        print("\n" + "=" * 80)
        print("\nTest 3: Friday Prospect Park should match 'Friday Prospect Park Loop'")
        print("-" * 80)

        similar_runs_3 = find_similar_runs(
            target_run_names=["Friday Prospect Park", "Friday PP Loop"],
            target_day_of_week="Friday",
            all_runs=all_runs,
            client=client
        )

        print(f"\nMatched {len(similar_runs_3)} runs:")
        unique_names_3 = set(run['run_name'] for run in similar_runs_3)
        for name in unique_names_3:
            count = sum(1 for r in similar_runs_3 if r['run_name'] == name)
            print(f"  - {name}: {count} occurrences")

        print("\n" + "=" * 80)
        print("\nAll tests completed!")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
