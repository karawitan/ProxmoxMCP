"""
Input validation and sanitization utilities for the Proxmox MCP server.

This module provides comprehensive input validation and sanitization to prevent
security vulnerabilities such as injection attacks and malformed input handling.

Key features:
- Node name validation
- VM ID validation
- Command sanitization and whitelisting
- Parameter sanitization
- Error handling for invalid inputs
"""

import re
from typing import List, Optional, Union
import logging

logger = logging.getLogger("proxmox-mcp.validation")


class ValidationError(ValueError):
    """Custom exception for validation errors."""

    pass


class InputValidator:
    """Comprehensive input validation and sanitization utility."""

    # Allowed node name pattern (alphanumeric, hyphens, underscores)
    NODE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    # VM ID pattern (numeric only)
    VMID_PATTERN = re.compile(r"^\d+$")

    # Allowed command whitelist (expandable)
    ALLOWED_COMMANDS = {
        "ls": ["ls", "-l", "-la", "-al", "-a", "--color=auto", "--color=never"],
        "uptime": ["uptime"],
        "uname": ["uname", "-a", "-r", "-v", "-m", "-n", "-s"],
        "whoami": ["whoami"],
        "pwd": ["pwd"],
        "date": ["date"],
        "ps": ["ps", "aux", "-ef"],
        "df": ["df", "-h"],
        "free": ["free", "-h"],
        "cat": ["cat"],  # Note: should be used carefully with file path validation
        "systemctl": ["systemctl", "status", "is-active", "is-enabled", "nginx"],
        "service": ["service", "--status-all"],
        "ip": ["ip", "addr", "show", "link", "route"],
        "netstat": ["netstat", "-tuln"],
    }

    @staticmethod
    def validate_node_name(node_name: str) -> str:
        """
        Validate and sanitize node name.

        Args:
            node_name: Node name to validate

        Returns:
            Validated node name

        Raises:
            ValidationError: If node name is invalid
        """
        if not node_name or not isinstance(node_name, str):
            raise ValidationError("Node name must be a non-empty string")

        node_name = node_name.strip()

        if len(node_name) > 64:
            raise ValidationError("Node name is too long (max 64 characters)")

        if not InputValidator.NODE_NAME_PATTERN.match(node_name):
            raise ValidationError(
                "Node name contains invalid characters. Only alphanumeric, "
                "hyphens, and underscores are allowed"
            )

        return node_name

    @staticmethod
    def validate_vmid(vmid: Union[str, int]) -> str:
        """
        Validate and sanitize VM ID.

        Args:
            vmid: VM ID to validate (string or integer)

        Returns:
            Validated VM ID as string

        Raises:
            ValidationError: If VM ID is invalid
        """
        if isinstance(vmid, int):
            vmid = str(vmid)

        if not vmid or not isinstance(vmid, str):
            raise ValidationError("VM ID must be a non-empty string or integer")

        vmid = vmid.strip()

        if not InputValidator.VMID_PATTERN.match(vmid):
            raise ValidationError("VM ID must be numeric")

        # Check reasonable range (Proxmox typically uses 100-999999)
        vmid_int = int(vmid)
        if vmid_int < 100 or vmid_int > 999999:
            raise ValidationError("VM ID must be between 100 and 999999")

        return vmid

    @staticmethod
    def validate_command(command: str) -> str:
        """
        Validate and sanitize command for execution.

        This method implements a whitelist approach to command validation,
        only allowing specific commands and their safe parameters.

        Args:
            command: Command to validate

        Returns:
            Validated command

        Raises:
            ValidationError: If command is not allowed or contains unsafe elements
        """
        if not command or not isinstance(command, str):
            raise ValidationError("Command must be a non-empty string")

        command = command.strip()

        if len(command) > 500:
            raise ValidationError("Command is too long (max 500 characters)")

        # Parse command and arguments
        command_parts = command.split()
        base_command = command_parts[0]

        # Check if base command is in whitelist
        if base_command not in InputValidator.ALLOWED_COMMANDS:
            raise ValidationError(f"Command '{base_command}' is not allowed")

        # Validate arguments against whitelist
        allowed_args = InputValidator.ALLOWED_COMMANDS[base_command]

        for part in command_parts:
            # Check for dangerous characters
            if any(
                char in part for char in ["|", "&", ";", ">", "<", "`", "$", "(", ")"]
            ):
                raise ValidationError(f"Command contains dangerous characters: {part}")

            # For non-base commands, check if they're in allowed args or safe file paths
            if part != base_command and part not in allowed_args:
                # Allow safe file paths for certain commands
                if base_command in ["cat", "ls"] and InputValidator._is_safe_file_path(
                    part
                ):
                    continue
                elif not part.startswith("-"):  # Allow arguments that start with -
                    raise ValidationError(
                        f"Argument '{part}' is not allowed for command '{base_command}'"
                    )

        logger.info(f"Command validated successfully: {command}")
        return command

    @staticmethod
    def _is_safe_file_path(path: str) -> bool:
        """
        Check if a file path is safe for certain operations.

        Args:
            path: File path to check

        Returns:
            True if path is considered safe
        """
        # Prevent directory traversal
        if ".." in path:
            return False

        # Only allow paths in safe directories (with specific file restrictions)
        safe_prefixes = ["/var/log/", "/proc/", "/sys/"]
        if any(path.startswith(prefix) for prefix in safe_prefixes):
            return True

        # Allow only specific safe files in /etc/
        safe_etc_files = ["/etc/hosts", "/etc/hostname", "/etc/os-release"]
        if path in safe_etc_files:
            return True

        # Allow relative paths in current directory (but not subdirectories with ..)
        if "/" not in path or (path.count("/") == 1 and not path.startswith("/")):
            return True

        return False

    @staticmethod
    def sanitize_log_data(data: dict) -> dict:
        """
        Sanitize dictionary data for safe logging by masking sensitive values.

        Args:
            data: Dictionary containing potentially sensitive data

        Returns:
            Dictionary with sensitive values masked
        """
        sensitive_keys = {
            "password",
            "passwd",
            "token",
            "secret",
            "key",
            "auth",
            "token_name",
            "token_value",
            "api_key",
            "access_token",
        }

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "****"
            elif isinstance(value, dict):
                sanitized[key] = InputValidator.sanitize_log_data(value)
            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def validate_storage_name(storage_name: str) -> str:
        """
        Validate storage name parameter.

        Args:
            storage_name: Storage name to validate

        Returns:
            Validated storage name

        Raises:
            ValidationError: If storage name is invalid
        """
        if not storage_name or not isinstance(storage_name, str):
            raise ValidationError("Storage name must be a non-empty string")

        storage_name = storage_name.strip()

        if len(storage_name) > 64:
            raise ValidationError("Storage name is too long (max 64 characters)")

        # Allow alphanumeric, hyphens, underscores, and dots
        if not re.match(r"^[a-zA-Z0-9_.-]+$", storage_name):
            raise ValidationError(
                "Storage name contains invalid characters. Only alphanumeric, "
                "hyphens, underscores, and dots are allowed"
            )

        return storage_name
