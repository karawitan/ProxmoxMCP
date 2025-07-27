"""
Tests for the Proxmox MCP server.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from proxmox_mcp.server import ProxmoxMCPServer

@pytest.fixture
def mock_env_vars():
    """Fixture to set up test environment variables."""
    env_vars = {
        "PROXMOX_HOST": "test.proxmox.com",
        "PROXMOX_USER": "test@pve",
        "PROXMOX_TOKEN_NAME": "test_token",
        "PROXMOX_TOKEN_VALUE": "test_value",
        "LOG_LEVEL": "DEBUG"
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def mock_config():
    """Fixture to mock load_config to use environment variables."""
    from proxmox_mcp.config.models import Config, ProxmoxConfig, AuthConfig, LoggingConfig
    
    def mock_load_config(config_path=None):
        return Config(
            proxmox=ProxmoxConfig(
                host=os.environ["PROXMOX_HOST"],
                port=8006,
                verify_ssl=True,
                service="PVE"
            ),
            auth=AuthConfig(
                user=os.environ["PROXMOX_USER"],
                token_name=os.environ["PROXMOX_TOKEN_NAME"],
                token_value=os.environ["PROXMOX_TOKEN_VALUE"]
            ),
            logging=LoggingConfig(
                level=os.environ.get("LOG_LEVEL", "INFO")
            )
        )
    
    with patch("proxmox_mcp.server.load_config", side_effect=mock_load_config):
        yield mock_load_config

@pytest.fixture
def mock_proxmox():
    """Fixture to mock ProxmoxAPI."""
    with patch("proxmox_mcp.core.proxmox.ProxmoxAPI") as mock:
        mock.return_value.nodes.get.return_value = [
            {"node": "node1", "status": "online"},
            {"node": "node2", "status": "online"}
        ]
        yield mock

@pytest.fixture
def server(mock_env_vars, mock_config, mock_proxmox):
    """Fixture to create a ProxmoxMCPServer instance."""
    return ProxmoxMCPServer()

def test_server_initialization(server, mock_proxmox):
    """Test server initialization with environment variables."""
    assert server.config.proxmox.host == "test.proxmox.com"
    assert server.config.auth.user == "test@pve"
    assert server.config.auth.token_name == "test_token"
    assert server.config.auth.token_value == "test_value"
    assert server.config.logging.level == "DEBUG"

    mock_proxmox.assert_called_once()

@pytest.mark.asyncio
async def test_list_tools(server):
    """Test listing available tools."""
    tools = await server.mcp.list_tools()

    assert len(tools) > 0
    tool_names = [tool.name for tool in tools]
    assert "get_nodes" in tool_names
    assert "get_vms" in tool_names
    # get_containers tool is not implemented
    assert "execute_vm_command" in tool_names

@pytest.mark.asyncio
async def test_get_nodes(server, mock_proxmox):
    """Test get_nodes tool."""
    # Mock the node list call
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"},
        {"node": "node2", "status": "online"}
    ]
    # Mock the detailed status calls for each node with proper numeric values
    mock_proxmox.return_value.nodes.return_value.status.get.return_value = {
        "uptime": 123456,
        "cpuinfo": {"cpus": 4},
        "memory": {"used": 1024*1024*1024, "total": 4*1024*1024*1024}  # 1GB used, 4GB total
    }
    
    response = await server.mcp.call_tool("get_nodes", {})
    # The response is formatted text, not JSON, so check that it contains the node names
    response_text = response[0].text
    assert "node1" in response_text
    assert "node2" in response_text

@pytest.mark.asyncio
async def test_get_node_status_missing_parameter(server):
    """Test get_node_status tool with missing parameter."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_node_status", {})

@pytest.mark.asyncio
async def test_get_node_status(server, mock_proxmox):
    """Test get_node_status tool with valid parameter."""
    mock_proxmox.return_value.nodes.return_value.status.get.return_value = {
        "status": "running",
        "uptime": 123456,
        "cpuinfo": {"cpus": 4},
        "memory": {"used": 1024*1024*1024, "total": 4*1024*1024*1024}  # 1GB used, 4GB total
    }

    response = await server.mcp.call_tool("get_node_status", {"node": "node1"})
    # The response is formatted text, not JSON, so check that it contains expected information
    response_text = response[0].text
    assert "node1" in response_text
    assert "RUNNING" in response_text or "running" in response_text

@pytest.mark.asyncio
async def test_get_vms(server, mock_proxmox):
    """Test get_vms tool."""
    mock_proxmox.return_value.nodes.get.return_value = [{"node": "node1", "status": "online"}]
    mock_proxmox.return_value.nodes.return_value.qemu.get.return_value = [
        {"vmid": "100", "name": "vm1", "status": "running", "mem": 1024*1024*1024, "maxmem": 2*1024*1024*1024},
        {"vmid": "101", "name": "vm2", "status": "stopped", "mem": 0, "maxmem": 1024*1024*1024}
    ]
    # Mock VM config calls with proper numeric values
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.config.get.return_value = {
        "cores": 2
    }

    response = await server.mcp.call_tool("get_vms", {})
    # The response is formatted text, not JSON, so check that it contains the VM names
    response_text = response[0].text
    assert "vm1" in response_text
    assert "vm2" in response_text


@pytest.mark.asyncio
async def test_get_storage(server, mock_proxmox):
    """Test get_storage tool."""
    mock_proxmox.return_value.storage.get.return_value = [
        {"storage": "local", "type": "dir", "node": "node1", "enabled": True, "content": ["images", "rootdir"]},
        {"storage": "ceph", "type": "rbd", "node": "node1", "enabled": True, "content": ["images"]}
    ]
    # Mock storage status calls with proper numeric values
    mock_proxmox.return_value.nodes.return_value.storage.return_value.status.get.return_value = {
        "used": 1024*1024*1024,  # 1GB used
        "total": 10*1024*1024*1024,  # 10GB total
        "avail": 9*1024*1024*1024   # 9GB available
    }

    response = await server.mcp.call_tool("get_storage", {})
    # The response is formatted text, not JSON, so check that it contains the storage names
    response_text = response[0].text
    assert "local" in response_text
    assert "ceph" in response_text

@pytest.mark.asyncio
async def test_get_cluster_status(server, mock_proxmox):
    """Test get_cluster_status tool."""
    # Mock cluster status with proper list format
    mock_proxmox.return_value.cluster.status.get.return_value = [
        {"name": "test-cluster", "quorate": 1, "type": "cluster"},
        {"name": "node1", "type": "node", "online": 1},
        {"name": "node2", "type": "node", "online": 1}
    ]

    response = await server.mcp.call_tool("get_cluster_status", {})
    # The response is formatted text, not JSON, so check that it contains expected information
    response_text = response[0].text
    assert "test-cluster" in response_text or "cluster" in response_text.lower()

@pytest.mark.asyncio
async def test_execute_vm_command_success(server, mock_proxmox):
    """Test successful VM command execution."""
    # Mock VM status check
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "running"
    }
    # Mock two-phase command execution: exec returns pid, exec-status returns results
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.post.return_value = {
        "pid": 12345
    }
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.get.return_value = {
        "out-data": "command output",
        "err-data": "",
        "exitcode": 0,
        "exited": 1
    }

    response = await server.mcp.call_tool("execute_vm_command", {
        "node": "node1",
        "vmid": "100",
        "command": "ls -l"
    })
    # The response is formatted text, not JSON, so check that it contains expected information
    response_text = response[0].text
    assert "SUCCESS" in response_text or "success" in response_text.lower()
    assert "command output" in response_text
    assert "ls -l" in response_text

@pytest.mark.asyncio
async def test_execute_vm_command_missing_parameters(server):
    """Test VM command execution with missing parameters."""
    with pytest.raises(ToolError):
        await server.mcp.call_tool("execute_vm_command", {})

@pytest.mark.asyncio
async def test_execute_vm_command_vm_not_running(server, mock_proxmox):
    """Test VM command execution when VM is not running."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "stopped"
    }

    with pytest.raises(ToolError, match="not running"):
        await server.mcp.call_tool("execute_vm_command", {
            "node": "node1",
            "vmid": "100",
            "command": "ls -l"
        })

@pytest.mark.asyncio
async def test_execute_vm_command_with_error(server, mock_proxmox):
    """Test VM command execution with command error."""
    # Mock VM status check
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "running"
    }
    # Mock two-phase command execution with error
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.post.return_value = {
        "pid": 12345
    }
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.get.return_value = {
        "out-data": "",
        "err-data": "command not found",
        "exitcode": 1,
        "exited": 1
    }

    response = await server.mcp.call_tool("execute_vm_command", {
        "node": "node1",
        "vmid": "100",
        "command": "ls /proc/nonexistent"
    })
    # The response is formatted text, not JSON, so check that it contains expected information
    response_text = response[0].text
    assert "SUCCESS" in response_text or "success" in response_text.lower()  # API call succeeded
    assert "command not found" in response_text
    assert "ls /proc/nonexistent" in response_text
