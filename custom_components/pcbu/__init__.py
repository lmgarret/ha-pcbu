"""The PC Bio Unlock integration."""

from __future__ import annotations

import socket

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .models import PCBLockConfig, PCBUConfigEntry
from .server import DATA_SERVER, PCBUnlockServer

PLATFORMS: list[Platform] = [Platform.LOCK]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DATA_SERVER] = PCBUnlockServer(hass)
    return True


def _check_local_ip(ip_address: str) -> None:
    """Raise an OSError if this host has no such IP address to listen on."""
    family = socket.AF_INET6 if ":" in ip_address else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((ip_address, 0))


def _issue_id(entry: PCBUConfigEntry) -> str:
    return f"unavailable_ip_{entry.entry_id}"


async def async_setup_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    conf = PCBLockConfig.from_dict(entry.data)
    placeholders = {"name": conf.remote_info.name, "ip": conf.server_ip_address}
    try:
        await hass.async_add_executor_job(_check_local_ip, conf.server_ip_address)
    except OSError as err:
        # e.g. Home Assistant moved to another IP address since the pairing
        ir.async_create_issue(
            hass,
            DOMAIN,
            _issue_id(entry),
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="unavailable_ip",
            translation_placeholders=placeholders,
        )
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="unavailable_ip",
            translation_placeholders=placeholders,
        ) from err
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry))

    entry.runtime_data = conf
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    # removing the lock entity also removes it from the unlock server
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry))


async def async_migrate_entry(hass: HomeAssistant, entry: PCBUConfigEntry) -> bool:
    if entry.version == 1:
        # entries created with py-pcbu < 0.5.0 lack the desktop OS
        data = {**entry.data}
        if "desktopOs" not in data and "desktop_os" not in data:
            remote_info = data.get("remoteInfo") or data.get("remote_info") or {}
            data["desktopOs"] = remote_info.get("os", "")
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
