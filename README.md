# BeauchBot - AI Assistant for Event Management

An intelligent messaging assistant that automates event coordination and communication via SMS. BeauchBot manages contact lists, coordinates with event organizers, sends reminders to attendees, and integrates with calendar and event management systems.

## Features

- **Automated Event Messaging**: Send personalized reminders to event attendees with organizer contacts included
- **Smart Deduplication**: Checks message history to avoid duplicate messages about the same event
- **Calendar Integration**: Parses calendar documents to extract events, times, and organizer assignments
- **Action Network Integration**: Links calendar events to Action Network for attendee lists and RSVPs
- **Contact Management**: Validates organizers and attendees against contact directories
- **Attendance Tracking**: Reads and writes attendance data to Google Sheets
- **Phone Number Normalization**: Consistent E.164 format (+1XXXXXXXXXX) throughout the system
- **Group Messaging**: Creates group conversations with event organizers and individual attendees
- **Scheduled Execution**: Cron-friendly script with dry-run and time simulation for testing

## Setup

### Environment Variables

Create a `.env` file with:

```bash
# OpenAI (required)
OPENAI_API_KEY=your_openai_api_key

# Twilio (required)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15551234567
MY_PHONE_NUMBER=+15559876543

# Google (required - Base64 encoded service account JSON)
GOOGLE_SERVICE_ACCOUNT_B64=your_encoded_service_account

# Contact Directory (required - Google Doc ID)
PHONE_DIRECTORY_DOC_ID=your_phone_directory_document_id

# Attendance Tracking (optional - Google Sheets ID)
ATTENDANCE_SHEET_ID=your_attendance_google_sheets_id

# Action Network (optional - for event/attendee integration)
ACTION_NETWORK_API_KEY=your_action_network_api_key

# Organizer Filtering (optional - comma-separated list)
ALLOWED_BLS=John Smith,Jane Doe
```

**Note**: All phone numbers should be in E.164 format (+1XXXXXXXXXX), though the system will normalize various formats automatically.

### Installation

```shell
# Using uv (recommended)
uv sync --no-editable

# Or with pip
pip install -r requirements.txt
```

### Docker

```shell
docker-compose up --build
```

## Usage

### Scheduled Event Messaging

The main workflow automatically:
1. Identifies upcoming events from calendar documents
2. Extracts organizer assignments
3. Matches events to Action Network for attendee lists
4. Sends personalized group messages to attendees with organizers included
5. Tracks message history to prevent duplicates

```bash
# Run the messaging workflow
python scripts/ping_agent.py

# Dry run mode (no actual messages sent)
python scripts/ping_agent.py --dry-run

# Simulate a specific time for testing
python scripts/ping_agent.py --simulate-time "2024-01-15,09:00"

# Include attendance-based nudge suggestions
python scripts/ping_agent.py --include-nudges
```

### Automated Scheduling

Add to crontab for hourly execution:
```bash
0 * * * * cd /path/to/beauchbot && python scripts/ping_agent.py >> /var/log/beauchbot.log 2>&1
```

**Note**: The script only runs during operating hours (8 AM - 8 PM) and processes events within a configurable time window.

## Configuration

### Google Service Account

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Docs API and Google Sheets API
3. Create and download service account JSON key
4. Base64 encode the JSON and set as `GOOGLE_SERVICE_ACCOUNT_B64`

```bash
base64 -i service-account.json | tr -d '\n'
```

### Contact Directory

Create a Google Doc with contacts in the format:
```
Name: Phone Number
John Smith: +15551234567
Jane Doe: (555) 987-6543
Bob Wilson: 555-111-2222
```

Share the document with your service account email (viewer access) and set the document ID in `PHONE_DIRECTORY_DOC_ID`.

**Note**: Phone numbers can be in any common format - they will be normalized automatically.

### Calendar Documents

Calendar documents should contain event information including:
- Event names and times
- Organizer assignments (e.g., "BL: (H) John (T) Jane")
- Date and location details

The LLM will intelligently parse the calendar structure to extract events and assignments.

### Attendance Tracking (Optional)

Set `ATTENDANCE_SHEET_ID` to enable writing attendance data to Google Sheets. The sheet will be automatically populated with:
- Event dates
- Event names
- Attendee lists

## Architecture

**Core Components**:
- `scripts/ping_agent.py` - Main workflow orchestrator
- `utils/phone_utils.py` - Phone number normalization and validation
- `utils/action_network_utils.py` - Event and attendee integration
- `utils/attendance_utils.py` - Attendance analysis and nudge suggestions
- `tools/twilio.py` - SMS messaging with group conversation support
- `tools/google_docs.py` - Document reading and sheet writing

**Key Features**:
- LLM-powered calendar parsing and name matching
- On-demand message history fetching for efficiency
- Smart deduplication across multiple conversations
- Group MMS support with automatic conversation reuse

## Development

### Testing

```bash
# Test phone number normalization
python scripts/test_phone_normalization.py

# Test message history fetching
python scripts/test_message_history.py +15551234567

# Test Action Network integration
python scripts/test_action_network.py
```

### Dependencies

```bash
# Add new package
uv add package-name

# Update all dependencies
uv sync --upgrade --no-editable

# Run scripts
uv run python scripts/ping_agent.py
```

## License

MIT