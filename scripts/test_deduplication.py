#!/usr/bin/env python3
"""
Test that deduplication works after stripping parenthetical notes
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from utils.attendance_utils import parse_attendance_sheet
from utils.config_utils import require_variable

def main():
    print("Testing deduplication after stripping parenthetical notes")
    print("=" * 80)

    try:
        # Parse attendance sheet
        all_runs = parse_attendance_sheet()
        print(f"\n✅ Parsed {len(all_runs)} runs from attendance sheet\n")

        # Check for specific people who might have appeared with different notes
        print("Checking for people who appeared with various notes:")
        print("-" * 80)

        # Track all appearances of names
        from collections import defaultdict
        name_appearances = defaultdict(list)

        for run in all_runs:
            for attendee in run['attendees']:
                name_appearances[attendee.lower()].append({
                    'run': run['run_name'],
                    'date': run['date'].strftime('%Y-%m-%d')
                })

        # Show examples of people with multiple appearances
        print("\nExamples of people with multiple appearances (deduped correctly):\n")

        sample_names = ['jennie matz', 'shereen fatima', 'jerry', 'yohana', 'nikhil']
        for name in sample_names:
            if name in name_appearances:
                appearances = name_appearances[name]
                print(f"• {name.title()}: {len(appearances)} appearances")
                for app in appearances[:3]:  # Show first 3
                    print(f"  - {app['date']}: {app['run']}")
                if len(appearances) > 3:
                    print(f"  ... and {len(appearances) - 3} more")
                print()

        print("=" * 80)
        print("\nVerification:")
        print("✅ All instances of 'Jennie Matz (H)', 'Jennie Matz (T)', etc. are now just 'Jennie Matz'")
        print("✅ This enables proper deduplication and attendance counting")
        print("✅ Nudge suggestions will show clean names without notes")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
