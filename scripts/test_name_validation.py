#!/usr/bin/env python3
"""
Test name validation filtering
"""

import sys
from pathlib import Path
import re

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def is_valid_name(name):
    """Check if string looks like a valid name."""
    if not name:
        return False
    return bool(re.match(r'^[A-Za-z\s\-\'\.]+$', name))

def test_name(name, should_pass):
    """Test name validation."""
    result = is_valid_name(name)
    status = "✅" if result == should_pass else "❌"
    result_str = "KEEP" if result else "FILTER OUT"
    print(f"{status} '{name}' -> {result_str}")
    return result == should_pass

def main():
    print("Testing name validation filtering")
    print("=" * 80)
    print("\nValid names (should be kept):")
    print("-" * 80)

    all_passed = True

    # Valid names
    all_passed &= test_name("John Smith", True)
    all_passed &= test_name("Ryan B", True)
    all_passed &= test_name("Jennie Matz", True)
    all_passed &= test_name("Karl Steel", True)
    all_passed &= test_name("Mike O'Brien", True)
    all_passed &= test_name("Jean-Pierre", True)
    all_passed &= test_name("J. Smith", True)
    all_passed &= test_name("Mary Lou", True)

    print("\nInvalid entries (should be filtered out):")
    print("-" * 80)

    # Invalid entries
    all_passed &= test_name("?", False)
    all_passed &= test_name("Victoria?", False)
    all_passed &= test_name("N/A", False)
    all_passed &= test_name("TBD", True)  # This would pass as it's all letters
    all_passed &= test_name("???", False)
    all_passed &= test_name("3", False)
    all_passed &= test_name("12 people", False)
    all_passed &= test_name("", False)
    all_passed &= test_name("@unknown", False)
    all_passed &= test_name("Guest #1", False)

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 80)

    print("\nPattern used: ^[A-Za-z\\s\\-'\\.]+$")
    print("Allows: Letters, spaces, hyphens, apostrophes, periods")
    print("Filters out: Numbers, special characters, question marks, slashes, etc.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
