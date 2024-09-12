"""Config flow for PC Bio Unlock integration."""

from __future__ import annotations

import errno
import logging
from typing import Any

from pcbu.helpers import get_ip, get_uuid
from pcbu.models import PairingQRData
from pcbu.tcp.pair_client import TCPPairClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BIND_IP,
    CONF_ENCRYPTION_KEY,
    CONF_PAIR_PORT,
    CONF_UNLOCK_PORT,
    CONF_REMOTE_HOST,
    DOMAIN,
    SOCKET_TIMEOUT,
)
from .models import PCBLockConfig, PCBRemoteInfo

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_REMOTE_HOST,
            description="The IP address of the desktop to pair with",
            default="192.168.1.100",
        ): str,
        # : vol.All(str, cv.matches_regex(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$")),
        vol.Required(
            CONF_BIND_IP,
            description="The IP address to bind to",
            default=get_ip(),
        ): str,
        # : vol.All(str, cv.matches_regex(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$")),
        vol.Required(
            CONF_PAIR_PORT,
            description="The pairing port (as in the QR code)",
            default=43295,
        ): vol.All(int, cv.port),
        vol.Required(
            CONF_ENCRYPTION_KEY,
            description="The encryption key for secure communication",
        ): str,
        vol.Required(
            CONF_UNLOCK_PORT,
            description="The port to listen on for the pairing/unlocking process",
            default=43296,
        ): vol.All(int, cv.port),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> PCBLockConfig:
    """Validate the user input allows us to pair."""

    pairing_data = PairingQRData(
        ip=data[CONF_REMOTE_HOST],
        port=data[CONF_PAIR_PORT],
        enc_key=data[CONF_ENCRYPTION_KEY],
        method=0,
    )
    machine_uuid: str = await hass.async_add_executor_job(get_uuid)

    _LOGGER.debug("Starting TCPPairClient....")
    client = TCPPairClient(
        pairing_qr_data=pairing_data,
        device_name="Home Assistant",
        machine_uuid=machine_uuid,
    )
    _LOGGER.debug("TCPPairClient started")
    # Return info that you want to store in the config entry.
    _LOGGER.debug("Initiating pairing process")
    response = client.pair(timeout=SOCKET_TIMEOUT)

    _LOGGER.debug("Got a pairing response")
    return PCBLockConfig(
        username=response.user_name,
        password=response.password,
        encryption_key=data[CONF_ENCRYPTION_KEY],
        pairing_id=response.pairing_id,
        desktop_ip_address=data[CONF_REMOTE_HOST],
        server_ip_address=data[CONF_BIND_IP],
        server_port=data[CONF_UNLOCK_PORT],
        remote_info=PCBRemoteInfo(
            name=response.host_name,
            ip_address=data[CONF_REMOTE_HOST],
            mac_address=response.mac_address,
            os=response.hostOS,
        ),
    )


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PC Bio Unlock."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                lock_conf = await validate_input(self.hass, user_input)

            except TimeoutError:
                _LOGGER.exception("Timeout while attempting to pair")
                errors["base"] = "timeout"
            except OSError as e:
                if e.errno == errno.EHOSTUNREACH:
                    errors["base"] = "remote_unreachable"
                else:
                    _LOGGER.exception("Unexpected OSError")
                    errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(lock_conf.pairing_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=lock_conf.remote_info.name, data=lock_conf.to_dict()
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "description": (
                    "Please enter the details to pair with your PC Bio Unlock device. "
                    "They can be found by scanning the QR code displayed by the PC Bio Unlock app on your PC."
                )
            },
        )
