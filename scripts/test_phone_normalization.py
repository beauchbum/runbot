#!/usr/bin/env python3
"""
Test script to validate phone number normalization.

This script tests various phone number formats to ensure they all normalize
correctly to E.164 format (+1XXXXXXXXXX).

Usage:
    python scripts/test_phone_normalization.py
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.phone_utils import normalize_phone_number, validate_phone_number


def test_phone_normalization():
    """Test various phone number formats."""

    test_cases = [
        # Valid formats that should normalize to +15551234567
        ("5551234567", "+15551234567", True),
        ("+15551234567", "+15551234567", True),
        ("15551234567", "+15551234567", True),
        ("+1 555 123 4567", "+15551234567", True),
        ("(555) 123-4567", "+15551234567", True),
        ("555-123-4567", "+15551234567", True),
        ("555.123.4567", "+15551234567", True),
        ("+1-555-123-4567", "+15551234567", True),
        ("1 (555) 123-4567", "+15551234567", True),

        # Invalid formats that should raise ValueError
        ("", None, False),
        ("123", None, False),
        ("12345", None, False),
        ("555123456", None, False),  # 9 digits
        ("555123456789", None, False),  # 12 digits
        ("25551234567", None, False),  # 11 digits not starting with 1
        ("abc5551234567", None, False),  # Contains letters
    ]

    print("=" * 80)
    print("PHONE NUMBER NORMALIZATION TESTS")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for input_phone, expected_output, should_succeed in test_cases:
        try:
            result = normalize_phone_number(input_phone)

            if should_succeed:
                if result == expected_output:
                    print(f"✅ PASS: '{input_phone}' -> '{result}'")
                    passed += 1
                else:
                    print(f"❌ FAIL: '{input_phone}' -> '{result}' (expected '{expected_output}')")
                    failed += 1
            else:
                print(f"❌ FAIL: '{input_phone}' should have raised ValueError but got '{result}'")
                failed += 1

        except ValueError as e:
            if not should_succeed:
                print(f"✅ PASS: '{input_phone}' correctly raised ValueError: {e}")
                passed += 1
            else:
                print(f"❌ FAIL: '{input_phone}' raised unexpected ValueError: {e}")
                failed += 1
        except Exception as e:
            print(f"❌ FAIL: '{input_phone}' raised unexpected error: {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    print()

    # Test validation function
    print("=" * 80)
    print("PHONE NUMBER VALIDATION TESTS")
    print("=" * 80)
    print()

    validation_tests = [
        ("+15551234567", True),
        ("+1 555 123 4567", True),  # Will be normalized then validated
        ("5551234567", True),  # Will be normalized then validated
        ("+25551234567", False),  # Non-US country code
        ("555123456", False),  # 9 digits
        ("invalid", False),
    ]

    val_passed = 0
    val_failed = 0

    for phone, expected_valid in validation_tests:
        result = validate_phone_number(phone)
        if result == expected_valid:
            status = "✅ PASS"
            val_passed += 1
        else:
            status = "❌ FAIL"
            val_failed += 1
        print(f"{status}: validate_phone_number('{phone}') -> {result} (expected {expected_valid})")

    print()
    print("=" * 80)
    print(f"VALIDATION RESULTS: {val_passed} passed, {val_failed} failed")
    print("=" * 80)
    print()

    total_passed = passed + val_passed
    total_failed = failed + val_failed

    print("=" * 80)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print("=" * 80)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(test_phone_normalization())
