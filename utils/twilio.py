"""
Twilio tools for BeauchBot.

Provides functionality to:
- Send individual SMS and Group MMS messages
- Get conversation history for individuals and groups
- Get contact phone numbers

All phone numbers are normalized to E.164 format (+1XXXXXXXXXX) for consistency.
"""

import os
import logging
import re
from typing import List, Dict, Any

# OpenAI Agents
from agents import function_tool

# Twilio
from twilio.rest import Client

# Import shared phone utilities
from utils.phone_utils import validate_phone_numbers_against_contacts, format_contact_list_for_error, normalize_phone_number

logger = logging.getLogger(__name__)

# Reduce Twilio logging verbosity
logging.getLogger('twilio').setLevel(logging.WARNING)
logging.getLogger('twilio.http_client').setLevel(logging.WARNING)


def get_twilio_client():
    """Initialize and return a Twilio client using environment variables."""
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    if not account_sid or not auth_token:
        raise ValueError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables are required"
        )
    
    return Client(account_sid, auth_token)


def get_twilio_phone_number() -> str:
    """
    Get the Twilio phone number from environment variables.

    Returns:
        Normalized phone number in E.164 format (+1XXXXXXXXXX)

    Raises:
        ValueError: If environment variable is not set or phone number is invalid
    """
    twilio_number = os.getenv('TWILIO_PHONE_NUMBER')

    if not twilio_number:
        raise ValueError("TWILIO_PHONE_NUMBER environment variable is required")

    try:
        return normalize_phone_number(twilio_number)
    except ValueError as e:
        raise ValueError(f"Invalid TWILIO_PHONE_NUMBER: {e}")


def get_my_phone_number() -> str:
    """
    Get my personal phone number from environment variables.

    Returns:
        Normalized phone number in E.164 format (+1XXXXXXXXXX)

    Raises:
        ValueError: If environment variable is not set or phone number is invalid
    """
    my_number = os.getenv('MY_PHONE_NUMBER')

    if not my_number:
        raise ValueError("MY_PHONE_NUMBER environment variable is required")

    try:
        return normalize_phone_number(my_number)
    except ValueError as e:
        raise ValueError(f"Invalid MY_PHONE_NUMBER: {e}")


def send_text(to_numbers: List[str], message: str) -> Dict[str, Any]:
    """Send a text message to an individual or group via Twilio.

    For individual messaging (1 number): Standard SMS between you and one recipient
    For group messaging (2+ numbers): Creates Group MMS where all participants see each other's messages
    Group MMS requires US/Canada (+1) numbers and creates true group conversations.
    Automatically reuses existing conversations with the same participants to avoid conflicts.

    Args:
        to_numbers: List of phone numbers in any format (will be normalized to E.164: +1XXXXXXXXXX)
        message: The message content to send

    Returns:
        Message status information or group conversation details including 'reused_existing' flag
    """
    try:
        if not to_numbers or len(to_numbers) == 0:
            return {"error": "At least one phone number is required"}

        # Normalize all phone numbers to E.164 format
        normalized_numbers = []
        for phone in to_numbers:
            try:
                normalized = normalize_phone_number(phone)
                normalized_numbers.append(normalized)
            except ValueError as e:
                return {"error": f"Invalid phone number '{phone}': {e}"}

        client = get_twilio_client()
        from_number = get_twilio_phone_number()
        
        # Determine if this is individual or group messaging based on recipient count
        if len(normalized_numbers) == 1:
            # Individual messaging using standard SMS
            return _send_individual_text(client, from_number, normalized_numbers[0], message)
        else:
            # Group messaging using Group MMS
            return _send_group_text(client, from_number, normalized_numbers, message)
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {"error": str(e)}
    
    except Exception as e:
        logger.error(f"Error sending text: {e}")
        return {"error": f"Failed to send text: {str(e)}"}

# ============================================================================
# HELPER FUNCTIONS (Internal)
# ============================================================================

def _send_individual_text(client, from_number: str, to_number: str, message: str) -> Dict[str, Any]:
    """Send individual SMS message."""
    
    # Send SMS using standard Twilio messaging
    message_result = client.messages.create(
        body=message,
        from_=from_number,
        to=to_number
    )
    
    response = {
        "type": "individual",
        "message_sid": message_result.sid,
        "to": to_number,
        "from": from_number,
        "body": message,
        "status": message_result.status,
        "date_created": message_result.date_created.isoformat() if message_result.date_created else None
    }
    
    logger.info(f"Individual SMS sent to {to_number}, Message: {message_result.sid}")
    return response


def _find_existing_group_conversation(client, target_participants: List[str]) -> Dict[str, Any]:
    """Find an existing Group MMS conversation with the same participants."""
    try:
        # Get recent conversations to check
        conversations = client.conversations.v1.conversations.list(limit=50)
        
        # Convert target participants to a set for comparison
        target_set = set(target_participants)
        
        for conversation in conversations:
            try:
                # Skip if conversation is not active
                if conversation.state != 'active':
                    continue
                
                # Get participants for this conversation
                participants = client.conversations.v1.conversations(conversation.sid).participants.list()
                
                # Extract phone numbers from participants
                participant_numbers = set()
                business_participant = None
                
                for participant in participants:
                    if participant.messaging_binding:
                        # SMS participant - has address
                        if hasattr(participant.messaging_binding, 'address') and participant.messaging_binding.address:
                            participant_numbers.add(participant.messaging_binding.address)
                        elif isinstance(participant.messaging_binding, dict) and participant.messaging_binding.get('address'):
                            participant_numbers.add(participant.messaging_binding['address'])
                    
                    # Track business participant
                    if participant.identity == "beauchbot_assistant":
                        business_participant = participant

                # Check if this conversation has the same SMS participants
                if participant_numbers == target_set:
                    logger.info(f"Found matching conversation: {conversation.sid}")
                    return {
                        "sid": conversation.sid,
                        "friendly_name": conversation.friendly_name,
                        "participants": list(participant_numbers),
                        "business_participant": business_participant.sid if business_participant else None
                    }
                    
            except Exception as e:
                logger.warning(f"Error checking conversation {conversation.sid}: {e}")
                continue
        
        logger.info("No existing conversation found with matching participants")
        return None
        
    except Exception as e:
        logger.error(f"Error finding existing group conversation: {e}")
        return None


def _send_group_text(client, from_number: str, to_numbers: List[str], message: str) -> Dict[str, Any]:
    """Send Group MMS message using Conversations API."""
    try:
        # Validate US/Canada numbers (Group MMS requirement)
        for phone_number in to_numbers:
            if not phone_number.startswith('+1'):
                return {"error": f"Group MMS only supports US/Canada (+1) numbers. Invalid: {phone_number}"}
        
        # Check if there's already an existing conversation with the same participants
        existing_conversation = _find_existing_group_conversation(client, to_numbers)
        
        if existing_conversation:
            logger.info(f"Found existing Group MMS conversation: {existing_conversation['sid']}")
            
            # Ensure beauchbot_assistant participant exists in the conversation
            try:
                # Check if beauchbot_assistant is already a participant
                participants = client.conversations.v1.conversations(existing_conversation['sid']).participants.list()
                beauchbot_participant_exists = any(p.identity == "beauchbot_assistant" for p in participants)
                
                if not beauchbot_participant_exists:
                    logger.info("Adding beauchbot_assistant participant to existing conversation")
                    # Add beauchbot_assistant as chat participant
                    client.conversations.v1.conversations(existing_conversation['sid']).participants.create(
                        identity="beauchbot_assistant",
                        messaging_binding_projected_address=from_number
                    )
                
                # Now send the message
                message_result = client.conversations.v1.conversations(existing_conversation['sid']).messages.create(
                    body=message,
                    author="beauchbot_assistant"
                )
                
                response = {
                    "type": "group",
                    "conversation_sid": existing_conversation['sid'],
                    "message_sid": message_result.sid,
                    "reused_existing": True,
                    "existing_participants": existing_conversation['participants'],
                    "body": message,
                    "date_created": message_result.date_created.isoformat() if message_result.date_created else None
                }
                
                logger.info(f"Group MMS sent to existing conversation: {existing_conversation['sid']}, Message: {message_result.sid}")
                return response
                
            except Exception as e:
                logger.error(f"Failed to send message to existing conversation: {e}")
                # Fall back to creating a new conversation
                logger.info("Falling back to creating new conversation...")

        # Create new conversation
        logger.info(f"Creating new Group MMS conversation with {len(to_numbers)} participants")
        
        # Create conversation
        conversation = client.conversations.v1.conversations.create(
            friendly_name=f"Group conversation {len(to_numbers)} participants"
        )
        
        # Add SMS participants using Group MMS setup (no proxy address)
        participants_added = []
        participants_failed = []
        
        for to_number in to_numbers:
            try:
                # Group MMS: SMS participants have ONLY address, NO proxy address
                participant = client.conversations.v1.conversations(conversation.sid).participants.create(
                    messaging_binding_address=to_number
                )
                
                participants_added.append({
                    "phone_number": to_number,
                    "participant_sid": participant.sid
                })
                
            except Exception as e:
                logger.error(f"Failed to add participant {to_number}: {e}")
                participants_failed.append({
                    "phone_number": to_number,
                    "error": str(e)
                })
        
        # Add business chat participant with projected address
        try:
            chat_participant = client.conversations.v1.conversations(conversation.sid).participants.create(
                identity="beauchbot_assistant",
                messaging_binding_projected_address=from_number
            )
            
            participants_added.append({
                "phone_number": f"BeauchBot (projected: {from_number})",
                "participant_sid": chat_participant.sid
            })
            
        except Exception as e:
            logger.error(f"Failed to add chat participant: {e}")
            participants_failed.append({
                "phone_number": "BeauchBot",
                "error": str(e)
            })
        
        # Send the message as BeauchBot
        if len(participants_added) > 0:
            message_result = client.conversations.v1.conversations(conversation.sid).messages.create(
                body=message,
                author="beauchbot_assistant"
            )
            
            response = {
                "type": "group",
                "conversation_sid": conversation.sid,
                "message_sid": message_result.sid,
                "reused_existing": False,
                "participants_added": participants_added,
                "participants_failed": participants_failed,
                "body": message,
                "date_created": message_result.date_created.isoformat() if message_result.date_created else None
            }
            
            logger.info(f"Group MMS sent successfully to conversation: {conversation.sid}, Message: {message_result.sid}")
            return response
        else:
            return {"error": "Failed to add any participants to the group conversation"}
            
    except Exception as e:
        logger.error(f"Error sending group text: {e}")
        return {"error": f"Failed to send group text: {str(e)}"}


def get_all_messages_to_phone_number(phone_number: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get all messages sent from our Twilio number to a specific phone number.

    This searches across all conversations (individual and group) to find any messages
    we've sent to this person, regardless of which conversation they were in.

    Args:
        phone_number: Phone number in any format (will be normalized to E.164: +1XXXXXXXXXX)
        limit: Maximum number of messages to retrieve (default: 20)

    Returns:
        List of message dictionaries with body, date_created, and conversation info
    """
    try:
        # Normalize the phone number
        try:
            phone_number = normalize_phone_number(phone_number)
        except ValueError as e:
            logger.error(f"Invalid phone number '{phone_number}': {e}")
            return []

        client = get_twilio_client()
        twilio_number = get_twilio_phone_number()

        all_messages = []

        # Search through recent conversations to find ones that include this phone number
        conversations = client.conversations.v1.conversations.list(limit=100)

        for conversation in conversations:
            try:
                if conversation.state != 'active':
                    continue

                # Get participants for this conversation
                participants = client.conversations.v1.conversations(conversation.sid).participants.list()

                # Check if the target phone number is a participant
                participant_found = False
                for participant in participants:
                    if participant.messaging_binding:
                        participant_address = None
                        if hasattr(participant.messaging_binding, 'address') and participant.messaging_binding.address:
                            participant_address = participant.messaging_binding.address
                        elif isinstance(participant.messaging_binding, dict) and participant.messaging_binding.get('address'):
                            participant_address = participant.messaging_binding['address']

                        if participant_address == phone_number:
                            participant_found = True
                            break

                # If this conversation includes the target phone number, get messages
                if participant_found:
                    # Get messages from this conversation sent by beauchbot_assistant
                    messages = client.conversations.v1.conversations(conversation.sid).messages.list(
                        limit=limit,
                        order='desc'
                    )

                    for msg in messages:
                        # Only include messages sent by us (beauchbot_assistant)
                        if msg.author == "beauchbot_assistant":
                            all_messages.append({
                                "conversation_sid": conversation.sid,
                                "body": msg.body,
                                "date_created": msg.date_created.isoformat() if msg.date_created else None,
                                "message_sid": msg.sid
                            })

            except Exception as e:
                logger.warning(f"Error checking conversation {conversation.sid}: {e}")
                continue

        # Sort by date (most recent first)
        all_messages.sort(key=lambda x: x.get('date_created', ''), reverse=True)

        # Limit to requested number
        all_messages = all_messages[:limit]

        logger.debug(f"Found {len(all_messages)} messages sent to {phone_number} across all conversations")
        return all_messages

    except Exception as e:
        logger.error(f"Error fetching all messages to {phone_number}: {e}")
        return []
