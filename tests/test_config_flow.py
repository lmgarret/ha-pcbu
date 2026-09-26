"""Test the config flow."""

import errno
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pcbu.errors import PairingError
from pcbu.models import PacketPairResponse, PairingMethod
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pcbu.const import DOMAIN
from custom_components.pcbu.models import PCBLockConfig

USER_INPUT = {
    "remote_host": "192.168.1.10",
    "bind_ip": "192.168.1.2",
    "pair_port": 43295,
    "encryption_key": "key",
}

RESPONSE = PacketPairResponse(
    err_msg="",
    pairing_id="pairing",
    pairing_method=PairingMethod.TCP,
    host_name="desktop",
    host_os="Windows",
    host_address="192.168.1.10",
    host_port=43296,
    mac_address="AA:BB:CC:DD:EE:FF",
    user_name="user",
    password="pwd",
)


@pytest.fixture(autouse=True)
def mock_helpers():
    with (
        patch("custom_components.pcbu.config_flow.get_uuid", return_value="uuid"),
        patch("custom_components.pcbu.config_flow.get_ip", return_value="192.168.1.2"),
        patch("custom_components.pcbu.async_setup_entry", return_value=True),
    ):
        yield


def mock_pair(**kwargs):
    return patch(
        "custom_components.pcbu.config_flow.TCPPairClient.pair",
        AsyncMock(**kwargs),
    )


async def test_pair(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with mock_pair(return_value=RESPONSE) as pair:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "desktop"
    assert result["result"].unique_id == "pairing"
    pair.assert_awaited_once()

    conf = PCBLockConfig.from_dict(result["data"])
    assert conf.desktop_ip_address == "192.168.1.10"
    assert conf.server_ip_address == "192.168.1.2"
    assert conf.server_port == 43298
    assert conf.desktop_os == "Windows"
    assert conf.username == "user"
    assert conf.password == "pwd"
    assert conf.remote_info.mac_address == "AA:BB:CC:DD:EE:FF"


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (TimeoutError, "timeout"),
        (PairingError("refused"), "pairing_refused"),
        (OSError(errno.EHOSTUNREACH, "unreachable"), "remote_unreachable"),
        (OSError(errno.ECONNREFUSED, "refused"), "remote_unreachable"),
        (OSError(errno.EACCES, "denied"), "unknown"),
        (ValueError, "unknown"),
    ],
)
async def test_pair_errors(hass: HomeAssistant, side_effect, error):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with mock_pair(side_effect=side_effect):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # the user can retry
    with mock_pair(return_value=RESPONSE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_invalid_ip(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with mock_pair(return_value=RESPONSE) as pair:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, "remote_host": "not an ip"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"remote_host": "invalid_ip"}
    pair.assert_not_awaited()


async def test_already_configured(hass: HomeAssistant):
    MockConfigEntry(domain=DOMAIN, unique_id="pairing").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with mock_pair(return_value=RESPONSE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(hass: HomeAssistant):
    with mock_pair(return_value=RESPONSE):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
    entry = result["result"]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"remote_host": "bad", "bind_ip": "192.168.1.3"}
    )
    assert result["errors"] == {"remote_host": "invalid_ip"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"remote_host": "192.168.1.20", "bind_ip": "192.168.1.3"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    conf = PCBLockConfig.from_dict(entry.data)
    assert conf.desktop_ip_address == "192.168.1.20"
    assert conf.remote_info.ip_address == "192.168.1.20"
    assert conf.server_ip_address == "192.168.1.3"
    # the pairing is kept
    assert conf.pairing_id == "pairing"
    assert conf.password == "pwd"
