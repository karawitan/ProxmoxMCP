"""
Tests for security validation and input sanitization.
"""

import pytest
from proxmox_mcp.utils.validation import InputValidator, ValidationError


class TestInputValidator:
    """Test the InputValidator security features."""
    
    def test_validate_node_name_valid(self):
        """Test valid node names."""
        valid_names = [
            "pve1",
            "proxmox-node2", 
            "node_3",
            "cluster-1",
            "test-123"
        ]
        
        for name in valid_names:
            result = InputValidator.validate_node_name(name)
            assert result == name
    
    def test_validate_node_name_invalid(self):
        """Test invalid node names."""
        invalid_names = [
            "",  # Empty
            None,  # None
            123,  # Not a string
            "node with spaces",  # Spaces
            "node@domain",  # @ symbol
            "node/path",  # / symbol
            "node;command",  # Semicolon
            "a" * 65,  # Too long
            "node|pipe",  # Pipe
            "node&amp",  # Ampersand
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                InputValidator.validate_node_name(name)
    
    def test_validate_vmid_valid(self):
        """Test valid VM IDs."""
        valid_vmids = [
            "100", 
            "999", 
            "12345",
            100,  # Integer input
            999999  # Max range
        ]
        
        for vmid in valid_vmids:
            result = InputValidator.validate_vmid(vmid)
            assert isinstance(result, str)
            assert int(result) >= 100
    
    def test_validate_vmid_invalid(self):
        """Test invalid VM IDs."""
        invalid_vmids = [
            "",  # Empty
            None,  # None
            "abc",  # Non-numeric
            "99",  # Too small
            "1000000",  # Too large
            "123.45",  # Decimal
            "123abc",  # Mixed
            "-123",  # Negative
        ]
        
        for vmid in invalid_vmids:
            with pytest.raises(ValidationError):
                InputValidator.validate_vmid(vmid)
    
    def test_validate_command_allowed(self):
        """Test allowed commands."""
        allowed_commands = [
            "ls",
            "ls -l",
            "ls -la",
            "uptime",
            "uname -a",
            "whoami", 
            "pwd",
            "date",
            "ps aux",
            "df -h",
            "free -h",
            "systemctl status nginx",
            "ip addr show"
        ]
        
        for cmd in allowed_commands:
            result = InputValidator.validate_command(cmd)
            assert result == cmd
    
    def test_validate_command_dangerous(self):
        """Test dangerous commands are blocked."""
        dangerous_commands = [
            "rm -rf /",  # rm not in whitelist
            "ls | grep secret",  # Pipe
            "ls; rm file",  # Semicolon 
            "ls && rm file",  # Ampersand
            "ls > /tmp/file",  # Redirect
            "cat /etc/passwd",  # Cat without validation
            "$(whoami)",  # Command substitution
            "`whoami`",  # Backticks
            "ls $HOME",  # Variable expansion
            "ls (test)",  # Parentheses
            "python -c 'import os; os.system(\"rm -rf /\")'",  # python not in whitelist
            "sh -c 'dangerous command'",  # sh not in whitelist
        ]
        
        for cmd in dangerous_commands:
            with pytest.raises(ValidationError):
                InputValidator.validate_command(cmd)
    
    def test_validate_command_edge_cases(self):
        """Test command validation edge cases."""
        edge_cases = [
            "",  # Empty
            None,  # None
            123,  # Not a string
            "a" * 501,  # Too long
            "   ls   ",  # Whitespace (should be trimmed)
        ]
        
        for cmd in edge_cases[:-1]:  # All except the last one
            with pytest.raises(ValidationError):
                InputValidator.validate_command(cmd)
        
        # Test whitespace trimming
        result = InputValidator.validate_command("   ls   ")
        assert result == "ls"
    
    def test_sanitize_log_data(self):
        """Test log data sanitization."""
        sensitive_data = {
            "user": "root@pam",
            "token_name": "test-token",
            "token_value": "secret-12345",
            "password": "secret-password",
            "api_key": "api-secret-key",
            "host": "proxmox.example.com",
            "port": 8006,
            "nested": {
                "secret": "nested-secret",
                "public": "public-info"
            }
        }
        
        sanitized = InputValidator.sanitize_log_data(sensitive_data)
        
        # Check that sensitive fields are masked
        assert sanitized["token_name"] == "****"
        assert sanitized["token_value"] == "****"
        assert sanitized["password"] == "****"
        assert sanitized["api_key"] == "****"
        assert sanitized["nested"]["secret"] == "****"
        
        # Check that non-sensitive fields are preserved
        assert sanitized["user"] == "root@pam"
        assert sanitized["host"] == "proxmox.example.com"
        assert sanitized["port"] == 8006
        assert sanitized["nested"]["public"] == "public-info"
    
    def test_validate_storage_name_valid(self):
        """Test valid storage names."""
        valid_names = [
            "local",
            "ceph-storage",
            "nfs_backup",
            "storage.001",
            "test-123"
        ]
        
        for name in valid_names:
            result = InputValidator.validate_storage_name(name)
            assert result == name
    
    def test_validate_storage_name_invalid(self):
        """Test invalid storage names."""
        invalid_names = [
            "",  # Empty
            None,  # None
            123,  # Not a string
            "storage with spaces",  # Spaces
            "storage@domain",  # @ symbol
            "storage/path",  # / symbol
            "storage;command",  # Semicolon
            "a" * 65,  # Too long
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                InputValidator.validate_storage_name(name)


class TestSecurityIntegration:
    """Test security integration across the system."""
    
    def test_command_whitelist_coverage(self):
        """Test that command whitelist covers expected use cases."""
        expected_commands = [
            'ls', 'uptime', 'uname', 'whoami', 'pwd', 'date', 
            'ps', 'df', 'free', 'cat', 'systemctl', 'service', 'ip', 'netstat'
        ]
        
        for cmd in expected_commands:
            assert cmd in InputValidator.ALLOWED_COMMANDS
    
    def test_file_path_safety(self):
        """Test file path safety checks."""
        # This tests the internal _is_safe_file_path method
        safe_paths = [
            "/etc/hosts",
            "/var/log/messages", 
            "/proc/cpuinfo",
            "/sys/class/net",
            "local_file.txt"
        ]
        
        for path in safe_paths:
            assert InputValidator._is_safe_file_path(path)
        
        unsafe_paths = [
            "../../../etc/passwd",  # Directory traversal
            "/etc/../../../etc/passwd",  # Directory traversal in absolute path
            "subdir/../../../etc/passwd",  # Directory traversal in relative path
        ]
        
        for path in unsafe_paths:
            assert not InputValidator._is_safe_file_path(path)
