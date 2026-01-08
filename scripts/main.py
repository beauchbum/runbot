#!/usr/bin/env python3
"""
Ping Agent Script for BeauchBot - Cron Job Entry Point

This script is designed to be run as a cron job (e.g., hourly).
It performs the following workflow for upcoming runs:
1. Identify and read the calendar document
2. Find runs happening within 3 hours
3. Extract BLs for each run
4. Match runs to Action Network events
5. Fetch attendees from Action Network
6. Check conversation history between BLs and attendees
7. Send group messages to attendees (with BLs included)

Environment Variables Required:
- OPENAI_API_KEY: OpenAI API key for the LLM
- GOOGLE_SERVICE_ACCOUNT_B64: Base64 encoded Google service account JSON
- PHONE_DIRECTORY_DOC_ID: Google Doc ID containing contact information
- ACTION_NETWORK_API_KEY: Action Network API key for event linking
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER: For messaging
- ATTENDANCE_SHEET_ID: Google Sheets ID for attendance tracking (optional, for nudges)
- ALLOWED_BLS: Comma-separated list of BL names to allow (optional, if not set all BLs are allowed)

Usage:
    python scripts/ping_agent.py                                    # Execute with current Eastern time
    python scripts/ping_agent.py --dry-run                          # Dry run (no actual messages sent)
    python scripts/ping_agent.py --simulate-time "2024-01-15,09:00" # Test with simulated time (9 AM EST)
    python scripts/ping_agent.py -t "2024-12-25"                    # Test Christmas day (midnight EST)
    python scripts/ping_agent.py --include-nudges                   # Include attendance-based nudge analysis
    python scripts/ping_agent.py -d -n                              # Dry run with nudge analysis enabled

Typical cron entry (runs every hour):
    0 * * * * cd /path/to/beauchbot && python scripts/ping_agent.py >> /var/log/beauchbot_cron.log 2>&1
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from openai import OpenAI

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.twilio import get_all_messages_to_phone_number, send_text
from utils.action_network_utils import (
    fetch_all_action_network_events,
    get_event_attendees,
    match_run_to_action_network_event,
)
from utils.attendance_utils import (
    format_nudge_message,
    identify_nudge_candidates,
    parse_attendance_sheet,
)
from utils.google_utils import (
    extract_text_from_document,
    get_google_docs_service,
    get_google_drive_service,
)
from utils.phone_utils import get_allowed_contacts, normalize_phone_number

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_simulated_time(simulated_time: str) -> datetime:
    """Parse the simulated time string and return a datetime object."""
    if "," in simulated_time:
        naive_time = datetime.strptime(simulated_time, '%Y-%m-%d,%H:%M')
    else:
        naive_time = datetime.strptime(simulated_time, '%Y-%m-%d')
    return naive_time.replace(tzinfo=ZoneInfo("America/New_York"))


def identify_calendar_doc(client: OpenAI, available_docs: List[Dict[str, Any]], current_time: datetime) -> Optional[str]:
    """Use LLM to identify which document is the calendar for the current month."""
    doc_list = "\n".join([
        f"- ID: {doc['id']}, Name: {doc['name']}, Modified: {doc.get('modified_time', 'Unknown')}"
        for doc in available_docs
    ])

    current_month = current_time.strftime('%B')
    current_year = current_time.strftime('%Y')

    prompt = f"""You are helping identify which Google Document is the calendar/schedule document for the current month.

Current date/time: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}
Current month: {current_month} {current_year}

Here are the available documents:
{doc_list}

Based on the document names, identify the calendar/schedule document for {current_month} {current_year}.
Look for documents with names like "{current_month} {current_year} Calendar", "{current_month} Calendar", etc.

If you cannot find an appropriate calendar document for {current_month} {current_year}, respond with exactly "NONE".
Otherwise, respond with ONLY the document ID, nothing else."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that identifies documents."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    doc_id = response.choices[0].message.content.strip()

    if doc_id == "NONE" or not doc_id:
        logger.warning(f"No calendar document found for {current_month} {current_year}")
        return None

    logger.info(f"Identified calendar document: {doc_id}")
    return doc_id


def parse_runs_from_calendar(client: OpenAI, calendar_text: str, current_time: datetime) -> List[Dict[str, Any]]:
    """Use LLM to parse all runs from calendar document, including BL assignments."""
    current_month = current_time.strftime('%B')
    current_year = current_time.year

    prompt = f"""You are parsing a monthly calendar document to extract ALL runs.

Current month/year: {current_month} {current_year}

Calendar document content:
{calendar_text}

CALENDAR FORMAT:
The calendar is a monthly table/grid with days of the week as column headers (Sunday through Saturday).
Each cell contains:
1. A day number (1-31) at the top
2. Zero or more run entries, each containing:
   - Run name and time (e.g., "Office Loop 7 PM" or "Prospect Park Loop 7 PM")
   - BL (Bottom-liner) section: "BL: (H) Name" for Head, "(T) Name" for Tail
   - Additional fields like "Chat blast:", "RSVP reach out:" (ignore these)
3. Multiple runs can occur on the same day

BL (BOTTOM-LINER) INFORMATION:
- BLs are listed as "BL: (H) Name" for Head and "(T) Name" for Tail
- Some runs have both Head and Tail BLs
- Some runs have only one BL (Head or Tail)
- Some runs have no BLs assigned yet (empty or missing)
- Sometimes formatted as "BL:(H) Name" (no space after colon)
- Extract ALL BL names regardless of role (H) or (T)

TASK:
Extract ALL runs from the entire calendar month.

For each run:
1. Find the day number in the cell
2. Parse the run name and time (e.g., "Office Loop 7 PM" → name: "Office Loop", time: 7 PM)
3. Convert time to 24-hour format:
   - Times with "AM" stay as-is (7 AM = 07:00)
   - Times with "PM" add 12 (7 PM = 19:00, 7:30 PM = 19:30)
4. Combine day + month + year + time to create ISO datetime with EST timezone (-05:00)
5. Extract ALL BL names (both Head and Tail) into an array
   - If "BL: (H) Gareth (T) Nic L" → ["Gareth", "Nic L"]
   - If "BL: (H) Tim (T)" → ["Tim"]
   - If "BL: Randy" → ["Randy"]
   - If no BLs or empty → []
6. Extract the complete text for that run (including BL section)

IMPORTANT:
- Extract ALL runs from the entire month, not just upcoming ones
- Pay attention to the day number in each cell
- Parse times correctly (7 PM = 19:00, 7:30 PM = 19:30)
- Use EST timezone offset: -05:00
- Extract ALL BL names regardless of (H) or (T) designation

Respond with ONLY a JSON array. Each run should have:
- "time": ISO format datetime (e.g., "{current_year}-12-15T19:00:00-05:00" for 7 PM on Dec 15)
- "name": Run name (e.g., "Office Loop")
- "bls": Array of BL names (e.g., ["Gareth", "Nic L"] or [] if none)
- "full_text": The complete text block for this run including BL section

If no runs found, respond with [].
Example: [{{"time": "{current_year}-12-02T19:00:00-05:00", "name": "Office Loop", "bls": ["Gareth", "Nic L"], "full_text": "Office Loop 7 PM\\nBL: (H) Gareth\\n(T) Nic L"}}]"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that parses calendar data. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    llm_response = response.choices[0].message.content.strip()

    if llm_response.startswith("```"):
        lines = llm_response.split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        llm_response = '\n'.join(lines).strip()

    try:
        runs = json.loads(llm_response)
        logger.info(f"Parsed {len(runs)} total runs from calendar")
        return runs
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse runs JSON: {e}")
        return []


def filter_runs_by_time_window(runs: List[Dict[str, Any]], current_time: datetime, hours: int = 3) -> List[Dict[str, Any]]:
    """Filter runs to only those occurring within the specified time window."""
    cutoff_time = current_time + timedelta(hours=hours)

    filtered_runs = []
    for run in runs:
        try:
            run_time_str = run.get('time', '')
            run_time = datetime.fromisoformat(run_time_str)

            if current_time <= run_time <= cutoff_time:
                filtered_runs.append(run)
                bl_count = len(run.get('bls', []))
                logger.info(f"Including run: {run.get('name')} at {run_time.strftime('%Y-%m-%d %I:%M %p')} ({bl_count} BLs)")
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping run with invalid time format: {run.get('name', 'Unknown')} - {e}")
            continue

    logger.info(f"Found {len(filtered_runs)} runs within {hours}-hour window")
    return filtered_runs


def get_allowed_bls() -> Optional[List[str]]:
    """Get list of allowed BLs from environment variable. Returns None if not set (allow all)."""
    allowed_bls_str = os.getenv('ALLOWED_BLS')
    if not allowed_bls_str:
        return None

    allowed_bls = [name.strip() for name in allowed_bls_str.split(',')]
    return allowed_bls


def validate_bls_against_contacts(client: OpenAI, bl_names: List[str], contacts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Validate BL names against the contact list using LLM for intelligent matching."""
    if not bl_names:
        return []

    contact_names = [contact['name'] for contact in contacts]
    contact_list = "\n".join([f"- {name}" for name in contact_names])
    bl_list = "\n".join([f"- {name}" for name in bl_names])

    prompt = f"""You are matching names from a calendar to a contact directory.

BL names from calendar (may have variations):
{bl_list}

Valid contact names from directory:
{contact_list}

For each BL name, find the best matching contact name. Account for:
- Case differences (John vs john)
- Last name vs initial (John Smith vs John S)
- Common nicknames (Mike vs Michael, Nic vs Nick)
- Missing or extra spaces

Respond with ONLY a JSON object mapping each BL name to its best match from the contact directory.
If no good match exists for a BL name, map it to null.

Example format:
{{
  "John S": "John Smith",
  "mike": "Mike Johnson",
  "Unknown Person": null
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that matches names intelligently. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        llm_response = response.choices[0].message.content.strip()

        if llm_response.startswith("```"):
            lines = llm_response.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            llm_response = '\n'.join(lines).strip()

        name_mappings = json.loads(llm_response)
        contact_by_name = {contact['name']: contact for contact in contacts}

        valid_bls = []
        invalid_bls = []

        for bl_name, matched_name in name_mappings.items():
            if matched_name and matched_name in contact_by_name:
                valid_bls.append(contact_by_name[matched_name])
                if bl_name != matched_name:
                    logger.info(f"Matched '{bl_name}' → '{matched_name}'")
            else:
                invalid_bls.append(bl_name)
                logger.warning(f"No match found for '{bl_name}'")

        if invalid_bls:
            logger.warning(f"Could not match {len(invalid_bls)} BL name(s): {', '.join(invalid_bls)}")

        allowed_bls = get_allowed_bls()
        if allowed_bls:
            allowed_bls_lower = [name.lower() for name in allowed_bls]
            filtered_bls = [bl for bl in valid_bls if bl['name'].lower() in allowed_bls_lower]

            if len(filtered_bls) < len(valid_bls):
                filtered_out = [bl['name'] for bl in valid_bls if bl['name'].lower() not in allowed_bls_lower]
                logger.info(f"Filtered out {len(filtered_out)} BL(s) not in allowed list: {', '.join(filtered_out)}")

            valid_bls = filtered_bls

        logger.info(f"Validated {len(valid_bls)} BLs")
        return valid_bls

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse LLM name matching response: {e}")
        logger.warning("Falling back to case-insensitive matching")

        valid_bls = []
        contact_by_name_lower = {contact['name'].lower(): contact for contact in contacts}

        for bl_name in bl_names:
            bl_name_lower = bl_name.lower()
            if bl_name_lower in contact_by_name_lower:
                valid_bls.append(contact_by_name_lower[bl_name_lower])
            else:
                logger.warning(f"No match found for '{bl_name}'")

        allowed_bls = get_allowed_bls()
        if allowed_bls:
            allowed_bls_lower = [name.lower() for name in allowed_bls]
            filtered_bls = [bl for bl in valid_bls if bl['name'].lower() in allowed_bls_lower]

            if len(filtered_bls) < len(valid_bls):
                filtered_out = [bl['name'] for bl in valid_bls if bl['name'].lower() not in allowed_bls_lower]
                logger.info(f"Filtered out {len(filtered_out)} BL(s) not in allowed list: {', '.join(filtered_out)}")

            valid_bls = filtered_bls

        return valid_bls


def format_attendee_message(attendee_name: str, bl_names: List[str], run_name: str, run_datetime: datetime) -> str:
    """Format a personalized message to an attendee."""
    first_name = attendee_name.split()[0] if attendee_name else "there"
    bl_first_names = [bl_name.split()[0] for bl_name in bl_names]

    if len(bl_first_names) == 1:
        bl_names_str = bl_first_names[0]
    elif len(bl_first_names) == 2:
        bl_names_str = f"{bl_first_names[0]} and {bl_first_names[1]}"
    else:
        bl_names_str = f"{', '.join(bl_first_names[:-1])}, and {bl_first_names[-1]}"

    run_time_str = run_datetime.strftime('%A, %B %d at %I:%M %p')

    message = (
        f"Hello {first_name}! I've put you in a conversation with {bl_names_str} "
        f"from DSA Running Club. It looks like you are signed up for {run_name} "
        f"on {run_time_str}. Are you still planning on attending? Also if you have "
        f"any questions feel free to put them here and we'll help you out!"
    )

    return message


# Note: normalize_phone_number is now imported from utils.phone_utils
# This ensures consistent E.164 format (+1XXXXXXXXXX) throughout the application


def check_if_already_messaged_about_run(
    client: OpenAI,
    all_messages: List[Dict[str, Any]],
    run_name: str,
    run_datetime: datetime
) -> bool:
    """Use LLM to determine if we've already messaged about this specific run."""
    if not all_messages:
        return False

    conversation_text = []
    for msg in all_messages[:15]:
        date = msg.get('date_created', 'Unknown date')
        body = msg.get('body', '')
        conversation_text.append(f"[{date}] {body}")

    conversation_str = "\n".join(conversation_text)
    run_time_str = run_datetime.strftime('%A, %B %d at %I:%M %p')

    prompt = f"""You are analyzing message history to determine if we've already sent a message about a specific run event.

IMPORTANT: These messages are from MULTIPLE conversations (we may have changed group chats).

TARGET RUN:
- Name: {run_name}
- Date/Time: {run_time_str}

ALL MESSAGES WE'VE SENT TO THIS PERSON (most recent, across all conversations):
{conversation_str}

Question: Have we already sent a message to this person about the "{run_name}" run on {run_time_str}?

Consider:
- These messages span multiple conversations/group chats
- We may have messaged about OTHER runs - that's fine, we only care about THIS specific run
- Look for messages that mention this run name and this specific date/time
- If there's a message confirming attendance, asking about attendance, or introducing this specific run, answer YES
- If there are only messages about different runs or dates, answer NO
- If there are no messages or they're unrelated, answer NO

Respond with ONLY one word: YES or NO"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes conversation history. Always respond with only YES or NO."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        llm_response = response.choices[0].message.content.strip().upper()
        return llm_response == "YES"

    except Exception as e:
        logger.warning(f"Error checking if already messaged: {e}")
        return True


def fetch_attendee_message_history(attendee_phone: str, attendee_name: str) -> List[Dict[str, Any]]:
    """
    Fetch message history for a specific attendee across all conversations.

    Args:
        attendee_phone: Phone number of the attendee (will be normalized)
        attendee_name: Name of the attendee (for logging)

    Returns:
        List of message dictionaries, or empty list on error
    """
    try:
        all_messages = get_all_messages_to_phone_number(phone_number=attendee_phone, limit=20)
        return all_messages
    except Exception as e:
        logger.warning(f"Error fetching messages for {attendee_name}: {e}")
        return []


def check_bl_message_history(client: OpenAI, valid_bl_contacts: List[Dict[str, str]], run_name: str, run_time: datetime) -> bool:
    """Check if we've already messaged BLs about this run. Returns True if already messaged."""
    for bl_contact in valid_bl_contacts:
        bl_name = bl_contact['name']
        bl_phone = bl_contact['phone_number']

        try:
            all_messages = get_all_messages_to_phone_number(phone_number=bl_phone, limit=20)

            if all_messages:
                already_messaged = check_if_already_messaged_about_run(
                    client=client,
                    all_messages=all_messages,
                    run_name=run_name,
                    run_datetime=run_time
                )

                if already_messaged:
                    logger.info(f"Already messaged {bl_name} about this run")
                    return True
        except Exception as e:
            logger.warning(f"Error fetching messages for {bl_name}: {e}")

    return False


def filter_nudge_candidates_by_rsvp(
    nudge_candidates: List[Dict[str, Any]],
    attendees: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Filter out nudge candidates who are already RSVP'd, using first name matching."""
    if not attendees:
        return nudge_candidates

    rsvp_first_names_lower = set()
    for attendee in attendees:
        attendee_name = attendee.get('full_name', '')
        if attendee_name:
            first_name = attendee_name.split()[0].lower()
            rsvp_first_names_lower.add(first_name)

    nudge_candidates_filtered = []
    for candidate in nudge_candidates:
        candidate_first_name = candidate['name'].split()[0].lower()
        if candidate_first_name not in rsvp_first_names_lower:
            nudge_candidates_filtered.append(candidate)

    return nudge_candidates_filtered


def send_nudge_message_to_bls(
    bl_names: List[str],
    bl_phone_numbers: List[str],
    run_name: str,
    nudge_candidates: List[Dict[str, Any]],
    dry_run: bool
) -> None:
    """Send nudge suggestions to BLs."""
    nudge_message = format_nudge_message(bl_names, run_name, nudge_candidates)

    try:
        if dry_run:
            logger.info(f"DRY RUN: Would send nudge message to BLs")
            logger.info(f"Recipients: {', '.join(bl_names)}")
            logger.info(f"Message:\n{nudge_message}")
        else:
            result = send_text(bl_phone_numbers, nudge_message)

            if "error" in result:
                logger.error(f"Failed to send nudge message to BLs: {result['error']}")
            else:
                logger.info(f"Sent nudge message to BLs")

    except Exception as e:
        logger.error(f"Error sending nudge message to BLs: {e}")


def send_messages_to_attendees(
    client: OpenAI,
    attendees: List[Dict[str, Any]],
    valid_bl_contacts: List[Dict[str, str]],
    bl_names: List[str],
    run_name: str,
    run_time: datetime,
    dry_run: bool
) -> None:
    """
    Send group messages to attendees with BLs included.

    Fetches message history on-demand for each attendee to check if they've
    already been messaged about this specific run.
    """
    bl_phone_numbers = [contact['phone_number'] for contact in valid_bl_contacts]
    # Normalize all BL phone numbers for comparison
    bl_phone_numbers_normalized = []
    for phone in bl_phone_numbers:
        try:
            bl_phone_numbers_normalized.append(normalize_phone_number(phone))
        except ValueError as e:
            logger.warning(f"Could not normalize BL phone number '{phone}': {e}")

    messages_sent = 0
    messages_failed = 0

    for attendee in attendees:
        attendee_name = attendee.get('full_name', 'Unknown')
        attendee_phone = attendee.get('primary_phone')

        if not attendee_phone:
            continue

        # Normalize attendee phone for comparison
        try:
            attendee_phone_normalized = normalize_phone_number(attendee_phone)
        except ValueError as e:
            logger.warning(f"Could not normalize attendee phone number '{attendee_phone}': {e}")
            continue

        # Skip if attendee is one of the BLs
        if attendee_phone_normalized in bl_phone_numbers_normalized:
            logger.debug(f"Skipping {attendee_name} (is a BL)")
            continue

        # Fetch message history on-demand for this specific attendee
        logger.debug(f"Fetching message history for {attendee_name}...")
        all_messages = fetch_attendee_message_history(attendee_phone_normalized, attendee_name)

        # Check if we've already messaged this attendee about this run
        already_messaged = check_if_already_messaged_about_run(
            client=client,
            all_messages=all_messages,
            run_name=run_name,
            run_datetime=run_time
        )

        if already_messaged:
            logger.info(f"Already messaged {attendee_name} about this run - skipping")
            continue

        # Create group message with BLs and this attendee
        group_participants = bl_phone_numbers_normalized + [attendee_phone_normalized]
        message = format_attendee_message(attendee_name, bl_names, run_name, run_time)

        try:
            if dry_run:
                logger.info(f"DRY RUN: Would send to {attendee_name}")
                messages_sent += 1
            else:
                logger.info(f"Creating group text with numbers: {', '.join(group_participants)}")
                result = send_text(group_participants, message)

                if "error" in result:
                    logger.error(f"Failed to send to {attendee_name}: {result['error']}")
                    messages_failed += 1
                else:
                    logger.info(f"Sent to {attendee_name}")
                    messages_sent += 1

        except Exception as e:
            logger.error(f"Error sending to {attendee_name}: {e}")
            messages_failed += 1

    logger.info(f"Messaging complete: {messages_sent} sent, {messages_failed} failed")


def process_run(
    run: Dict[str, Any],
    client: OpenAI,
    contacts: List[Dict[str, str]],
    action_network_events: List[Dict[str, Any]],
    attendance_data: List[Dict[str, Any]],
    current_time: datetime,
    include_nudges: bool,
    dry_run: bool
) -> None:
    """Process a single run: match to Action Network, fetch attendees, send messages."""
    run_name = run.get('name', 'Unknown')
    run_time_str = run.get('time', '')

    logger.info(f"\nProcessing run: {run_name}")

    if run_time_str and action_network_events:
        try:
            run_datetime = datetime.fromisoformat(run_time_str)

            matched_event = match_run_to_action_network_event(
                run_name=run_name,
                run_datetime=run_datetime,
                action_network_events=action_network_events,
                openai_client=client,
                time_window_hours=12
            )

            if matched_event:
                logger.info(f"Linked to Action Network event: {matched_event.get('title', 'Unknown')}")
                logger.info(f"Attendance: {matched_event.get('total_accepted', 0)} confirmed")

                run['action_network_event'] = matched_event

                try:
                    event_id = matched_event.get('id').split(':')[-1]
                    attendees = get_event_attendees(event_id, max_attendances=100)
                    run['action_network_attendees'] = attendees
                    logger.info(f"Found {len(attendees)} attendees")
                except Exception as e:
                    logger.warning(f"Error fetching attendees: {e}")
            else:
                logger.info(f"No matching Action Network event found")
        except Exception as e:
            logger.warning(f"Error matching to Action Network: {e}")

    bl_names = run.get('bls', [])
    attendees = run.get('action_network_attendees', [])

    if not bl_names:
        logger.warning(f"No BLs assigned for run '{run_name}'")
        return

    logger.info(f"Found {len(bl_names)} BLs: {', '.join(bl_names)}")

    valid_bl_contacts = validate_bls_against_contacts(client, bl_names, contacts)

    if not valid_bl_contacts:
        logger.warning(f"No valid BL contacts for run '{run_name}'")
        return

    skip_bl_message = False
    run_time = datetime.fromisoformat(run.get('time', ''))

    if include_nudges and valid_bl_contacts:
        logger.info(f"Checking BL message history...")
        skip_bl_message = check_bl_message_history(client, valid_bl_contacts, run_name, run_time)

    nudge_candidates = []

    if include_nudges and attendance_data and not skip_bl_message:
        day_of_week = run_time.strftime('%A')

        logger.info(f"Analyzing attendance for nudge candidates...")
        all_nudge_candidates = identify_nudge_candidates(
            target_run_name=run_name,
            target_day_of_week=day_of_week,
            current_time=current_time,
            all_runs=attendance_data
        )

        bl_names_lower = [name.lower() for name in bl_names]
        nudge_candidates = [
            candidate for candidate in all_nudge_candidates
            if candidate['name'].lower() not in bl_names_lower
        ]

        nudge_candidates = filter_nudge_candidates_by_rsvp(nudge_candidates, attendees)

        logger.info(f"Identified {len(nudge_candidates)} nudge candidates")

    if include_nudges and valid_bl_contacts and not skip_bl_message:
        logger.info(f"Sending nudge suggestions to BLs...")
        bl_phone_numbers = [contact['phone_number'] for contact in valid_bl_contacts]
        send_nudge_message_to_bls(bl_names, bl_phone_numbers, run_name, nudge_candidates, dry_run)

    if attendees and valid_bl_contacts:
        logger.info(f"Sending messages to attendees...")
        send_messages_to_attendees(
            client, attendees, valid_bl_contacts, bl_names, run_name, run_time, dry_run
        )


def run_cron_execution(simulated_time: Optional[str] = None, dry_run: bool = False, include_nudges: bool = False) -> int:
    """Execute the cron job workflow."""
    start_time = datetime.now()
    logger.info(f"Starting BeauchBot cron execution at {start_time}")

    try:
        required_vars = ["OPENAI_API_KEY", "GOOGLE_SERVICE_ACCOUNT_B64", "PHONE_DIRECTORY_DOC_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return 1

        eastern_tz = ZoneInfo("America/New_York")

        if simulated_time:
            try:
                current_time = parse_simulated_time(simulated_time)
                logger.info(f"Using simulated time: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
            except ValueError:
                logger.error(f"Invalid simulated time format: {simulated_time}")
                return 1
        else:
            current_time = datetime.now(eastern_tz)
            logger.info(f"Current time: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        drive_service = get_google_drive_service()
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=20,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()

        available_docs = results.get('files', [])
        if not available_docs:
            logger.error("No Google Docs found")
            return 1

        calendar_doc_id = identify_calendar_doc(client, available_docs, current_time)
        if not calendar_doc_id:
            current_month = current_time.strftime('%B')
            current_year = current_time.strftime('%Y')
            logger.error(f"Could not find calendar document for {current_month} {current_year}")
            return 1

        docs_service = get_google_docs_service()
        document = docs_service.documents().get(documentId=calendar_doc_id).execute()
        calendar_text = extract_text_from_document(document)

        all_runs = parse_runs_from_calendar(client, calendar_text, current_time)

        if not all_runs:
            logger.warning("No runs found in calendar")
            return 0

        applicable_hours = 10
        runs = filter_runs_by_time_window(all_runs, current_time, hours=applicable_hours)

        if not runs:
            logger.info(f"No runs found within {applicable_hours} hours")
            return 0

        action_network_events = []
        try:
            action_network_events = fetch_all_action_network_events(max_pages=3)
            logger.info(f"Loaded {len(action_network_events)} Action Network events")
        except Exception as e:
            logger.error(f"Failed to fetch Action Network events: {e}")
            logger.warning("Continuing without Action Network integration")

        attendance_data = []
        if include_nudges:
            try:
                attendance_data = parse_attendance_sheet()
                logger.info(f"Loaded attendance data for {len(attendance_data)} runs")
            except Exception as e:
                logger.error(f"Failed to load attendance data: {e}")
                logger.warning("Continuing without nudge suggestions")

        contacts = get_allowed_contacts()
        if not contacts:
            logger.error("Could not load contacts from phone directory")
            return 1

        logger.info(f"Loaded {len(contacts)} contacts from phone directory")

        for i, run in enumerate(runs, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Run {i}/{len(runs)}")
            process_run(run, client, contacts, action_network_events, attendance_data, current_time, include_nudges, dry_run)

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Cron execution completed successfully")
        logger.info(f"Duration: {duration}")

        return 0

    except Exception as e:
        logger.error(f"Cron execution failed: {e}", exc_info=True)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BeauchBot cron job entry point")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Dry run (don't send texts)")
    parser.add_argument("--simulate-time", "-t", help="Simulate time (format: 'YYYY-MM-DD,HH:MM' or 'YYYY-MM-DD')")
    parser.add_argument("--include-nudges", "-n", action="store_true", help="Include nudge suggestions (default: disabled)")

    args = parser.parse_args()

    eastern_tz = ZoneInfo("America/New_York")
    now = parse_simulated_time(args.simulate_time) if args.simulate_time else datetime.now(eastern_tz)

    if now.hour < 8 or now.hour >= 20:
        logger.info(f"Outside operating hours (8 AM - 8 PM). Current hour: {now.hour}")
        return 0

    exit_code = run_cron_execution(
        simulated_time=args.simulate_time,
        dry_run=args.dry_run,
        include_nudges=args.include_nudges
    )

    if exit_code == 0:
        logger.info("Cron job completed successfully")
    else:
        logger.error("Cron job failed")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
