# ruff: noqa: D103, D102, D107, D101
from collections import defaultdict

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
    def on_valid_unlock_request(self, pairing: PCPairing) -> bool:
        _LOGGER.info(f"Accepted unlock request from {pairing.ip_address}")
        return True

    def on_invalid_unlock_request(self, ip_address: str):
        _LOGGER.info(f"Rejected unlock request from {ip_address}")

    # def on_listen(self):
    #     _LOGGER.info(f"Started listening on port {self.port}")

    # def on_exist(self):
    #     _LOGGER.info(f"Stopped server listening on port {self.port}")

class PCBUnlockServer:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.locks = defaultdict(dict)
        self.servers = {}

    async def add_lock(self, lock: "PCBLock", port: int):
        self.locks[port][lock.conf.desktop_ip_address] = lock
        if port not in self.servers:
            
            async def start_server():
                with TCPUnlockServer(
                    [lock.conf for lock in self.locks[port].values()], port=port
                ) as server:
                    self.servers[port] = server
                    await server.async_listen()

            self.hass.async_create_task(start_server())

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "pcbunlock_server" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["pcbunlock_server"] = PCBUnlockServer(hass)

    pcbunlock_server = hass.data[DOMAIN]["pcbunlock_server"]
    locks = []

    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    lock_conf = PCBLockConfig.from_dict(entry_data)

    lock = PCBLock(lock_conf)
    locks.append(lock)
    await pcbunlock_server.add_lock(lock, lock.conf.server_port)
    async_add_entities(locks)


class PCBLock(LockEntity):
    # _attr_has_entity_name = True

    def __init__(self, conf: PCBLockConfig):
        self.conf = conf

        self._attr_name = conf.remote_info.name
        self._attr_is_locked = False
        self._attr_available = False

        self._attr_unique_id = conf.pairing_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, conf.remote_info.mac_address), (DOMAIN, conf.pairing_id)},
            "name": conf.remote_info.name,
        }

    @property
    def name(self):
        return self.conf.remote_info.name

    async def async_lock(self, **kwargs):
        # Implement lock logic here
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        # Implement unlock logic here
        self._attr_is_locked = False
        self.async_write_ha_state()

    @callback
    def set_available(self, available: bool):
        self._attr_available = available
        self.async_write_ha_state()
