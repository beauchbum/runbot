"""
Configuration utilities for BeauchBot.

Provides functionality to fetch configuration from either Windmill or environment variables,
with automatic fallback for local development.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_variable(key: str, windmill_path: str = "f/run_club") -> Optional[str]:
    """
    Get a configuration variable from Windmill or environment variables.

    This function tries Windmill first (if available), then falls back to environment variables.
    This allows the code to work both in Windmill and in local development without requiring
    wmill as a dependency.

    Args:
        key: The variable name (e.g., "openai_api_key")
        windmill_path: The Windmill folder path (default: "f/run_club")

    Returns:
        The variable value, or None if not found

    Examples:
        >>> get_variable("openai_api_key")
        # First tries: wmill.get_variable("f/run_club/openai_api_key")
        # Then tries: os.getenv("OPENAI_API_KEY")
    """
    # Try Windmill first (inline import so it's optional)
    try:
        import wmill
        windmill_key = f"{windmill_path}/{key}"
        value = wmill.get_variable(windmill_key)
        if value:
            logger.debug(f"Loaded '{key}' from Windmill")
            return value
    except ImportError:
        # wmill not installed - this is fine for local development
        logger.debug("wmill package not available, using environment variables")
    except Exception as e:
        # Windmill variable not found or other error
        logger.debug(f"Could not load '{key}' from Windmill: {e}")

    # Fall back to environment variable
    # Convert snake_case to UPPER_SNAKE_CASE for env var name
    env_var_name = key.upper()
    value = os.getenv(env_var_name)

    if value:
        logger.debug(f"Loaded '{key}' from environment variable {env_var_name}")
        return value

    # Not found in either location
    logger.debug(f"Variable '{key}' not found in Windmill or environment")
    return None


def require_variable(key: str, windmill_path: str = "f/run_club") -> str:
    """
    Get a required configuration variable, raising an error if not found.

    Args:
        key: The variable name (e.g., "openai_api_key")
        windmill_path: The Windmill folder path (default: "f/run_club")

    Returns:
        The variable value

    Raises:
        ValueError: If the variable is not found in Windmill or environment

    Examples:
        >>> api_key = require_variable("openai_api_key")
    """
    value = get_variable(key, windmill_path)

    if not value:
        env_var_name = key.upper()
        raise ValueError(
            f"Required configuration variable '{key}' not found. "
            f"Set it in Windmill as '{windmill_path}/{key}' or as environment variable '{env_var_name}'"
        )

    return value
