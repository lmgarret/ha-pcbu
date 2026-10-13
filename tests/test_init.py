"""Test component setup."""

from homeassistant.setup import async_setup_component

from custom_components.pcbu.const import DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


async def test_load_entry_stored_by_0_2(hass, socket_enabled):
    """Entries stored by ha-pcbu 0.2 (dataclass-wizard 0.x) still load."""
    from homeassistant.config_entries import ConfigEntryState
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    data = {
        "pairingId": "a",
        "desktopIpAddress": "127.0.0.1",
        "desktopOs": "Windows",
        "serverIpAddress": "127.0.0.1",
        "serverPort": 43991,
        "username": "user",
        "password": "pwd",
        "encryptionKey": "key",
        "remoteInfo": {
            "name": "desktop",
            "ipAddress": "127.0.0.1",
            "macAddress": "AA:BB",
            "os": "Windows",
        },
    }
    entry = MockConfigEntry(domain=DOMAIN, unique_id="a", data=data, version=2)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.remote_info.mac_address == "AA:BB"
    assert entry.runtime_data.to_dict() == data
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unavailable_server_ip(hass, socket_enabled):
    """An entry whose Home Assistant IP address is gone retries and raises an issue,
    until it is reconfigured."""
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.helpers import issue_registry as ir
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.pcbu.models import PCBLockConfig, PCBRemoteInfo

    conf = PCBLockConfig(
        pairing_id="a",
        desktop_ip_address="127.0.0.1",
        desktop_os="Linux",
        # TEST-NET-1 address the host does not have
        server_ip_address="192.0.2.1",
        server_port=43992,
        username="user",
        password="pwd",
        encryption_key="key",
        remote_info=PCBRemoteInfo(
            name="desktop", ip_address="127.0.0.1", mac_address="AA:BB", os="Linux"
        ),
    )
    entry = MockConfigEntry(domain=DOMAIN, unique_id="a", data=conf.to_dict())
    entry.add_to_hass(hass)
    issue_id = f"unavailable_ip_{entry.entry_id}"

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue.translation_placeholders == {"name": "desktop", "ip": "192.0.2.1"}

    conf.server_ip_address = "127.0.0.1"
    hass.config_entries.async_update_entry(entry, data=conf.to_dict())
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    assert await hass.config_entries.async_remove(entry.entry_id)
