"""Lock entity: available and locked while its desktop waits to be unlocked."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .models import PCBLockConfig, PCBUConfigEntry
from .server import DATA_SERVER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PCBUConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PCBLock(entry.runtime_data)])


class PCBLock(LockEntity):
    """A paired desktop. Unlocking it sends the credentials to its pending request."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, conf: PCBLockConfig) -> None:
        self.conf = conf
        # set by the unlock server the lock is registered on
        self.unlock_cb: Callable[[], Awaitable[None]] | None = None

        self._attr_is_locked = False
        self._attr_available = False
        self._attr_unique_id = conf.pairing_id
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, conf.remote_info.mac_address),
                (DOMAIN, conf.pairing_id),
            },
            name=conf.remote_info.name,
            model=conf.remote_info.os,
        )

    async def async_added_to_hass(self) -> None:
        await self.hass.data[DATA_SERVER].add_lock(self)

    async def async_will_remove_from_hass(self) -> None:
        await self.hass.data[DATA_SERVER].remove_lock(self)
        self.unlock_cb = None

    async def async_lock(self, **kwargs: Any) -> None:
        # the integration actually does not support locking
        # another integration would be required for that
        pass

    async def async_unlock(self, **kwargs: Any) -> None:
        name = self.conf.remote_info.name
        if self.unlock_cb is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="no_unlock_server",
                translation_placeholders={"name": name},
            )
        try:
            await self.unlock_cb()
        except (ValueError, OSError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unlock_failed",
                translation_placeholders={"name": name, "error": str(err)},
            ) from err
        finally:
            # the unlock request can only be answered once, even if it failed
            self.set_unavailable()

    @callback
    def set_available_and_locked(self) -> None:
        self._attr_available = True
        self._attr_is_locked = True
        self._write_state()

    @callback
    def set_unavailable(self) -> None:
        self._attr_available = False
        self._attr_is_locked = False
        self._write_state()

    @callback
    def _write_state(self) -> None:
        # the unlock server can call back while the entity is being removed
        if self.hass is not None:
            self.async_write_ha_state()
