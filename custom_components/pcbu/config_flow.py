"""Config flow for PC Bio Unlock integration."""

from __future__ import annotations

import errno
import ipaddress
import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pcbu.errors import PairingError
from pcbu.helpers import get_ip, get_uuid
from pcbu.models import PairingQRData
from pcbu.tcp.pair_client import TCPPairClient
import voluptuous as vol

from .const import (
    CONF_BIND_IP,
    CONF_ENCRYPTION_KEY,
    CONF_PAIR_PORT,
    CONF_REMOTE_HOST,
    DEFAULT_PAIR_PORT,
    DOMAIN,
    SOCKET_TIMEOUT,
    UNLOCK_SERVER_PORT,
)
from .models import PCBLockConfig, PCBRemoteInfo

_LOGGER = logging.getLogger(__name__)

UNREACHABLE_ERRNOS = {errno.EHOSTUNREACH, errno.ENETUNREACH, errno.ECONNREFUSED}

IP_ADDRESSES_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REMOTE_HOST): TextSelector(),
        vol.Required(CONF_BIND_IP): TextSelector(),
    }
)

USER_SCHEMA = IP_ADDRESSES_SCHEMA.extend(
    {
        vol.Required(CONF_PAIR_PORT, default=DEFAULT_PAIR_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_ENCRYPTION_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


def validate_ip_addresses(user_input: dict[str, Any]) -> dict[str, str]:
    """Return the errors of the IP address fields."""
    errors = {}
    for key in (CONF_REMOTE_HOST, CONF_BIND_IP):
        try:
            ipaddress.ip_address(user_input[key])
        except ValueError:
            errors[key] = "invalid_ip"
    return errors


async def pair(hass: HomeAssistant, data: dict[str, Any]) -> PCBLockConfig:
    """Pair with the desktop, returning the lock's config."""
    pairing_data = PairingQRData(
        ip=data[CONF_REMOTE_HOST],
        port=int(data[CONF_PAIR_PORT]),
        enc_key=data[CONF_ENCRYPTION_KEY],
        method=0,
    )
    machine_uuid: str = await hass.async_add_executor_job(get_uuid)
    client = TCPPairClient(
        pairing_qr_data=pairing_data,
        device_name="Home Assistant",
        ip_address=data[CONF_BIND_IP],
        machine_uuid=machine_uuid,
    )
    _LOGGER.debug("Pairing with %s", data[CONF_REMOTE_HOST])
    response = await client.pair(timeout=SOCKET_TIMEOUT)

    return PCBLockConfig(
        username=response.user_name,
        password=response.password,
        encryption_key=data[CONF_ENCRYPTION_KEY],
        pairing_id=response.pairing_id,
        desktop_ip_address=data[CONF_REMOTE_HOST],
        desktop_os=response.host_os,
        server_ip_address=data[CONF_BIND_IP],
        server_port=UNLOCK_SERVER_PORT,
        remote_info=PCBRemoteInfo(
            name=response.host_name,
            ip_address=data[CONF_REMOTE_HOST],
            mac_address=response.mac_address,
            os=response.host_os,
        ),
    )


class PCBUConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PC Bio Unlock."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pair with a desktop."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_ip_addresses(user_input)
        if user_input is not None and not errors:
            try:
                lock_conf = await pair(self.hass, user_input)
            except TimeoutError:
                errors["base"] = "timeout"
            except PairingError as err:
                _LOGGER.warning("Pairing refused: %s", err)
                errors["base"] = "pairing_refused"
            except OSError as err:
                if err.errno in UNREACHABLE_ERRNOS:
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

        suggested = user_input or {
            CONF_BIND_IP: await self.hass.async_add_executor_job(get_ip)
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, suggested),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the IP addresses of a paired desktop and Home Assistant."""
        entry = self._get_reconfigure_entry()
        conf = PCBLockConfig.from_dict(entry.data)
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_ip_addresses(user_input)
            if not errors:
                conf.desktop_ip_address = user_input[CONF_REMOTE_HOST]
                conf.remote_info.ip_address = user_input[CONF_REMOTE_HOST]
                conf.server_ip_address = user_input[CONF_BIND_IP]
                return self.async_update_reload_and_abort(entry, data=conf.to_dict())

        suggested = user_input or {
            CONF_REMOTE_HOST: conf.desktop_ip_address,
            CONF_BIND_IP: conf.server_ip_address,
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                IP_ADDRESSES_SCHEMA, suggested
            ),
            errors=errors,
        )
