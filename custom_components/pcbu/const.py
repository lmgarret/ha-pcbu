"""Constants for the PC Bio Unlock integration."""

DOMAIN = "pcbu"
CONF_REMOTE_HOST = "remote_host"
CONF_BIND_IP = "bind_ip"
CONF_PAIR_PORT = "pair_port"
CONF_ENCRYPTION_KEY = "encryption_key"

DEFAULT_PAIR_PORT = 43295
# not customizable, see https://github.com/MeisApps/pcbu-desktop/issues/20
UNLOCK_SERVER_PORT = 43298

SOCKET_TIMEOUT = 10
