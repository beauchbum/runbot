#!/usr/bin/env python3
"""
Test BL exclusion with fuzzy matching
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from difflib import SequenceMatcher

def test_bl_match(candidate_name, bl_names, threshold=0.8):
    """Test if a candidate name matches any BL name with fuzzy matching."""
    candidate_lower = candidate_name.lower()

    print(f"\nCandidate: '{candidate_name}'")

    for bl_name in bl_names:
        bl_lower = bl_name.lower()
        similarity = SequenceMatcher(None, candidate_lower, bl_lower).ratio()

        if similarity >= threshold:
            print(f"  ✅ Matches BL '{bl_name}' (similarity: {similarity:.2f}) - WOULD BE EXCLUDED")
            return True
        else:
            print(f"  ❌ '{bl_name}' (similarity: {similarity:.2f})")

    print(f"  ✅ No BL match - WOULD BE INCLUDED in nudges")
    return False

def main():
    print("Testing BL exclusion with fuzzy matching")
    print("=" * 80)
    print("\nThreshold: 0.8 (must be 80% similar to exclude)")
    print("=" * 80)

    # Sample BL names
    bl_names = ["Ryan Beauchamp", "Jennie Matz", "Karl Steel"]

    print("\n\nTest Cases:")
    print("-" * 80)

    # Test exact match
    test_bl_match("Ryan Beauchamp", bl_names)

    # Test shortened version
    test_bl_match("Ryan B", bl_names)

    # Test first name only
    test_bl_match("Ryan", bl_names)

    # Test with middle initial
    test_bl_match("Ryan J Beauchamp", bl_names)

    # Test completely different name
    test_bl_match("John Smith", bl_names)

    # Test partial match with attendee marker
    test_bl_match("Jennie Matz (T)", bl_names)

    # Test similar but different name
    test_bl_match("Karl S", bl_names)

    # Test close match
    test_bl_match("Jennie M", bl_names)

    print("\n" + "=" * 80)
    print("\nSummary:")
    print("- Names with 80%+ similarity to BL names will be excluded from nudges")
    print("- This handles variations like 'Ryan B' vs 'Ryan Beauchamp'")
    print("- Completely different names will still be included in nudges")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
