"""Unlock server, shared by all the locks listening on the same port."""

from __future__ import annotations

import asyncio
from collections import defaultdict
import contextlib
import functools
import logging
from typing import TYPE_CHECKING, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey
from pcbu.models import PCPairing
from pcbu.tcp.unlock_server import TCPUnlockServerBase

from .const import DOMAIN

if TYPE_CHECKING:
    from .lock import PCBLock

_LOGGER = logging.getLogger(__name__)


class TCPUnlockServer(TCPUnlockServerBase):
    """Implementation of py-pcbu's TCPUnlockServerBase: an incoming unlock request
    makes the matching lock available, and unlocking it answers the request."""

    def __init__(self, locks: list[PCBLock]) -> None:
        self.locks = list(locks)
        super().__init__([lock.conf for lock in self.locks])
        for lock in self.locks:
            # bind each lock's own conf, a closure would capture the loop variable
            lock.unlock_cb = functools.partial(self.unlock, lock.conf)

    def get_lock(self, pairing: PCPairing) -> PCBLock:
        for lock in self.locks:
            if lock.conf.pairing_id == pairing.pairing_id:
                return lock
        raise ValueError(
            f"Could not find matching lock for pairing id {pairing.pairing_id}"
        )

    async def on_valid_unlock_request(self, pairing: PCPairing) -> None:
        """See TCPUnlockServerBase.on_valid_unlock_request."""
        _LOGGER.info("Accepted unlock request from %s", pairing.desktop_ip_address)
        self.get_lock(pairing).set_available_and_locked()

    async def on_invalid_unlock_request(self, ip: str) -> None:
        """See TCPUnlockServerBase.on_invalid_unlock_request."""
        _LOGGER.info("Rejected unlock request from %s", ip)

    async def on_unlock_request_cancelled(self, pairing: PCPairing) -> None:
        """See TCPUnlockServerBase.on_unlock_request_cancelled."""
        _LOGGER.info("Unlock request from %s was dropped", pairing.desktop_ip_address)
        self.get_lock(pairing).set_unavailable()


class TCPServerRuntime(TypedDict):
    """A running TCPUnlockServer alongside its Home Assistant task."""

    server: TCPUnlockServer
    task: asyncio.Task


class PCBUnlockServer:
    """Runs one TCPUnlockServer per port, restarted whenever its locks change."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.locks: defaultdict[int, dict[str, PCBLock]] = defaultdict(dict)
        self.servers: dict[int, TCPServerRuntime] = {}
        # serializes server restarts, as they share the same port
        self._refresh_lock = asyncio.Lock()

    async def _refresh_tcp_server(self, port: int, new_locks: list[PCBLock]) -> None:
        """Restart the server of a port with the given locks."""
        if port in self.servers:
            server = self.servers[port]["server"]
            task = self.servers[port]["task"]

            _LOGGER.info("Stopping server (:%s) (%s locks)...", port, len(server.locks))
            task.cancel()
            # wait for the port to be released before binding it again
            with contextlib.suppress(asyncio.CancelledError):
                await task
            del self.servers[port]

        if not new_locks:
            return

        async def _start_tcp_server(server: TCPUnlockServer) -> None:
            async with server:
                await server.start()

        new_server = TCPUnlockServer(locks=new_locks)
        task = self.hass.async_create_background_task(
            _start_tcp_server(new_server), name=f"PCBUnlock Server (:{port})"
        )
        self.servers[port] = {"server": new_server, "task": task}

    def get_server(self, lock: PCBLock) -> TCPUnlockServer | None:
        """The server the lock is registered on, if running."""
        runtime = self.servers.get(lock.conf.server_port)
        return runtime["server"] if runtime else None

    async def add_lock(self, lock: PCBLock) -> None:
        async with self._refresh_lock:
            port = lock.conf.server_port
            self.locks[port][lock.conf.pairing_id] = lock
            await self._refresh_tcp_server(port, list(self.locks[port].values()))

    async def remove_lock(self, lock: PCBLock) -> None:
        async with self._refresh_lock:
            port = lock.conf.server_port
            self.locks[port].pop(lock.conf.pairing_id, None)
            await self._refresh_tcp_server(port, list(self.locks[port].values()))


DATA_SERVER: HassKey[PCBUnlockServer] = HassKey(DOMAIN)
