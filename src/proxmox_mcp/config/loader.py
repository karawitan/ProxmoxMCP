"""
Configuration loading utilities for the Proxmox MCP server.

This module handles loading and validation of server configuration:
- Environment variable loading from .env file
- Configuration validation using Pydantic models
- Error handling for missing or invalid configurations

The module ensures that all required configuration is present
and valid before the server starts operation.
"""
import os
import sys
from typing import Optional

from dotenv import load_dotenv, find_dotenv

from .models import Config


def load_config(dotenv_path: Optional[str] = None) -> Config:
    """Load and validate configuration from environment variables.

    Performs the following steps:
    1. Locates and loads .env file (or uses provided path)
    2. Loads environment variables from .env file
    3. Validates required environment variables are present
    4. Converts to typed Config object using Pydantic

    Required environment variables:
    - PROXMOX_HOST: Proxmox server hostname/IP
    - PROXMOX_PORT: Proxmox server port (optional, defaults to 8006)
    - PROXMOX_USER: Proxmox username
    - PROXMOX_TOKEN_NAME: API token name
    - PROXMOX_TOKEN_VALUE: API token value
    - PROXMOX_VERIFY_SSL: SSL verification (optional, defaults to true)
    - LOG_LEVEL: Logging level (optional, defaults to INFO)

    Args:
        dotenv_path: Path to the .env file
                    If not provided, searches for .env in current and parent directories

    Returns:
        Config object containing validated configuration with structure:
        {
            "proxmox": {
                "host": "proxmox-host",
                "port": 8006,
                "user": "username",
                "verify_ssl": true
            },
            "auth": {
                "token_name": "token-name",
                "token_value": "token-value"
            },
            "logging": {
                "level": "INFO"
            }
        }

    Raises:
        RuntimeError: If required environment variables are missing
        ValueError: If environment variable values are invalid
        SystemExit: If .env file is not found
    """
    
    # Load .env file
    if dotenv_path:
        if not os.path.exists(dotenv_path):
            print(f".env file not found at {dotenv_path}. Exiting.")
            sys.exit(1)
        load_dotenv(dotenv_path)
    else:
        dotenv_file = find_dotenv()
        if not dotenv_file:
            print(".env file not found. Exiting.")
            sys.exit(1)
        load_dotenv(dotenv_file)

    # Load and validate required environment variables
    proxmox_host = os.getenv('PROXMOX_HOST')
    if not proxmox_host:
        raise RuntimeError("PROXMOX_HOST environment variable must be set")

    proxmox_user = os.getenv('PROXMOX_USER')
    if not proxmox_user:
        raise RuntimeError("PROXMOX_USER environment variable must be set")

    token_name = os.getenv('PROXMOX_TOKEN_NAME')
    if not token_name:
        raise RuntimeError("PROXMOX_TOKEN_NAME environment variable must be set")

    token_value = os.getenv('PROXMOX_TOKEN_VALUE')
    if not token_value:
        raise RuntimeError("PROXMOX_TOKEN_VALUE environment variable must be set")

    # Load optional environment variables with defaults
    proxmox_port = int(os.getenv('PROXMOX_PORT', '8006'))
    verify_ssl = os.getenv('PROXMOX_VERIFY_SSL', 'true').lower() in ('true', '1', 'yes', 'on')
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Validate port number
    if not (1 <= proxmox_port <= 65535):
        raise ValueError(f"Invalid PROXMOX_PORT value: {proxmox_port}. Must be between 1 and 65535")

    # Validate log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_log_levels:
        raise ValueError(f"Invalid LOG_LEVEL value: {log_level}. Must be one of {valid_log_levels}")

    # Build configuration dictionary
    config_data = {
        "proxmox": {
            "host": proxmox_host,
            "port": proxmox_port,
            "user": proxmox_user,
            "verify_ssl": verify_ssl
        },
        "auth": {
            "token_name": token_name,
            "token_value": token_value
        },
        "logging": {
            "level": log_level
        }
    }

    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Failed to create config object: {e}") from e


def get_env_var(var_name: str, default: Optional[str] = None, required: bool = True) -> str:
    """Helper function to get environment variable with validation.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if variable is not set
        required: Whether the variable is required
        
    Returns:
        Environment variable value
        
    Raises:
        RuntimeError: If required variable is missing and no default provided
    """
    value = os.getenv(var_name, default)
    if required and not value:
        raise RuntimeError(f"{var_name} environment variable must be set")
    return value
