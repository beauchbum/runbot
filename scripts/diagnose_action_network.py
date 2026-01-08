#!/usr/bin/env python3
"""
Diagnostic script for Action Network API connection issues.

This script helps diagnose 403 Forbidden and other API errors by:
1. Checking if the API key is set
2. Testing basic API connectivity
3. Showing detailed request/response information
4. Testing different endpoints

Usage:
    python scripts/diagnose_action_network.py
"""

import sys
import os
import logging
import requests
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up logging with DEBUG level for maximum detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ACTION_NETWORK_API_BASE = "https://actionnetwork.org/api/v2"


def check_api_key():
    """Check if API key is properly set."""
    logger.info("=" * 60)
    logger.info("STEP 1: Checking API Key Configuration")
    logger.info("=" * 60)

    api_key = os.getenv('ACTION_NETWORK_API_KEY')

    if not api_key:
        logger.error("❌ ACTION_NETWORK_API_KEY environment variable is NOT set")
        logger.info("\nPlease set your API key:")
        logger.info("  export ACTION_NETWORK_API_KEY='your_api_key_here'")
        return False

    logger.info(f"✅ API key is set")
    logger.info(f"   Length: {len(api_key)} characters")
    logger.info(f"   First 10 chars: {api_key[:10]}...")
    logger.info(f"   Last 10 chars: ...{api_key[-10:]}")

    # Check for common issues
    if api_key.startswith(' ') or api_key.endswith(' '):
        logger.warning("⚠️  API key has leading/trailing whitespace")

    if '\n' in api_key or '\r' in api_key:
        logger.warning("⚠️  API key contains newline characters")

    return True


def test_api_endpoint():
    """Test the API endpoint with detailed logging."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Testing API Endpoint")
    logger.info("=" * 60)

    api_key = os.getenv('ACTION_NETWORK_API_KEY', '').strip()
    url = f"{ACTION_NETWORK_API_BASE}/events"

    headers = {
        'OSDI-API-Token': api_key
    }

    params = {
        'page': 1,
        'per_page': 5
    }

    logger.info(f"Request details:")
    logger.info(f"   URL: {url}")
    logger.info(f"   Method: GET")
    logger.info(f"   Headers: {list(headers.keys())}")
    logger.info(f"   Params: {params}")

    try:
        logger.info("\nSending request...")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        logger.info(f"\nResponse received:")
        logger.info(f"   Status Code: {response.status_code}")
        logger.info(f"   Reason: {response.reason}")
        logger.info(f"   Headers: {dict(response.headers)}")

        if response.status_code == 200:
            logger.info(f"\n✅ SUCCESS! API request succeeded")
            data = response.json()
            logger.info(f"   Total records: {data.get('total_records', 'Unknown')}")
            logger.info(f"   Total pages: {data.get('total_pages', 'Unknown')}")

            events = data.get('_embedded', {}).get('osdi:events', [])
            logger.info(f"   Events on this page: {len(events)}")

            if events:
                logger.info(f"\n   First event preview:")
                first_event = events[0]
                logger.info(f"      Title: {first_event.get('title', 'N/A')}")
                logger.info(f"      Name: {first_event.get('name', 'N/A')}")
                logger.info(f"      Start: {first_event.get('start_date', 'N/A')}")

            return True

        elif response.status_code == 403:
            logger.error(f"\n❌ 403 Forbidden - Access Denied")
            logger.error(f"   This typically means:")
            logger.error(f"   1. The API key is invalid or expired")
            logger.error(f"   2. The API key lacks permissions to access events")
            logger.error(f"   3. Your account is not a partner account")
            logger.error(f"\n   Response body:")
            logger.error(f"   {response.text[:1000]}")

            return False

        elif response.status_code == 401:
            logger.error(f"\n❌ 401 Unauthorized - Authentication Failed")
            logger.error(f"   The API key is not being accepted")
            logger.error(f"\n   Response body:")
            logger.error(f"   {response.text[:1000]}")

            return False

        else:
            logger.error(f"\n❌ Unexpected status code: {response.status_code}")
            logger.error(f"   Response body:")
            logger.error(f"   {response.text[:1000]}")

            return False

    except requests.exceptions.Timeout:
        logger.error(f"\n❌ Request timed out")
        return False

    except requests.exceptions.ConnectionError as e:
        logger.error(f"\n❌ Connection error: {e}")
        return False

    except requests.exceptions.RequestException as e:
        logger.error(f"\n❌ Request error: {e}")
        return False

    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        return False


def test_alternative_endpoint():
    """Test an alternative endpoint to see if it's an endpoint-specific issue."""
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Testing Alternative Endpoint (Entry Point)")
    logger.info("=" * 60)

    api_key = os.getenv('ACTION_NETWORK_API_KEY', '').strip()
    url = ACTION_NETWORK_API_BASE  # Just the base URL

    headers = {
        'OSDI-API-Token': api_key
    }

    logger.info(f"Testing base API endpoint: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        logger.info(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"✅ Base endpoint accessible")
            data = response.json()

            # Show available endpoints
            if '_links' in data:
                logger.info(f"\n   Available endpoints:")
                for key, value in data['_links'].items():
                    if isinstance(value, dict) and 'href' in value:
                        logger.info(f"      - {key}: {value['href']}")

            return True
        else:
            logger.error(f"❌ Base endpoint returned {response.status_code}")
            logger.error(f"   Response: {response.text[:500]}")
            return False

    except Exception as e:
        logger.error(f"❌ Error testing base endpoint: {e}")
        return False


def main():
    """Main diagnostic routine."""
    logger.info("🔧 Action Network API Diagnostics\n")

    # Step 1: Check API key
    if not check_api_key():
        return 1

    # Step 2: Test main endpoint
    success = test_api_endpoint()

    # Step 3: Try alternative endpoint
    test_alternative_endpoint()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)

    if success:
        logger.info("✅ All checks passed! API connection is working.")
        return 0
    else:
        logger.error("❌ API connection failed. Please check:")
        logger.error("   1. Your API key is correct")
        logger.error("   2. Your account has partner access")
        logger.error("   3. The API key has not expired")
        logger.error("\n   Generate API keys at:")
        logger.error("   https://actionnetwork.org/docs (after becoming a partner)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
