# ruff: noqa: D103, D102, D107, D101
from dataclasses import dataclass

from dataclass_wizard import JSONWizard
from pcbu.models import PCPairingSecret


@dataclass
class PCBRemoteInfo(JSONWizard):
    name: str
    ip_address: str
    mac_address: str
    os: str

@dataclass
class PCBLockConfig(PCPairingSecret):
    """Model reprensenting all the information needed to unlocka desktop. Contains sensitive fields."""

    encryption_key: str
    server_port: int
    remote_info: PCBRemoteInfo
