#!/usr/bin/env python3
"""
Test script to validate message history fetching from Twilio.

This script fetches and displays all messages sent from our Twilio number
to a specific phone number across all conversations.

Phone numbers are automatically normalized to E.164 format (+1XXXXXXXXXX).

Usage:
    python scripts/test_message_history.py "+15551234567"
    python scripts/test_message_history.py 5551234567
    python scripts/test_message_history.py "(555) 123-4567"
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.twilio import get_all_messages_to_phone_number
from utils.phone_utils import normalize_phone_number

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_message_history.py <phone_number>")
        print("Example: python scripts/test_message_history.py +15551234567")
        print("         python scripts/test_message_history.py 5551234567")
        print("         python scripts/test_message_history.py '(555) 123-4567'")
        return 1

    phone_number = sys.argv[1]

    # Normalize phone number to E.164 format
    try:
        phone_number = normalize_phone_number(phone_number)
    except ValueError as e:
        print(f"\n❌ ERROR: Invalid phone number format: {e}")
        return 1

    print("=" * 80)
    print(f"MESSAGE HISTORY TEST")
    print("=" * 80)
    print(f"Target phone number (normalized): {phone_number}")
    print(f"Twilio number: {os.getenv('TWILIO_PHONE_NUMBER', 'Not set')}")
    print("=" * 80)

    # Check for required environment variables
    if not os.getenv('TWILIO_ACCOUNT_SID'):
        print("\n❌ ERROR: TWILIO_ACCOUNT_SID environment variable not set")
        return 1

    if not os.getenv('TWILIO_AUTH_TOKEN'):
        print("\n❌ ERROR: TWILIO_AUTH_TOKEN environment variable not set")
        return 1

    if not os.getenv('TWILIO_PHONE_NUMBER'):
        print("\n❌ ERROR: TWILIO_PHONE_NUMBER environment variable not set")
        return 1

    print("\n🔍 Fetching all messages sent to this number across all conversations...")
    print()

    try:
        messages = get_all_messages_to_phone_number(phone_number, limit=50)

        if not messages:
            print("📭 No messages found")
            print()
            print("This could mean:")
            print("  - We haven't sent any messages to this number")
            print("  - The number is not in any active conversations")
            return 0

        print(f"✅ Found {len(messages)} message(s)")
        print()
        print("-" * 80)

        for i, msg in enumerate(messages, 1):
            conversation_sid = msg.get('conversation_sid', 'Unknown')
            date_created = msg.get('date_created', 'Unknown date')
            body = msg.get('body', '')
            message_sid = msg.get('message_sid', 'Unknown')

            print(f"\nMessage {i}:")
            print(f"  Conversation: {conversation_sid}")
            print(f"  Date: {date_created}")
            print(f"  Message SID: {message_sid}")
            print(f"  Body:")
            print(f"    {body}")
            print("-" * 80)

        print(f"\n✅ Successfully retrieved {len(messages)} message(s)")
        return 0

    except Exception as e:
        print(f"\n❌ Error fetching messages: {e}")
        logger.error(f"Error details:", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
