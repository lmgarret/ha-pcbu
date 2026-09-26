from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from pcbu.models import PCBUModel, PCPairingSecret


@dataclass
class PCBRemoteInfo(PCBUModel):
    name: str
    ip_address: str
    mac_address: str
    os: str


@dataclass
class PCBLockConfig(PCPairingSecret):
    """All the information needed to unlock a desktop. Contains sensitive fields."""

    encryption_key: str
    server_port: int
    remote_info: PCBRemoteInfo


type PCBUConfigEntry = ConfigEntry[PCBLockConfig]
