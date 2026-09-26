"""Test the unlock flow."""

import asyncio

from pcbu.crypto import encrypt_aes
from pcbu.models import EncryptedUnlockPayload, PacketUnlockRequest, PCPairingSecret
from pcbu.tcp.common import asend
from pcbu.tcp.unlock_client import TCPUnlockClient
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_LOCKED, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.pcbu.const import DOMAIN
from custom_components.pcbu.models import PCBLockConfig, PCBRemoteInfo

PORT = 43990


def _lock_conf(pairing_id: str) -> PCBLockConfig:
    return PCBLockConfig(
        pairing_id=pairing_id,
        desktop_ip_address="127.0.0.1",
        desktop_os="Linux",
        server_ip_address="127.0.0.1",
        server_port=PORT,
        username=f"user-{pairing_id}",
        password=f"pwd-{pairing_id}",
        encryption_key=f"key-{pairing_id}",
        remote_info=PCBRemoteInfo(
            name=f"desktop {pairing_id}",
            ip_address="127.0.0.1",
            mac_address=f"mac-{pairing_id}",
            os="Linux",
        ),
    )


def _client(conf: PCBLockConfig) -> TCPUnlockClient:
    return TCPUnlockClient(PCPairingSecret.from_dict(conf.to_dict()))


async def _wait_for_state(hass: HomeAssistant, entity_id: str, state: str):
    for _ in range(100):
        await asyncio.sleep(0.05)
        if hass.states.get(entity_id).state == state:
            return
    raise AssertionError(f"{entity_id} never reached {state}")


@pytest.fixture
async def locks(hass: HomeAssistant, socket_enabled):
    """Set up two locks sharing the same unlock server port."""
    confs = [_lock_conf("a"), _lock_conf("b")]
    for conf in confs:
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id=conf.pairing_id, data=conf.to_dict()
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)  # let the unlock server bind
    yield confs

    for entry in hass.config_entries.async_entries(DOMAIN):
        assert await hass.config_entries.async_unload(entry.entry_id)
    # the unlock server is stopped once no lock uses it anymore
    assert hass.data[DOMAIN]["server"].servers == {}


async def test_unlock_the_requesting_desktop(hass: HomeAssistant, locks):
    """Each lock must only answer its own desktop's unlock request."""
    conf_a, conf_b = locks
    assert hass.states.get("lock.desktop_a").state == STATE_UNAVAILABLE

    request_a = asyncio.create_task(_client(conf_a).unlock(timeout=5))
    await _wait_for_state(hass, "lock.desktop_a", STATE_LOCKED)
    request_b = asyncio.create_task(_client(conf_b).unlock(timeout=5))
    await _wait_for_state(hass, "lock.desktop_b", STATE_LOCKED)

    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.desktop_a"}, blocking=True
    )
    assert (await request_a).password == conf_a.password
    assert hass.states.get("lock.desktop_a").state == STATE_UNAVAILABLE
    assert hass.states.get("lock.desktop_b").state == STATE_LOCKED
    assert not request_b.done()

    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.desktop_b"}, blocking=True
    )
    assert (await request_b).password == conf_b.password
    assert hass.states.get("lock.desktop_b").state == STATE_UNAVAILABLE


async def test_dropped_unlock_request(hass: HomeAssistant, locks):
    """The lock becomes unavailable again when the desktop drops its request."""
    conf_a, _ = locks
    reader, writer = await asyncio.open_connection("127.0.0.1", PORT)
    payload = EncryptedUnlockPayload(auth_user=conf_a.username, unlock_token="token")
    request = PacketUnlockRequest(
        pairing_id=conf_a.pairing_id,
        enc_data=encrypt_aes(payload.to_json().encode(), conf_a.encryption_key).hex(),
    )
    await asend(writer, request.to_json().encode())
    await _wait_for_state(hass, "lock.desktop_a", STATE_LOCKED)

    writer.close()
    await _wait_for_state(hass, "lock.desktop_a", STATE_UNAVAILABLE)


async def test_reload_entry(hass: HomeAssistant, locks):
    """Unloading and reloading an entry keeps the other locks working."""
    conf_a, conf_b = locks
    entry_a = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, "a")

    assert await hass.config_entries.async_unload(entry_a.entry_id)
    assert entry_a.state is ConfigEntryState.NOT_LOADED
    await asyncio.sleep(0.1)

    request_b = asyncio.create_task(_client(conf_b).unlock(timeout=5))
    await _wait_for_state(hass, "lock.desktop_b", STATE_LOCKED)
    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.desktop_b"}, blocking=True
    )
    assert (await request_b).password == conf_b.password

    assert await hass.config_entries.async_setup(entry_a.entry_id)
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)

    request_a = asyncio.create_task(_client(conf_a).unlock(timeout=5))
    await _wait_for_state(hass, "lock.desktop_a", STATE_LOCKED)
    await hass.services.async_call(
        "lock", "unlock", {"entity_id": "lock.desktop_a"}, blocking=True
    )
    assert (await request_a).password == conf_a.password


async def test_migrate_entry_without_desktop_os(hass: HomeAssistant, socket_enabled):
    """Entries created before py-pcbu 0.5.0 get their desktop OS from the remote info."""
    data = _lock_conf("a").to_dict()
    del data["desktopOs"]
    data["remoteInfo"]["os"] = "Windows"
    entry = MockConfigEntry(domain=DOMAIN, unique_id="a", data=data, version=1)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data["desktopOs"] == "Windows"
    assert await hass.config_entries.async_unload(entry.entry_id)
