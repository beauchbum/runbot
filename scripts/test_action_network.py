#!/usr/bin/env python3
"""
Test script for Action Network API integration.

This script helps debug and verify the Action Network integration by:
1. Fetching events from Action Network
2. Displaying event details
3. Testing event matching logic

Usage:
    python scripts/test_action_network.py                    # List all events
    python scripts/test_action_network.py --match            # Test matching a sample run
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.action_network_utils import (
    fetch_all_action_network_events,
    extract_event_details,
    match_run_to_action_network_event
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_events():
    """List all Action Network events with details."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    logger.info("🔍 Fetching Action Network events...")

    try:
        events = fetch_all_action_network_events(max_pages=3)

        if not events:
            logger.warning("No events found")
            return

        logger.info(f"\n📋 Found {len(events)} total events:\n")

        eastern_tz = ZoneInfo("America/New_York")

        for i, event in enumerate(events, 1):
            details = extract_event_details(event)

            print(f"{i}. {details['title'] or details['name']}")
            print(f"   ID: {details['id']}")

            # Parse and display the start date in Eastern time
            start_date_str = details['start_date']
            if start_date_str:
                try:
                    # Parse the datetime
                    if 'T' in start_date_str:
                        start_date_clean = start_date_str.replace('Z', '')
                        if '+' in start_date_clean or start_date_clean.endswith(('-00:00', '-05:00', '-04:00')):
                            event_start = datetime.fromisoformat(start_date_clean)
                        else:
                            event_start = datetime.fromisoformat(start_date_clean)
                            event_start = event_start.replace(tzinfo=eastern_tz)

                        event_start = event_start.astimezone(eastern_tz)
                        print(f"   Start (original): {start_date_str}")
                        print(f"   Start (EST): {event_start.strftime('%Y-%m-%d %I:%M %p %Z')}")
                    else:
                        print(f"   Start: {start_date_str}")
                except Exception as e:
                    print(f"   Start: {start_date_str} (parse error: {e})")
            else:
                print(f"   Start: Not set")

            location = details['location']
            if location:
                venue = location.get('venue')
                locality = location.get('locality')
                if venue or locality:
                    print(f"   Location: {venue or ''} {locality or ''}".strip())

            print(f"   Status: {details['status']}")
            print(f"   Attendance: {details['total_accepted']} confirmed")
            print()

    except Exception as e:
        logger.error(f"❌ Error fetching events: {e}", exc_info=True)


def test_matching():
    """Test matching a sample run to Action Network events."""
    from openai import OpenAI

    logger.info("🧪 Testing run matching...")

    # Initialize OpenAI client (required)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logger.error("❌ OPENAI_API_KEY environment variable is required for LLM matching")
        return 1

    openai_client = OpenAI(api_key=openai_api_key)

    # Fetch events
    events = fetch_all_action_network_events(max_pages=3)

    if not events:
        logger.error("No events available to test matching")
        return

    # Test with a sample run (you can modify these values)
    eastern_tz = ZoneInfo("America/New_York")
    sample_run_name = "Office Loop"
    sample_run_datetime = datetime.now(eastern_tz).replace(hour=19, minute=0, second=0, microsecond=0)

    logger.info(f"\n🔍 Testing match for:")
    logger.info(f"   Run: {sample_run_name}")
    logger.info(f"   Time: {sample_run_datetime.strftime('%Y-%m-%d %H:%M %Z')}")
    print()

    matched_event = match_run_to_action_network_event(
        run_name=sample_run_name,
        run_datetime=sample_run_datetime,
        action_network_events=events,
        openai_client=openai_client,
        time_window_hours=12
    )

    if matched_event:
        print(f"\n✅ Match found!")
        print(f"   Title: {matched_event['title']}")
        print(f"   Event ID: {matched_event['id']}")
        print(f"   Time difference: {matched_event.get('match_time_diff_hours', 0):.1f} hours")

        # Fetch attendees
        event_id = matched_event.get('id')
        if event_id:
            print(f"\n👥 Fetching attendees...")
            from utils.action_network_utils import get_event_attendees

            try:
                attendees = get_event_attendees(event_id, max_attendances=50)
                print(f"\n✅ Found {len(attendees)} attendees")

                if attendees:
                    print(f"\n   Sample attendees:")
                    for i, attendee in enumerate(attendees[:5], 1):
                        name = attendee.get('full_name', 'Unknown')
                        email = attendee.get('primary_email', 'N/A')
                        print(f"      {i}. {name} ({email})")

                    if len(attendees) > 5:
                        print(f"      ... and {len(attendees) - 5} more")

            except Exception as e:
                print(f"\n❌ Error fetching attendees: {e}")
    else:
        print(f"\n❌ No match found")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Action Network API integration",
    )
    parser.add_argument(
        "--match",
        action="store_true",
        help="Test matching a sample run to events"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv('ACTION_NETWORK_API_KEY'):
        logger.error("❌ ACTION_NETWORK_API_KEY environment variable is required")
        return 1

    if args.match:
        test_matching()
    else:
        list_events()

    return 0


if __name__ == "__main__":
    sys.exit(main())
