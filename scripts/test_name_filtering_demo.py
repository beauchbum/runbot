#!/usr/bin/env python3
"""
Demonstrate name filtering and cleaning in action
"""

import sys
from pathlib import Path
import re

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def process_attendee_name(raw_name):
    """Process an attendee name: strip notes, validate."""
    # Take first line only
    name = raw_name.split('\n')[0].strip()

    # Strip parenthetical notes
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()

    # Validate - must be alphabetical with spaces, hyphens, apostrophes, periods
    if name and re.match(r'^[A-Za-z\s\-\'\.]+$', name):
        return name
    return None

def main():
    print("Demonstration: Name Filtering and Cleaning")
    print("=" * 80)

    # Simulate various attendee entries from the form
    test_entries = [
        "Jennie Matz (T)",
        "Shereen Fatima (H)",
        "Karl Steel",
        "Victoria?",
        "Ryan B (first timer)",
        "Mike O'Brien (tail)",
        "Jean-Pierre",
        "???",
        "12",
        "N/A",
        "J. Smith",
        "Guest #1",
        "Yohana (head)",
        "",
        "Charles (in DSA)",
    ]

    print("\nProcessing attendee entries from form:\n")
    print(f"{'Raw Entry':<30} | {'Cleaned':<20} | Status")
    print("-" * 80)

    kept = []
    filtered = []

    for entry in test_entries:
        cleaned = process_attendee_name(entry)
        if cleaned:
            status = "✅ KEEP"
            kept.append(cleaned)
        else:
            status = "❌ FILTER OUT"
            filtered.append(entry)

        display_entry = entry if entry else "(empty)"
        display_cleaned = cleaned if cleaned else "(invalid)"
        print(f"{display_entry:<30} | {display_cleaned:<20} | {status}")

    print("\n" + "=" * 80)
    print(f"\nSummary:")
    print(f"  Total entries: {len(test_entries)}")
    print(f"  Kept: {len(kept)} ({len(kept)/len(test_entries)*100:.0f}%)")
    print(f"  Filtered out: {len(filtered)} ({len(filtered)/len(test_entries)*100:.0f}%)")

    print(f"\n✅ Final clean attendee list:")
    for name in kept:
        print(f"  • {name}")

    print(f"\n❌ Filtered out (won't appear in nudges):")
    for entry in filtered:
        display = entry if entry else "(empty)"
        print(f"  • {display}")

    print("\n" + "=" * 80)
    print("\nBenefits:")
    print("  • No confusing markers like (T), (H) in nudge messages")
    print("  • No invalid entries like '?', 'N/A', numbers")
    print("  • Clean, professional appearance for BL communications")
    print("  • Better deduplication (same person with different notes = one person)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
