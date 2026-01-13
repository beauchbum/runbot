"""
Attendance utilities for BeauchBot.

Provides functionality to:
- Parse attendance data from Google Sheets
- Find similar runs based on location and day of week
- Identify people who should be nudged
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from openai import OpenAI

from utils.config_utils import require_variable

logger = logging.getLogger(__name__)


def parse_attendance_sheet() -> List[Dict[str, Any]]:
    """
    Parse the attendance Google Sheet into structured run data.

    Google Form format (as of Jan 2026):
    - Row 1: Headers (Timestamp, Email Address, When did the run happen?, Which run was it?, How many people attended?, Who attended?, ...)
    - Row 2+: Form responses with run data
    - Col 3: Date (e.g., "1/8/2026")
    - Col 4: Run name (e.g., "Thursday South Brooklyn")
    - Col 6: Attendees (comma-separated, e.g., "Ryan B, Avonlea F, Julian G")

    Returns:
        List of run dictionaries with:
        - date: datetime object
        - run_name: str
        - attendees: List[str] (names)
        - day_of_week: str (e.g., "Monday")
    """
    from utils.google_utils import get_google_sheets_service

    sheet_id = require_variable('attendance_sheet_id')

    logger.info("📊 Fetching attendance sheet data...")

    sheets_service = get_google_sheets_service()

    # Fetch data from Form Responses sheet
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Form Responses 1!A1:Z1000"  # Fetch all data
    ).execute()

    values = result.get('values', [])

    if not values or len(values) < 2:
        logger.warning("⚠️  Attendance sheet has insufficient data")
        return []

    # Skip header row
    header_row = values[0]
    data_rows = values[1:]

    eastern_tz = ZoneInfo("America/New_York")

    runs = []

    # Expected column indices (0-based)
    DATE_COL = 2  # Col 3: "When did the run happen?"
    RUN_NAME_COL = 3  # Col 4: "Which run was it?"
    ATTENDEES_COL = 5  # Col 6: "Who attended?"

    logger.info(f"Processing {len(data_rows)} form responses...")

    for row_idx, row in enumerate(data_rows, start=2):  # Start=2 because row 1 is header
        # Skip empty rows
        if len(row) <= ATTENDEES_COL:
            continue

        # Extract date
        date_str = row[DATE_COL].strip() if DATE_COL < len(row) else ""
        if not date_str:
            logger.warning(f"⚠️  Row {row_idx}: Missing date, skipping")
            continue

        # Extract run name
        run_name = row[RUN_NAME_COL].strip() if RUN_NAME_COL < len(row) else ""
        if not run_name:
            logger.warning(f"⚠️  Row {row_idx}: Missing run name, skipping")
            continue

        # Extract attendees
        attendees_str = row[ATTENDEES_COL].strip() if ATTENDEES_COL < len(row) else ""
        if not attendees_str:
            logger.warning(f"⚠️  Row {row_idx}: No attendees listed for '{run_name}', skipping")
            continue

        # Parse the date
        try:
            date_obj = None
            # Try different date formats
            for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    date_obj = date_obj.replace(tzinfo=eastern_tz)
                    break
                except ValueError:
                    continue

            # If no format matched, try short format (M/D or M/DD) and assume current or next year
            if not date_obj:
                try:
                    # Try parsing without year
                    for short_fmt in ['%m/%d', '%-m/%d', '%-m/%-d']:
                        try:
                            # Parse with a dummy year first
                            temp_date = datetime.strptime(date_str, short_fmt)
                            # Assume current year initially
                            current_year = datetime.now().year
                            date_obj = temp_date.replace(year=current_year, tzinfo=eastern_tz)

                            # If the date is more than 6 months in the past, assume it's for next year
                            now = datetime.now(eastern_tz)
                            if (now - date_obj).days > 180:
                                date_obj = date_obj.replace(year=current_year + 1)
                            # If the date is more than 6 months in the future, assume it's for last year
                            elif (date_obj - now).days > 180:
                                date_obj = date_obj.replace(year=current_year - 1)

                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            if not date_obj:
                logger.warning(f"⚠️  Row {row_idx}: Could not parse date '{date_str}', skipping")
                continue
        except Exception as e:
            logger.warning(f"⚠️  Row {row_idx}: Error parsing date '{date_str}': {e}, skipping")
            continue

        # Parse attendees (comma-separated, may include extra info in parentheses)
        attendees = []
        for attendee in attendees_str.split(','):
            # Clean up the name
            name = attendee.strip()

            # Skip empty names
            if not name:
                continue

            # Take first line only (in case of multi-line entries)
            name = name.split('\n')[0].strip()

            # Strip parenthetical notes (e.g., "Jennie Matz (T)" -> "Jennie Matz")
            # Match pattern: anything followed by space + (anything inside parentheses)
            import re
            name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()

            # Filter out entries that don't look like names (should be alphabetical characters and spaces only)
            if name and re.match(r'^[A-Za-z\s\-\'\.]+$', name):
                attendees.append(name)

        if not attendees:
            logger.warning(f"⚠️  Row {row_idx}: No valid attendees parsed from '{attendees_str}', skipping")
            continue

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


def llm_match_attendance_runs(
    target_run_names: List[str],
    candidate_runs: List[Dict[str, Any]],
    client: OpenAI
) -> List[Dict[str, Any]]:
    """
    Use LLM to intelligently match target run names against candidate attendance runs.

    Args:
        target_run_names: List of run names to match (e.g., [Action Network name, Calendar name])
        candidate_runs: List of attendance run dictionaries to filter
        client: OpenAI client

    Returns:
        Filtered list of runs that match the target
    """
    if not candidate_runs:
        return []

    # If all candidates have the same run name, just return them all
    unique_names = set(run['run_name'] for run in candidate_runs)
    if len(unique_names) == 1:
        logger.info(f"   All candidates have the same name, returning all {len(candidate_runs)} runs")
        return candidate_runs

    # Build list of unique candidate names with their dates
    candidate_info = []
    for name in unique_names:
        matching_runs = [r for r in candidate_runs if r['run_name'] == name]
        dates = [r['date'].strftime('%Y-%m-%d') for r in matching_runs[:3]]
        if len(matching_runs) > 3:
            dates.append(f"... and {len(matching_runs) - 3} more")
        candidate_info.append({
            'name': name,
            'count': len(matching_runs),
            'sample_dates': dates
        })

    target_names_str = "' or '".join(target_run_names)
    candidates_str = "\n".join([
        "- {name} ({count} occurrences, e.g., {dates})".format(
            name=c['name'],
            count=c['count'],
            dates=', '.join(c['sample_dates'])
        ) for c in candidate_info
    ])

    prompt = """You are matching run names to find attendance records for the same geographic location/route.

TARGET RUN NAMES (the run we're looking for):
{target_names_str}

CANDIDATE ATTENDANCE RUNS (all on the same day of week):
{candidates_str}

Your task: Identify which candidates are for the SAME RUN/LOCATION as the target.

MATCHING RULES:
1. EXACT or VERY CLOSE matches should ALWAYS be included
2. Same core location = match (e.g., "South Brooklyn", "Queens", "Prospect Park")
3. Ignore day-of-week prefixes (e.g., "Thursday South Brooklyn" = "South Brooklyn Run")
4. Ignore generic suffixes like "Run", "Loop", "Edition", "Series"
5. Common abbreviations: "PP" = Prospect Park, "CP" = Central Park, "SBK" = South Brooklyn

NON-MATCHING RULES:
1. Different event types: "Queens Loop" ≠ "Queens R2C" or "Queens Run2Canvass"
2. Different neighborhoods: "North Brooklyn" ≠ "South Brooklyn"

Be INCLUSIVE - when in doubt, include it. Focus on the geographic location.

OUTPUT FORMAT:
- Return ONLY the candidate name(s) that match (copy exactly from the candidate list)
- One name per line
- If no matches, return exactly "NONE"
- Do NOT add explanations or extra text

Example:
If target is "Thursday South Brooklyn" and candidates include "SBK Dumping Run" and "Thursday South Brooklyn", you should return both (same location).
If target is "Queens Loop" and candidates include "Queens R2C", do NOT match (different event types).""".format(
        target_names_str=target_names_str,
        candidates_str=candidates_str
    )

    try:
        logger.info(f"   Using LLM to match '{target_names_str}' against {len(unique_names)} candidate names...")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that matches run names. Always respond with candidate names or 'NONE'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        llm_response = response.choices[0].message.content.strip()
        logger.info(f"   LLM response: {llm_response}")

        if llm_response.upper() == "NONE":
            logger.info(f"   LLM determined no matches")
            return []

        # Parse the matched names (strip bullet points if present)
        matched_names = []
        for line in llm_response.split('\n'):
            line = line.strip()
            if line:
                # Remove leading bullet points or dashes
                if line.startswith('- '):
                    line = line[2:].strip()
                elif line.startswith('* '):
                    line = line[2:].strip()
                matched_names.append(line)

        # Filter candidate runs to only those with matched names
        matched_runs = [run for run in candidate_runs if run['run_name'] in matched_names]

        logger.info(f"   LLM matched {len(matched_names)} name(s), returning {len(matched_runs)} total runs")
        return matched_runs

    except Exception as e:
        logger.error(f"   ❌ Error in LLM matching: {e}")
        logger.info(f"   Falling back to returning all candidates")
        return candidate_runs


def find_similar_runs(target_run_names: List[str], target_day_of_week: str,
                      all_runs: List[Dict[str, Any]],
                      client: OpenAI) -> List[Dict[str, Any]]:
    """
    Find runs similar to the target run based on day of week and LLM matching.

    Strategy:
    1. First match by day of week (required)
    2. If only one unique run name on that day, return all runs with that day
    3. If multiple unique run names on that day, use LLM to intelligently match

    Args:
        target_run_names: List of target run names to match against (e.g., [Action Network name, Calendar name])
        target_day_of_week: Day of week (e.g., "Monday")
        all_runs: List of all runs from attendance sheet
        client: OpenAI client for LLM matching

    Returns:
        List of similar run dictionaries
    """
    target_names_display = "' or '".join(target_run_names)
    logger.info(f"🔍 Looking for runs similar to '{target_names_display}' on {target_day_of_week}s")
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

    # Use LLM to match runs
    similar_runs = llm_match_attendance_runs(target_run_names, same_day_runs, client)

    logger.info(f"✅ Found {len(similar_runs)} similar runs to '{target_names_display}' on {target_day_of_week}s")
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


def identify_nudge_candidates(target_run_names: List[str],
                               target_day_of_week: str,
                               current_time: datetime,
                               all_runs: List[Dict[str, Any]],
                               client: OpenAI,
                               max_candidates: int = 10) -> List[Dict[str, Any]]:
    """
    Identify people who should be nudged for the upcoming run.

    Strategy:
    - Include anyone who has attended similar runs in the past
    - Prioritize people who attended 1-3 times (not regulars)
    - Sort by recency (most recent first)
    - Limit to top candidates

    Args:
        target_run_names: List of names for the upcoming run (e.g., [Action Network name, Calendar name])
        target_day_of_week: Day of week for the upcoming run
        current_time: Current datetime
        all_runs: List of all runs from attendance sheet
        client: OpenAI client for LLM matching
        max_candidates: Maximum number of candidates to return (default: 10)

    Returns:
        List of nudge candidate dictionaries with:
        - name: Person's name
        - reason: Why they should be nudged
        - last_attendance: Date of last attendance
        - attendance_count: Total times attended similar runs
        - days_since_last: Days since last attendance
    """
    target_names_display = "' or '".join(target_run_names)
    logger.info(f"🔍 Identifying nudge candidates for '{target_names_display}' on {target_day_of_week}...")

    # Find similar runs
    similar_runs = find_similar_runs(target_run_names, target_day_of_week, all_runs, client)

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

        nudge_candidates.append({
            'name': person,
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
                         nudge_candidates: List[Dict[str, Any]],
                         attendance_form_link: Optional[str] = None,
                         invalid_bl_names: Optional[List[str]] = None) -> str:
    """
    Format the nudge message to send to BLs.

    Args:
        bl_names: List of BL names
        run_name: Name of the run
        nudge_candidates: List of nudge candidate dictionaries
        attendance_form_link: Optional link to attendance form
        invalid_bl_names: Optional list of BL names that couldn't be validated

    Returns:
        Formatted message string
    """
    bl_first_names = [bl_name.split()[0] for bl_name in bl_names]
    if len(bl_first_names) == 1:
        greeting = f"Hi {bl_first_names[0]}!"
    elif len(bl_first_names) == 2:
        greeting = f"Hi {bl_first_names[0]} and {bl_first_names[1]}!"
    else:
        greeting = f"Hi {', '.join(bl_first_names[:-1])}, and {bl_first_names[-1]}!"

    # Build message
    message = f"{greeting} You are assigned to BL {run_name}.\n\n"

    # Add note about invalid BLs if any
    if invalid_bl_names:
        for invalid_name in invalid_bl_names:
            message += f"Note: {invalid_name} is also BL for this run, but their contact info is not available yet.\n\n"

    if not nudge_candidates:
        message += "No specific nudge suggestions at this time. Great job spreading the word!"
    else:
        message += "Here are a few people you may want to nudge for today:\n\n"

        for candidate in nudge_candidates:
            name = candidate['name']
            last_date = candidate['last_attendance']

            # Format last attendance date
            last_date_str = last_date.strftime('%b %d, %Y') if last_date else 'Unknown'

            message += f"• {name}\n"
            message += f"  Last attended: {last_date_str}\n\n"

    # Add attendance form link if provided
    if attendance_form_link:
        message += f"\nPlease mark attendance after the run: {attendance_form_link}"

    return message.strip()
