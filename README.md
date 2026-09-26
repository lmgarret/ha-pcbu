
> [!CAUTION]
> This integration is pretty experimental, not all features are implemented nor properly implemented. You may encounter bugs using it.
> 
> Also the disclaimer from [`py-pcbu`](https://github.com/lmgarret/py-pcbu) applies here too!
> PCBU and this library handles your accounts passwords. This project's license includes a NO-LIABILITY disclaimer that I won't repeat here. Please handle your account passwords responsibly!
> And always inspect projects that handle such sensitive data, even if they're FOSS.


# PC Bio Unlock (Unofficial) for Home Assistant

## Installation
Add `https://github.com/lmgarret/ha-pcbu` to HACS as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) of type _Integration_, install _PC Bio Unlock (Unofficial)_, then restart Home Assistant.

## Configuration
1. In the PC Bio Unlock desktop app, start pairing a new device with the TCP method.
2. In Home Assistant, add the _PC Bio Unlock_ integration, and enter the PC's IP address, pairing port and encryption key shown next to the QR code, along with Home Assistant's IP address.

Each paired PC is a lock entity. When the PC asks to be unlocked, the lock becomes available and locked: unlocking it (from the UI, an automation, an actionable notification...) sends the credentials to the PC. The lock becomes unavailable again once used, or if the PC gives up.

If the PC or Home Assistant changes IP address, use _Reconfigure_ on the integration entry: the PC stays paired.

## Development
1. Follow the instructions to setup a Home Assistant development environment [here](https://developers.home-assistant.io/docs/development_environment)
2. Symlink the repository's `custom_components` as the dev HomeAssistant instance's `config/custom_components` directory
3. Run HomeAssistant in debug mode using F5 in VSCode
4. Debug stuff

### Tests and linting
The tests need Python 3.14 and run against the Home Assistant version pinned in `requirements.test.txt`:
```bash
uv venv --python 3.14 && source .venv/bin/activate
uv pip install -r requirements.test.txt
jq -r '.requirements[]' custom_components/pcbu/manifest.json | xargs -d '\n' uv pip install
pytest
```
Linting and formatting use [ruff](https://docs.astral.sh/ruff/), through [pre-commit](https://pre-commit.com/): `pre-commit install`, or `pre-commit run --all-files`.

The CI also validates the integration with [hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) and the [HACS action](https://hacs.xyz/docs/publish/action/).

---

Repository was bootstrapped using [this tutorial](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/)