"""The PC Bio Unlock integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .lock import PCBUnlockServer, PCBLock
from .models import PCBLockConfig

PLATFORMS: list[Platform] = [Platform.LOCK]


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data[DOMAIN] = {"entries": {}, "server": PCBUnlockServer(hass)}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN]["entries"][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    pcbunlock_server: PCBUnlockServer = hass.data[DOMAIN]["server"]

    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    lock_conf = PCBLockConfig.from_dict(entry_data)
    lock = PCBLock(lock_conf)
    await pcbunlock_server.remove_lock(lock)

    return True
