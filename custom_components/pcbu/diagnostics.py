"""Diagnostics support for PC Bio Unlock."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .models import PCBUConfigEntry
from .server import DATA_SERVER

TO_REDACT = {"encryptionKey", "password", "username"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PCBUConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    conf = entry.runtime_data
    runtime = hass.data[DATA_SERVER].servers.get(conf.server_port)
    return {
        "entry": async_redact_data(entry.as_dict(), {"data"}),
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "unlock_server": {
            "running": runtime is not None,
            "locks": len(runtime["server"].locks) if runtime else 0,
            "pending_unlock_request": bool(
                runtime and runtime["server"].has_pending_unlock_request(conf)
            ),
        },
    }
