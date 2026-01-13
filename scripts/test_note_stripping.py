#!/usr/bin/env python3
"""
Test parenthetical note stripping from attendee names
"""

import sys
from pathlib import Path
import re

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def strip_parenthetical_notes(name):
    """Strip parenthetical notes from name."""
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
    return name

def test_strip(original, expected):
    """Test name stripping."""
    result = strip_parenthetical_notes(original)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{original}' -> '{result}' (expected: '{expected}')")
    return result == expected

def main():
    print("Testing parenthetical note stripping from attendee names")
    print("=" * 80)
    print()

    all_passed = True

    # Test various patterns
    print("Test Cases:")
    print("-" * 80)

    # Common markers
    all_passed &= test_strip("Jennie Matz (T)", "Jennie Matz")
    all_passed &= test_strip("Shereen Fatima (H)", "Shereen Fatima")
    all_passed &= test_strip("Ryan B (first timer)", "Ryan B")

    # No parentheses (should remain unchanged)
    all_passed &= test_strip("John Smith", "John Smith")
    all_passed &= test_strip("Karl Steel", "Karl Steel")

    # Multiple words in parentheses
    all_passed &= test_strip("Alex Jones (new member DSA)", "Alex Jones")
    all_passed &= test_strip("Sarah Chen (brought friend)", "Sarah Chen")

    # Edge cases
    all_passed &= test_strip("Mike O'Brien (tail)", "Mike O'Brien")
    all_passed &= test_strip("Jean-Pierre (head)", "Jean-Pierre")
    all_passed &= test_strip("Lisa (first run)", "Lisa")

    # Multiple parentheses (should only strip last one)
    all_passed &= test_strip("John (J) Smith (H)", "John (J) Smith")

    # With extra spaces
    all_passed &= test_strip("Rachel Downing  (T)  ", "Rachel Downing")
    all_passed &= test_strip("  Randy Cruz (H)  ", "Randy Cruz")

    print()
    print("=" * 80)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 80)

    print("\nBenefits:")
    print("• Better deduplication: 'Jennie Matz (T)' and 'Jennie Matz (H)' now match")
    print("• Cleaner nudge messages: No markers like (T), (H), (first timer) shown")
    print("• More accurate attendance tracking: Same person with different notes counted as one person")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
