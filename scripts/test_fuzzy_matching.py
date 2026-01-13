#!/usr/bin/env python3
"""
Test the fuzzy matching logic to see how it handles various run names.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.attendance_utils import fuzzy_match_location

def test_match(name1, name2):
    score = fuzzy_match_location(name1, name2)
    print(f"  '{name1}' vs '{name2}': {score:.3f}")
    return score

def main():
    print("Testing fuzzy matching with 'run' stripped out\n")
    print("=" * 80)

    print("\nTest 1: Should match (same location, different variations)")
    print("-" * 80)
    test_match("Saturday Queens Loop", "Queens Run")
    test_match("Saturday Queens Loop", "Queens Saturday Run")
    test_match("Friday Prospect Park Loop", "Friday PP Loop Run")
    test_match("Tuesday Chinatown Office Loop", "Tuesday Chinatown Run")

    print("\nTest 2: Should NOT match (different locations)")
    print("-" * 80)
    test_match("Saturday Queens Loop", "Queens R2C")
    test_match("Saturday Queens Loop", "Queens Run2Canvass")
    test_match("Friday Prospect Park Loop", "Friday Manhattan Run")
    test_match("Tuesday Chinatown Office Loop", "Tuesday Brooklyn Run")

    print("\nTest 3: Edge cases")
    print("-" * 80)
    test_match("North Brooklyn Run", "North Brooklyn Run Series")
    test_match("Thursday South Brooklyn", "Thursday North Brooklyn")
    test_match("Sunday Central Park Loop", "Sunday CP")
    test_match("Sunday Central Park Loop", "CP R2C")

    print("\n" + "=" * 80)
    print(f"\nCurrent threshold: 0.8")
    print("Scores >= 0.8 will be considered matches\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
