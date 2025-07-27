import os
import re
from dotenv import load_dotenv
import pytest
from proxmoxer import ProxmoxAPI

load_dotenv()

def sanitize_host(host):
    if not host:
        return host
    return re.sub(r'^https?://', '', host)

@pytest.fixture(scope="session")
def proxmox_client():
    host = sanitize_host(os.getenv("PROXMOX_HOST"))
    user = os.getenv("PROXMOX_USER")
    token_name = os.getenv("PROXMOX_TOKEN_NAME")
    token_value = os.getenv("PROXMOX_TOKEN_VALUE")

    if not all([host, user, token_name, token_value]):
        pytest.skip("Proxmox connection details not fully configured in environment")

    proxmox = ProxmoxAPI(
        host,
        user=user,
        token_name=token_name,
        token_value=token_value,
        verify_ssl=False
    )
    return proxmox


def test_get_proxmox_version(proxmox_client):
    version_info = proxmox_client.version.get()
    assert "version" in version_info
    assert "release" in version_info
    print(f"Proxmox API Version: {version_info['version']}, Release: {version_info['release']}")

