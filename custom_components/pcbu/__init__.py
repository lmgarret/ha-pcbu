"""The PC Bio Unlock integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .models import PCBLockConfig, PCBUConfigEntry
from .server import DATA_SERVER, PCBUnlockServer

PLATFORMS: list[Platform] = [Platform.LOCK]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DATA_SERVER] = PCBUnlockServer(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    entry.runtime_data = PCBLockConfig.from_dict(entry.data)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    # removing the lock entity also removes it from the unlock server
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    if entry.version == 1:
        # entries created with py-pcbu < 0.5.0 lack the desktop OS
        data = {**entry.data}
        if "desktopOs" not in data and "desktop_os" not in data:
            remote_info = data.get("remoteInfo") or data.get("remote_info") or {}
            data["desktopOs"] = remote_info.get("os", "")
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
