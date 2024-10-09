# ruff: noqa: D103, D102, D107, D101
import asyncio
from collections import defaultdict
from typing import TypedDict

from pcbu.models import PCPairing
from pcbu.tcp.unlock_server import TCPUnlockServerBase

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import PCBLockConfig
import logging

_LOGGER = logging.getLogger(__name__)


class TCPUnlockServer(TCPUnlockServerBase):
    """Implementation of py-pcbu's TCPUnlockServerBase. When the unlock requests comes in, sets the lock as available."""

    def __init__(self, locks: list["PCBLock"]) -> None:
        self.locks = locks
        super().__init__([lock.conf for lock in locks])
        for lock in locks:

            async def unlock_cb():
                await self.unlock(lock.conf)

            lock._unlock_cb = unlock_cb

    def get_lock(self, pairing: PCPairing) -> "PCBLock":
        for lock in self.locks:
            if lock.conf.pairing_id == pairing.pairing_id:
                return lock
        raise ValueError(
            f"Could not find matching lock for pairing id {pairing.pairing_id}"
        )

    async def on_valid_unlock_request(self, pairing: PCPairing) -> None:
        """see TCPUnlockServerBase.on_valid_unlock_request"""
        _LOGGER.info(f"Accepted unlock request from {pairing.desktop_ip_address}")
        lock = self.get_lock(pairing)
        lock.set_available_and_locked()

    async def on_invalid_unlock_request(self, ip_address: str):
        """see TCPUnlockServerBase.on_invalid_unlock_request"""
        _LOGGER.info(f"Rejected unlock request from {ip_address}")


class TCPServerRuntime(TypedDict):
    """Typing model, only used in PCBUnlockServer to hold a ref to a single TCPServer alongside its HASS task"""

    server: TCPUnlockServer
    task: asyncio.Task


class PCBUnlockServer:
    """Platform for our integration. This should only be instantiated once, when the integration is setup."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.locks = defaultdict(dict)
        self.servers: dict[int, TCPServerRuntime] = {}

    async def _refresh_tcp_server(self, port: int, new_locks: list["PCBLock"]):
        """assumes the locks all share the same unlock server port"""
        if port in self.servers:
            server = self.servers[port]["server"]
            task: asyncio.Task = self.servers[port]["task"]

            _LOGGER.info(f"Stopping server (:{port}) ({len(server.locks)} locks)...")
            task.cancel()
            del self.servers[port]

        async def _start_tcp_server(server: TCPUnlockServer):
            async with server:
                await server.start()

        new_server = TCPUnlockServer(locks=new_locks)
        task = self.hass.async_create_background_task(
            _start_tcp_server(new_server), name=f"PCBUnlock Server (:{port})"
        )
        self.servers[port] = {"server": new_server, "task": task}

    async def add_lock(self, lock: "PCBLock"):
        port = lock.conf.server_port
        self.locks[port][lock.conf.desktop_ip_address] = lock
        await self._refresh_tcp_server(port=port, new_locks=self.locks[port].values())

    async def remove_lock(self, lock: "PCBLock"):
        port = lock.conf.server_port
        del self.locks[lock.conf.server_port][lock.conf.desktop_ip_address]
        await self._refresh_tcp_server(port=port, new_locks=self.locks[port].values())


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    pcbunlock_server: PCBUnlockServer = hass.data[DOMAIN]["server"]

    entry_data = hass.data[DOMAIN]["entries"][config_entry.entry_id]
    lock_conf = PCBLockConfig.from_dict(entry_data)

    lock = PCBLock(lock_conf)
    await pcbunlock_server.add_lock(lock)
    async_add_entities([lock])


async def async_unload_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> bool:
    pcbunlock_server: PCBUnlockServer = hass.data[DOMAIN]["server"]

    entry_data = hass.data[DOMAIN]["entries"][config_entry.entry_id]
    lock_conf = PCBLockConfig.from_dict(entry_data)

    lock = PCBLock(lock_conf)
    await pcbunlock_server.remove_lock(lock)

    return True


class PCBLock(LockEntity):
    def __init__(self, conf: PCBLockConfig):
        self.conf = conf

        self._unlock_cb = None

        self._attr_name = conf.remote_info.name
        self._attr_is_locked = False
        self._attr_available = False

        self._attr_unique_id = conf.pairing_id
        self._attr_device_info = {
            "identifiers": {
                (DOMAIN, conf.remote_info.mac_address),
                (DOMAIN, conf.pairing_id),
            },
            "name": conf.remote_info.name,
        }

    @property
    def name(self):
        return self.conf.remote_info.name

    async def async_lock(self, **kwargs):
        # the integration actually does not support locking
        # another integration would be required for that
        pass

    async def async_unlock(self, **kwargs):
        if self._unlock_cb:
            await self._unlock_cb()
            self._attr_is_locked = False
            self._attr_available = False
            self.async_write_ha_state()

    @callback
    def set_available_and_locked(self):
        self._attr_available = True
        self._attr_is_locked = True
        self.async_write_ha_state()
