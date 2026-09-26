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
