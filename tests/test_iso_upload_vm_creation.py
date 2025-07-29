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
    vm_id = 122
    disk_size_gb = 8

    # 1. Create a dummy ISO file
    with tempfile.NamedTemporaryFile(suffix=".iso", delete=False) as temp_iso:
        temp_iso.write(b"This is a dummy ISO file content.")
        dummy_iso_filepath = temp_iso.name
    print(f"Created dummy ISO at: {dummy_iso_filepath}")

    iso_name = os.path.basename(dummy_iso_filepath) # Use the actual filename from tempfile
    iso_path_on_proxmox = f"{storage_name}:iso/{iso_name}"

    try:
        # 2. Upload the dummy ISO
        print(f"Uploading ISO '{iso_name}' to node '{node_name}', storage '{storage_name}'...")
        with open(dummy_iso_filepath, 'rb') as f:
            upload_response = proxmox_client.nodes(node_name).storage(storage_name).upload.post(
                content="iso",
                filename=f
            )
        print(f"ISO '{iso_name}' uploaded successfully. Upload response: {upload_response}")
        import time
        time.sleep(2) # Give Proxmox time to register the ISO

        # Verify ISO existence after upload
        iso_found = False
        storage_content = proxmox_client.nodes(node_name).storage(storage_name).content.get()
        print(f"Storage content for {storage_name}: {storage_content}")
        for item in storage_content:
            print(f"Checking item: {item.get('volid')}")
            if item.get('content') == 'iso' and iso_name in item.get('volid', ''):
                iso_found = True
                iso_path_on_proxmox = item.get('volid') # Update iso_path_on_proxmox with the actual volid
                break
        assert iso_found, f"Uploaded ISO {iso_name} not found in storage {storage_name}."
        print(f"Verified ISO {iso_name} exists in storage.")

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

        # Verify VM creation
        vm_config = proxmox_client.nodes(node_name).qemu(vm_id).config.get()
        assert vm_config is not None, f"VM {vm_id} configuration not found after creation."
        print(f"Verified VM {vm_id} configuration exists.")

        vms = proxmox_client.cluster.resources.get(type='vm')
        assert any(vm['vmid'] == vm_id for vm in vms), f"VM {vm_id} not found in resource list after creation."
        print(f"Verified VM {vm_id} exists in resource list.")

    finally:
        # 4. Cleanup
        print(f"Starting cleanup for VM {vm_id} and ISO '{iso_name}'...")
        try:
            # Stop VM if running
            vms = proxmox_client.cluster.resources.get(type='vm')
            if any(vm['vmid'] == vm_id and vm['status'] == 'running' for vm in vms):
                print(f"Stopping VM {vm_id}...")
                proxmox_client.nodes(node_name).qemu(vm_id).status.stop.post()
                time.sleep(5) # Wait for VM to stop

            # Delete VM
            print(f"Deleting VM {vm_id}...")
            # Check if VM exists before attempting to delete
            vms = proxmox_client.cluster.resources.get(type='vm')
            if any(vm['vmid'] == vm_id for vm in vms):
                proxmox_client.nodes(node_name).qemu(vm_id).delete()
                print(f"VM {vm_id} deleted.")
                # Verify VM deletion
                time.sleep(5) # Add a small delay for deletion to propagate
                vms_after_deletion = proxmox_client.cluster.resources.get(type='vm')
                assert not any(vm['vmid'] == vm_id for vm in vms_after_deletion), f"VM {vm_id} still found after deletion."
                print(f"Verified VM {vm_id} is no longer in resource list.")
            else:
                print(f"VM {vm_id} not found, skipping deletion.")
        except Exception as e:
            print(f"Error deleting VM {vm_id}: {e}")
            raise # Re-raise the exception to fail the test

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
