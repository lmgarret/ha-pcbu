"""Test the diagnostics."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.pcbu.const import DOMAIN

from .test_lock import _lock_conf


async def test_diagnostics(hass: HomeAssistant, hass_client, socket_enabled):
    assert await async_setup_component(hass, "diagnostics", {})
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="a", data=_lock_conf("a").to_dict(), version=2
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    data = diagnostics["data"]
    for key in ("password", "encryptionKey", "username"):
        assert data[key] == "**REDACTED**"
    assert data["pairingId"] == "a"
    assert diagnostics["unlock_server"] == {
        "running": True,
        "locks": 1,
        "pending_unlock_request": False,
    }
    assert await hass.config_entries.async_unload(entry.entry_id)
