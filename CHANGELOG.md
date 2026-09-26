# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.2.1]: https://github.com/lmgarret/ha-pcbu/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/lmgarret/ha-pcbu/compare/0.1.3...0.2.0
[0.1.3]: https://github.com/lmgarret/ha-pcbu/compare/0.1.2...0.1.3
[0.1.2]: https://github.com/lmgarret/ha-pcbu/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/lmgarret/ha-pcbu/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/lmgarret/ha-pcbu/compare/2934012e963020758d868caa083225b350a5ed7a...0.1.0
