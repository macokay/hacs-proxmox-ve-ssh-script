"""Button platform for Proxmox VE SSH Script.

Each configured script is represented as a button entity. Pressing the button
establishes an SSH connection to the Proxmox VE host and executes the script.
stdout/stderr and exit codes are logged to the Home Assistant log.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncssh

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SCRIPT_CONTENT,
    CONF_SCRIPT_ID,
    CONF_SCRIPT_NAME,
    CONF_SCRIPTS,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities for each configured script."""
    data: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    scripts: list[dict[str, Any]] = data.get(CONF_SCRIPTS, [])

    async_add_entities(
        ProxmoxSSHScriptButton(entry, script) for script in scripts
    )


class ProxmoxSSHScriptButton(ButtonEntity):
    """Button entity that executes a bash script on a Proxmox VE node via SSH."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, script: dict[str, Any]) -> None:
        """Initialise button from config entry and script definition."""
        self._entry = entry
        self._script = script
        # Unique ID combines config entry (host/user) with the script's UUID
        self._attr_unique_id = f"{entry.entry_id}_{script[CONF_SCRIPT_ID]}"
        self._attr_name = script[CONF_SCRIPT_NAME]

    @property
    def device_info(self) -> dict[str, Any]:
        """Group all buttons under a single device per Proxmox host."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Proxmox VE ({self._entry.data[CONF_HOST]})",
            "manufacturer": "Proxmox",
            "model": "Proxmox VE",
        }

    async def async_press(self) -> None:
        """Open SSH connection and run the script when button is pressed."""
        data = self._entry.data
        host: str = data[CONF_HOST]
        port: int = data[CONF_PORT]
        username: str = data[CONF_USERNAME]
        password: str = data[CONF_PASSWORD]
        script_name: str = self._script[CONF_SCRIPT_NAME]
        script_content: str = self._script[CONF_SCRIPT_CONTENT]

        _LOGGER.debug("Pressing button '%s' — connecting to %s:%d", script_name, host, port)

        try:
            conn = await asyncio.wait_for(
                asyncssh.connect(
                    host,
                    port=port,
                    username=username,
                    password=password,
                    # Skip host key verification — acceptable for local LAN Proxmox hosts
                    known_hosts=None,
                ),
                timeout=DEFAULT_TIMEOUT,
            )

            try:
                result = await asyncio.wait_for(
                    conn.run(script_content),
                    timeout=DEFAULT_TIMEOUT,
                )
            finally:
                conn.close()

            # Log stdout if the script produced any output
            if result.stdout and result.stdout.strip():
                _LOGGER.info(
                    "Script '%s' stdout:\n%s",
                    script_name,
                    result.stdout.strip(),
                )

            # Log stderr as a warning — not necessarily fatal but worth surfacing
            if result.stderr and result.stderr.strip():
                _LOGGER.warning(
                    "Script '%s' stderr:\n%s",
                    script_name,
                    result.stderr.strip(),
                )

            if result.exit_status != 0:
                _LOGGER.error(
                    "Script '%s' exited with non-zero status %d",
                    script_name,
                    result.exit_status,
                )
            else:
                _LOGGER.info("Script '%s' completed successfully (exit 0)", script_name)

        except asyncio.TimeoutError:
            _LOGGER.error(
                "Script '%s' timed out after %d seconds",
                script_name,
                DEFAULT_TIMEOUT,
            )
        except asyncssh.PermissionDenied as err:
            _LOGGER.error(
                "SSH authentication failed for script '%s': %s",
                script_name,
                err,
            )
        except asyncssh.Error as err:
            _LOGGER.error(
                "SSH error running script '%s': %s",
                script_name,
                err,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Unexpected error running script '%s': %s",
                script_name,
                err,
            )
