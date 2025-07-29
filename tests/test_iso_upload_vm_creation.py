import os
import pytest
import tempfile
import re
from proxmoxer import ProxmoxAPI

def sanitize_host(host):
    if not host:
        return host
    return re.sub(r'^https?://', '', host)

@pytest.fixture(scope="module")
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
        verify_ssl=False,
        timeout=30 # Increased timeout to 30 seconds
    )
    return proxmox

def test_iso_upload_and_vm_creation(proxmox_client):
    node_name = "pve"  # Replace with your Proxmox node name
    storage_name = "local"  # Replace with your ISO storage name
    iso_name = "test_dummy_iso.iso"
    vm_id = 122
    disk_size_gb = 8
    iso_path_on_proxmox = f"{storage_name}:iso/{iso_name}"

    # 1. Create a dummy ISO file
    with tempfile.NamedTemporaryFile(suffix=".iso", delete=False) as temp_iso:
        temp_iso.write(b"This is a dummy ISO file content.")
        dummy_iso_filepath = temp_iso.name
    print(f"Created dummy ISO at: {dummy_iso_filepath}")

    try:
        # 2. Upload the dummy ISO
        print(f"Uploading ISO '{iso_name}' to node '{node_name}', storage '{storage_name}'...")
        with open(dummy_iso_filepath, 'rb') as f:
            proxmox_client.nodes(node_name).storage(storage_name).upload.post(
                content="iso",
                filename=f
            )
        print(f"ISO '{iso_name}' uploaded successfully.")

        # 3. Create the VM
        print(f"Creating VM {vm_id} on node '{node_name}'...")
        proxmox_client.nodes(node_name).qemu.create(
            vmid=vm_id,
            name=f"test-vm-{vm_id}",
            memory=512,  # MB
            sockets=1,
            cores=1,
            ide0=f"{iso_path_on_proxmox},media=cdrom",
            scsi0=f"local-lvm:{disk_size_gb}", # Assuming 'local-lvm' is your LVM-Thin storage
            boot="order=ide0;scsi0"
        )
        print(f"VM {vm_id} created successfully.")

        # Optional: Verify VM creation (e.g., check if it exists)
        vms = proxmox_client.cluster.resources.get(type='vm')
        assert any(vm['vmid'] == vm_id for vm in vms), f"VM {vm_id} not found after creation."
        print(f"Verified VM {vm_id} exists.")

    finally:
        # 4. Cleanup
        print(f"Starting cleanup for VM {vm_id} and ISO '{iso_name}'...")
        try:
            # Delete VM
            print(f"Deleting VM {vm_id}...")
            # Check if VM exists before attempting to delete
            vms = proxmox_client.cluster.resources.get(type='vm')
            if any(vm['vmid'] == vm_id for vm in vms):
                proxmox_client.nodes(node_name).qemu(vm_id).delete()
                print(f"VM {vm_id} deleted.")
            else:
                print(f"VM {vm_id} not found, skipping deletion.")
        except Exception as e:
            print(f"Error deleting VM {vm_id}: {e}")

        try:
            # Delete uploaded ISO
            print(f"Deleting ISO '{iso_name}' from storage '{storage_name}'...")
            proxmox_client.nodes(node_name).storage(storage_name).content(f"iso/{iso_name}").delete()
            print(f"ISO '{iso_name}' deleted.")
        except Exception as e:
            print(f"Error deleting ISO '{iso_name}': {e}")

        # Delete dummy ISO file from local filesystem
        if os.path.exists(dummy_iso_filepath):
            os.remove(dummy_iso_filepath)
            print(f"Dummy ISO file '{dummy_iso_filepath}' removed from local filesystem.")
