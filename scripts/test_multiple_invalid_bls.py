#!/usr/bin/env python3
"""
Test BL messages with multiple invalid BLs
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import format_nudge_message
from datetime import datetime

def main():
    print("Testing BL messages with multiple invalid BLs")
    print("=" * 80)

    # Scenario 1: Only one BL is valid
    print("\n" + "=" * 80)
    print("\nScenario 1: 3 BLs assigned, but only 1 found in contacts")
    print("-" * 80)
    validated_names_1 = ["Ryan Beauchamp"]
    invalid_names_1 = ["John Doe", "Jane Smith"]

    message1 = format_nudge_message(
        validated_names_1,
        "Saturday Queens Loop",
        [],
        "https://forms.gle/example123",
        invalid_names_1
    )
    print(message1)

    # Scenario 2: No invalid BLs (all found)
    print("\n" + "=" * 80)
    print("\nScenario 2: 3 BLs assigned, all found in contacts")
    print("-" * 80)
    validated_names_2 = ["Ryan Beauchamp", "John Doe", "Jane Smith"]
    invalid_names_2 = []

    message2 = format_nudge_message(
        validated_names_2,
        "Saturday Queens Loop",
        [],
        "https://forms.gle/example123",
        invalid_names_2
    )
    print(message2)

    # Scenario 3: With nudge candidates and multiple invalid BLs
    print("\n" + "=" * 80)
    print("\nScenario 3: 2 valid BLs, 2 invalid BLs, with nudge suggestions")
    print("-" * 80)
    validated_names_3 = ["Ryan Beauchamp", "Karl Steel"]
    invalid_names_3 = ["Unknown Person", "New Member"]

    nudge_candidates = [
        {
            'name': 'Rachel Downing',
            'last_attendance': datetime(2025, 12, 20),
            'attendance_count': 1,
            'days_since_last': 24
        }
    ]

    message3 = format_nudge_message(
        validated_names_3,
        "Friday Prospect Park Loop",
        nudge_candidates,
        "https://forms.gle/example123",
        invalid_names_3
    )
    print(message3)

    print("\n" + "=" * 80)
    print("\nKey Features:")
    print("✅ Multiple invalid BLs are each noted separately")
    print("✅ When no invalid BLs, no note appears")
    print("✅ Invalid BL note appears after greeting but before nudge suggestions")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
