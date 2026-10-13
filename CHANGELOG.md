# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Repair issue when an entry's Home Assistant IP address is not on this host anymore (e.g. Home Assistant moved), pointing to Reconfigure. The entry then fails to set up and retries, instead of showing a lock that can never be unlocked
- Pairing the same user of the same PC again replaces its previous pairing, instead of adding a duplicate entry. Other users of the same PC are still paired separately

### Changed
- Requires py-pcbu 0.9.0: an address that cannot be bound no longer prevents the other entries from unlocking, and rejected unlock requests log why

### Fixed
- Adding a lock failed when the unlock server of its port had previously failed to start

## [0.3.1] - 2026-10-13
### Added
- Dedicated config flow error when the clocks of Home Assistant and the PC differ too much to pair, instead of "Unexpected error"

### Changed
- Requires py-pcbu 0.8.0, which accepts clocks up to 2 minutes apart instead of 20 seconds, as the desktop does

## [0.3.0] - 2026-09-26
### Added
- Reconfigure step, to update the PC and Home Assistant IP addresses without pairing again
- Diagnostics, with the password, encryption key and username redacted
- IP address validation in the config flow, and a dedicated error when the PC refuses the pairing
- Descriptions of the config flow fields, translated error messages when unlocking fails
- CI running ruff, the tests against Home Assistant 2026.9, hassfest and the HACS validation
- Dependabot for GitHub Actions and the test requirements
- `issue_tracker` and `loggers` in the manifest, minimum Home Assistant version in `hacs.json`

### Changed
- Requires py-pcbu 0.7.0 (dataclass-wizard 1.x) and Home Assistant 2025.2 or newer
- The lock entity is named after its device (`has_entity_name`), and the device shows the PC's OS as model
- Config entries keep their parsed config in `runtime_data`, and the unlock server moved to its own module
- The pairing tells the PC Home Assistant's configured IP address instead of a guessed one
- Tooling: `pyproject.toml` with ruff replaces `setup.cfg` (flake8, isort, mypy for Python 3.7), and pre-commit hooks are updated

### Fixed
- Reloading an entry while its PC waited for an unlock hung (py-pcbu 0.7.0)
- hassfest errors: manifest keys order, missing `CONFIG_SCHEMA`

## [0.2.1] - 2026-09-26
### Fixed
- The integration failed to load on fresh installs, which pulled dataclass-wizard 1.0: it is now limited to `<1`

## [0.2.0] - 2026-09-26
### Changed
- Requires py-pcbu 0.6.0

### Fixed
- With several paired desktops, unlocking a lock sent the credentials to the last paired desktop instead
- Desktops sharing the same IP address overwrote each other's lock
- Locks now become unavailable when the desktop drops its unlock request
- A failed unlock now raises an error and resets the lock instead of silently leaving it available
- Unloading or reloading an entry: lock entities were not removed and the unlock server could fail to restart
- The unlock server is stopped when no lock uses it anymore
- Entries created with 0.1.2 or older failing to load since 0.1.3 (missing desktop OS)
- The bind IP default in the config flow was computed once, when the module was imported

## [0.1.3] - 2024-11-19
### Fixed
- Windows changing username case when cold booting (py-pcbu 0.5.0)

## [0.1.2] - 2024-10-14
### Fixed
- Unlock port default value wrong, and should not be changed

## [0.1.1] - 2024-10-14
### Fixed
- Documentation link

## [0.1.0] - 2024-10-14
### Added
- First commit

[0.3.1]: https://github.com/lmgarret/ha-pcbu/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/lmgarret/ha-pcbu/compare/0.2.1...0.3.0
[0.2.1]: https://github.com/lmgarret/ha-pcbu/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/lmgarret/ha-pcbu/compare/0.1.3...0.2.0
[0.1.3]: https://github.com/lmgarret/ha-pcbu/compare/0.1.2...0.1.3
[0.1.2]: https://github.com/lmgarret/ha-pcbu/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/lmgarret/ha-pcbu/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/lmgarret/ha-pcbu/compare/2934012e963020758d868caa083225b350a5ed7a...0.1.0
