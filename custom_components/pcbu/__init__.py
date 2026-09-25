"""The PC Bio Unlock integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .lock import PCBUnlockServer

PLATFORMS: list[Platform] = [Platform.LOCK]


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data[DOMAIN] = {"entries": {}, "server": PCBUnlockServer(hass)}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN]["entries"][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # removing the lock entity also removes it from the unlock server
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]["entries"].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version == 1:
        # entries created with py-pcbu < 0.5.0 lack the desktop OS
        data = {**entry.data}
        if "desktopOs" not in data and "desktop_os" not in data:
            remote_info = data.get("remoteInfo") or data.get("remote_info") or {}
            data["desktopOs"] = remote_info.get("os", "")
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
