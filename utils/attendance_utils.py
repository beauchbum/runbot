"""
Attendance utilities for BeauchBot.

Provides functionality to:
- Parse attendance data from Google Sheets
- Find similar runs based on location and day of week
- Identify people who should be nudged
"""

import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def parse_attendance_sheet() -> List[Dict[str, Any]]:
    """
    Parse the attendance Google Sheet into structured run data.

    The sheet format is:
    - Row 1: Dates (column headers)
    - Row 2: Run names
    - Row 3+: Attendee names (one per cell, vertically stacked)

    Returns:
        List of run dictionaries with:
        - date: datetime object
        - run_name: str
        - attendees: List[str] (names)
        - day_of_week: str (e.g., "Monday")
    """
    from utils.google_utils import get_google_sheets_service

    sheet_id = os.getenv('ATTENDANCE_SHEET_ID')
    if not sheet_id:
        raise ValueError("ATTENDANCE_SHEET_ID environment variable is required")

    logger.info("📊 Fetching attendance sheet data...")

    sheets_service = get_google_sheets_service()

    # Fetch data from the Attendance sheet
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Attendance!A1:ZZ1000"  # Fetch all data
    ).execute()

    values = result.get('values', [])

    if not values or len(values) < 3:
        logger.warning("⚠️  Attendance sheet has insufficient data")
        return []

    # Parse the data
    runs = []
    date_row = values[0]  # Row 1: Dates
    run_name_row = values[1]  # Row 2: Run names
    attendee_rows = values[2:]  # Row 3+: Attendees

    eastern_tz = ZoneInfo("America/New_York")

    # Process each column (starting from index 1, skipping the "Date:" label column)
    for col_idx in range(1, len(date_row)):
        date_str = date_row[col_idx].strip() if col_idx < len(date_row) else ""
        run_name = run_name_row[col_idx].strip() if col_idx < len(run_name_row) else ""

        # Skip empty columns
        if not date_str or not run_name:
            continue

        # Parse the date
        try:
            # Try different date formats
            for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    date_obj = date_obj.replace(tzinfo=eastern_tz)
                    break
                except ValueError:
                    continue
            else:
                logger.warning(f"⚠️  Could not parse date: {date_str}")
                continue
        except Exception as e:
            logger.warning(f"⚠️  Error parsing date '{date_str}': {e}")
            continue

        # Extract attendees from this column
        attendees = []
        for row in attendee_rows:
            if col_idx < len(row):
                cell_value = row[col_idx].strip()
                # Filter out empty cells and cells with just "NEW" or notes
                if cell_value and cell_value not in ['NEW', '']:
                    # Remove "NEW" tags and notes (text in parentheses)
                    name = cell_value.split('\n')[0].strip()  # Take first line only
                    if name and name != 'NEW':
                        attendees.append(name)

        # Create run entry
        run_entry = {
            'date': date_obj,
            'run_name': run_name,
            'attendees': attendees,
            'day_of_week': date_obj.strftime('%A')  # Monday, Tuesday, etc.
        }

        runs.append(run_entry)

    logger.info(f"✅ Parsed {len(runs)} runs from attendance sheet")

    # Log sample of parsed data for debugging
    if runs:
        logger.info(f"📊 Sample of parsed runs:")
        for run in runs[:3]:  # Show first 3 runs
            logger.info(f"   - {run['date'].strftime('%Y-%m-%d')} ({run['day_of_week']}): {run['run_name']}")
            logger.info(f"     Attendees: {', '.join(run['attendees'][:5])}{'...' if len(run['attendees']) > 5 else ''}")

        # Log day-of-week breakdown
        from collections import Counter
        day_counts = Counter(run['day_of_week'] for run in runs)
        logger.info(f"📊 Runs by day of week:")
        for day, count in sorted(day_counts.items()):
            logger.info(f"   {day}: {count} runs")

    return runs


def fuzzy_match_location(run_name1: str, run_name2: str) -> float:
    """
    Calculate fuzzy match score between two run names based on location.

    Args:
        run_name1: First run name
        run_name2: Second run name

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize run names (lowercase, remove common words)
    def normalize(name: str) -> str:
        name = name.lower()
        # Remove common words that don't indicate location
        for word in ['run', 'loop', 'evening', 'morning', 'the']:
            name = name.replace(word, '')
        return name.strip()

    norm1 = normalize(run_name1)
    norm2 = normalize(run_name2)

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_similar_runs(target_run_name: str, target_day_of_week: str,
                      all_runs: List[Dict[str, Any]],
                      location_threshold: float = 0.6) -> List[Dict[str, Any]]:
    """
    Find runs similar to the target run based on day of week and location.

    Strategy:
    1. First match by day of week (required)
    2. If only one unique run name on that day, return all runs with that day
    3. If multiple unique run names on that day, apply fuzzy location matching

    Args:
        target_run_name: Name of the target run
        target_day_of_week: Day of week (e.g., "Monday")
        all_runs: List of all runs from attendance sheet
        location_threshold: Minimum fuzzy match score for location (0.0-1.0)

    Returns:
        List of similar run dictionaries
    """
    logger.info(f"🔍 Looking for runs similar to '{target_run_name}' on {target_day_of_week}s")
    logger.info(f"   Total runs to check: {len(all_runs)}")

    # First, filter by day of week
    same_day_runs = [run for run in all_runs if run['day_of_week'] == target_day_of_week]
    logger.info(f"   Found {len(same_day_runs)} runs on {target_day_of_week}s")

    if not same_day_runs:
        logger.info(f"✅ Found 0 similar runs (no runs on {target_day_of_week}s)")
        return []

    # Log runs on this day
    logger.info(f"   Runs on {target_day_of_week}s:")
    for run in same_day_runs:
        logger.info(f"     - {run['run_name']} ({run['date'].strftime('%Y-%m-%d')})")

    # Group runs by date to check if there are multiple runs on the same specific day
    from collections import defaultdict
    runs_by_date = defaultdict(list)
    for run in same_day_runs:
        runs_by_date[run['date'].date()].append(run)

    # Check if any date has multiple runs
    dates_with_multiple_runs = [date for date, runs in runs_by_date.items() if len(runs) > 1]

    if not dates_with_multiple_runs:
        # No dates with multiple runs - just use all runs on this day of week
        logger.info(f"   ✅ No dates with multiple runs, using all {len(same_day_runs)} runs on {target_day_of_week}s")
        return same_day_runs

    # There are some dates with multiple runs - apply fuzzy matching to disambiguate
    logger.info(f"   Found {len(dates_with_multiple_runs)} date(s) with multiple runs")
    logger.info(f"   Applying fuzzy matching (threshold: {location_threshold})")

    similar_runs = []
    for run in same_day_runs:
        # If this run's date has only one run, include it automatically
        if len(runs_by_date[run['date'].date()]) == 1:
            similar_runs.append(run)
            logger.info(f"   ✅ Auto-including '{run['run_name']}' ({run['date'].strftime('%Y-%m-%d')}) - only run on that date")
            continue

        # Multiple runs on this date - use fuzzy matching
        similarity = fuzzy_match_location(target_run_name, run['run_name'])
        logger.info(f"   Comparing '{target_run_name}' vs '{run['run_name']}' ({run['date'].strftime('%Y-%m-%d')}): similarity={similarity:.2f}")

        if similarity >= location_threshold:
            similar_runs.append(run)
            logger.info(f"     ✅ Match! (>= {location_threshold})")
        else:
            logger.info(f"     ❌ No match (< {location_threshold})")

    logger.info(f"✅ Found {len(similar_runs)} similar runs to '{target_run_name}' on {target_day_of_week}s")
    return similar_runs


def get_person_attendance_history(person_name: str,
                                   similar_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get attendance history for a specific person across similar runs.

    Args:
        person_name: Name of the person
        similar_runs: List of similar runs to check

    Returns:
        List of runs this person attended, sorted by date (most recent first)
    """
    attendance = []

    # Normalize the person name for matching (case-insensitive, handle nicknames)
    person_name_lower = person_name.lower()

    for run in similar_runs:
        # Check if person attended this run (case-insensitive matching)
        for attendee in run['attendees']:
            if attendee.lower() == person_name_lower or person_name_lower in attendee.lower():
                attendance.append({
                    'date': run['date'],
                    'run_name': run['run_name']
                })
                break

    # Sort by date, most recent first
    attendance.sort(key=lambda x: x['date'], reverse=True)
    return attendance


def identify_nudge_candidates(target_run_name: str,
                               target_day_of_week: str,
                               current_time: datetime,
                               all_runs: List[Dict[str, Any]],
                               max_candidates: int = 10) -> List[Dict[str, Any]]:
    """
    Identify people who should be nudged for the upcoming run.

    Strategy:
    - Include anyone who has attended similar runs in the past
    - Prioritize people who attended 1-3 times (not regulars)
    - Sort by recency (most recent first)
    - Limit to top candidates

    Args:
        target_run_name: Name of the upcoming run
        target_day_of_week: Day of week for the upcoming run
        current_time: Current datetime
        all_runs: List of all runs from attendance sheet
        max_candidates: Maximum number of candidates to return (default: 10)

    Returns:
        List of nudge candidate dictionaries with:
        - name: Person's name
        - reason: Why they should be nudged
        - last_attendance: Date of last attendance
        - attendance_count: Total times attended similar runs
        - days_since_last: Days since last attendance
    """
    logger.info(f"🔍 Identifying nudge candidates for '{target_run_name}' on {target_day_of_week}...")

    # Find similar runs
    similar_runs = find_similar_runs(target_run_name, target_day_of_week, all_runs)

    if not similar_runs:
        logger.warning("⚠️  No similar runs found in attendance history")
        return []

    # Collect all unique attendees from similar runs
    all_attendees = set()
    for run in similar_runs:
        all_attendees.update(run['attendees'])

    logger.info(f"📊 Found {len(all_attendees)} unique attendees across similar runs")

    today = current_time.date()

    nudge_candidates = []

    for person in all_attendees:
        # Get their attendance history for similar runs
        history = get_person_attendance_history(person, similar_runs)

        if not history:
            continue

        # Get dates only
        attendance_dates = [h['date'].date() for h in history]
        total_attendance = len(attendance_dates)
        last_attendance = attendance_dates[0] if attendance_dates else None

        if not last_attendance:
            continue

        # Calculate days since last attendance
        days_since_last = (today - last_attendance).days

        logger.info(f"   Analyzing {person}:")
        logger.info(f"     Total attendance: {total_attendance}")
        logger.info(f"     Last attended: {last_attendance.strftime('%Y-%m-%d')} ({days_since_last} days ago)")

        # Determine reason for nudge based on attendance pattern
        if total_attendance == 1:
            if days_since_last <= 14:
                reason = "First run was recently - follow up!"
            else:
                reason = f"Came once {days_since_last} days ago"
        elif total_attendance == 2:
            reason = f"Attended 2x, last {days_since_last} days ago"
        elif total_attendance == 3:
            reason = f"Attended 3x, last {days_since_last} days ago"
        elif days_since_last >= 30:
            reason = f"Regular who hasn't come in {days_since_last} days"
        else:
            reason = f"Attended {total_attendance}x, last {days_since_last} days ago"

        logger.info(f"     ✅ NUDGE: {reason}")

        nudge_candidates.append({
            'name': person,
            'reason': reason,
            'last_attendance': last_attendance,
            'attendance_count': total_attendance,
            'days_since_last': days_since_last
        })

    # Sort by priority:
    # 1. People who attended 1-3 times (higher priority)
    # 2. More recent attendance (lower days_since_last)
    def priority_score(candidate):
        attendance = candidate['attendance_count']
        days = candidate['days_since_last']

        # Priority tier based on attendance count
        if attendance <= 3:
            tier = 0  # Highest priority - new/occasional attendees
        elif attendance <= 6:
            tier = 1  # Medium priority - semi-regular
        else:
            tier = 2  # Lower priority - regulars

        # Within each tier, sort by recency (lower is better)
        return (tier, days)

    nudge_candidates.sort(key=priority_score)

    # Limit to max_candidates
    nudge_candidates = nudge_candidates[:max_candidates]

    logger.info(f"✅ Identified {len(nudge_candidates)} nudge candidates (prioritized by attendance pattern and recency)")
    return nudge_candidates


def format_nudge_message(bl_names: List[str], run_name: str,
                         nudge_candidates: List[Dict[str, Any]]) -> str:
    """
    Format the nudge message to send to BLs.

    Args:
        bl_names: List of BL names
        run_name: Name of the run
        nudge_candidates: List of nudge candidate dictionaries

    Returns:
        Formatted message string
    """
    # Create greeting with BL names
    if len(bl_names) == 1:
        greeting = f"Hi {bl_names[0]}!"
    elif len(bl_names) == 2:
        greeting = f"Hi {bl_names[0]} and {bl_names[1]}!"
    else:
        greeting = f"Hi {', '.join(bl_names[:-1])}, and {bl_names[-1]}!"

    # Build message
    message = f"{greeting} You are assigned to BL {run_name}.\n\n"

    if not nudge_candidates:
        message += "No specific nudge suggestions at this time. Great job spreading the word!"
    else:
        message += "Here are a few people you may want to nudge for today:\n\n"

        for candidate in nudge_candidates:
            name = candidate['name']
            reason = candidate['reason']
            last_date = candidate['last_attendance']

            # Format last attendance date
            last_date_str = last_date.strftime('%b %d, %Y') if last_date else 'Unknown'

            message += f"• {name} - {reason}\n"
            message += f"  Last attended: {last_date_str}\n\n"

    return message.strip()
