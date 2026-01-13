#!/usr/bin/env python3
"""
Test that BL messages only include validated BL names
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import format_nudge_message

def main():
    print("Testing BL message formatting with validated names only")
    print("=" * 80)

    # Scenario: Calendar has 3 BLs, but only 2 were validated/found in contacts
    calendar_bl_names = ["Ryan Beauchamp", "John Doe", "Jane Smith"]
    validated_bl_names = ["Ryan Beauchamp", "Jane Smith"]  # John Doe not found
    invalid_bl_names = ["John Doe"]

    print("\nScenario:")
    print(f"  BL names from calendar: {', '.join(calendar_bl_names)}")
    print(f"  Validated BL names (found in contacts): {', '.join(validated_bl_names)}")
    print(f"  Invalid BL names (not in contacts): {', '.join(invalid_bl_names)}")
    print()

    # Sample attendance form link
    attendance_form_link = "https://forms.gle/example123"

    # Test with no nudge candidates but with invalid BL
    print("-" * 80)
    print("\nTest 1: No nudge candidates, with invalid BL (with form link)")
    print("-" * 80)
    message1 = format_nudge_message(validated_bl_names, "Saturday Queens Loop", [], attendance_form_link, invalid_bl_names)
    print(message1)

    # Test with nudge candidates and invalid BL
    print("\n" + "-" * 80)
    print("\nTest 2: With nudge candidates and invalid BL (with form link)")
    print("-" * 80)
    from datetime import datetime
    nudge_candidates = [
        {
            'name': 'Rachel Downing',
            'last_attendance': datetime(2025, 12, 20),
            'attendance_count': 1,
            'days_since_last': 24
        },
        {
            'name': 'Randy Cruz',
            'last_attendance': datetime(2025, 12, 20),
            'attendance_count': 2,
            'days_since_last': 24
        }
    ]
    message2 = format_nudge_message(validated_bl_names, "Saturday Queens Loop", nudge_candidates, attendance_form_link, invalid_bl_names)
    print(message2)

    # Test without invalid BLs
    print("\n" + "-" * 80)
    print("\nTest 3: All BLs valid (no invalid BL note)")
    print("-" * 80)
    message3 = format_nudge_message(validated_bl_names, "Saturday Queens Loop", nudge_candidates, attendance_form_link, None)
    print(message3)

    # Test without form link (backward compatibility)
    print("\n" + "-" * 80)
    print("\nTest 4: Without form link (backward compatibility)")
    print("-" * 80)
    message4 = format_nudge_message(validated_bl_names, "Saturday Queens Loop", nudge_candidates, None, None)
    print(message4)

    print("\n" + "=" * 80)
    print("\nVerification:")
    print("✅ Message greeting should include: Ryan Beauchamp and Jane Smith")
    print("✅ Message should include note about: John Doe (not validated/no contact info)")
    print("✅ Messages without invalid BLs should not show the note")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
