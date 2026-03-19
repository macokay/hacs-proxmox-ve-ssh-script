"""Config flow for Proxmox VE SSH Script.

Setup flow:
  1. User enters host, port, username, password.
  2. Integration tests the SSH connection before creating the entry.

Options flow (post-setup):
  - Menu: Add script / Remove script / Save and close
  - Scripts are stored in config entry options as a list of dicts.
  - Adding/removing a script reloads the integration to sync button entities.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import asyncssh
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_SCRIPT_CONTENT,
    CONF_SCRIPT_ID,
    CONF_SCRIPT_NAME,
    CONF_SCRIPTS,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _test_ssh_connection(
    host: str, port: int, username: str, password: str
) -> str | None:
    """Attempt an SSH connection and return an error key, or None on success."""
    try:
        conn = await asyncio.wait_for(
            asyncssh.connect(
                host,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
            ),
            timeout=10,
        )
        conn.close()
        return None
    except asyncio.TimeoutError:
        return "cannot_connect"
    except asyncssh.PermissionDenied:
        return "invalid_auth"
    except (asyncssh.Error, OSError):
        return "cannot_connect"
    except Exception:  # pylint: disable=broad-except
        return "unknown"


class ProxmoxVESSHScriptConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for Proxmox VE SSH Script."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show connection form and validate SSH credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _test_ssh_connection(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            if error:
                errors["base"] = error
            else:
                # Prevent duplicate entries for the same host+port+user combination
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_USERNAME]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                    options={CONF_SCRIPTS: []},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_USERNAME): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return ProxmoxVESSHScriptOptionsFlow(config_entry)


class ProxmoxVESSHScriptOptionsFlow(OptionsFlow):
    """Handle options flow for adding and removing scripts."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise with current list of scripts from options."""
        # Work on a mutable copy — only persisted when user selects "Save and close"
        self._scripts: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_SCRIPTS, [])
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the main options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_script", "remove_script", "finish"],
        )

    async def async_step_add_script(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Form to add a new script."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_SCRIPT_NAME, "").strip()
            content = user_input.get(CONF_SCRIPT_CONTENT, "").strip()

            if not name:
                errors[CONF_SCRIPT_NAME] = "empty_name"
            elif not content:
                errors[CONF_SCRIPT_CONTENT] = "empty_content"
            else:
                self._scripts.append(
                    {
                        CONF_SCRIPT_ID: str(uuid.uuid4()),
                        CONF_SCRIPT_NAME: name,
                        CONF_SCRIPT_CONTENT: content,
                    }
                )
                _LOGGER.debug("Added script '%s'", name)
                # Return to menu after adding
                return await self.async_step_init()

        return self.async_show_form(
            step_id="add_script",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCRIPT_NAME): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    # Multiline textarea so multi-line bash scripts are comfortable to write
                    vol.Required(CONF_SCRIPT_CONTENT): TextSelector(
                        TextSelectorConfig(multiline=True)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_script(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Form to select and remove an existing script."""
        # If there are no scripts yet, skip straight back to the menu
        if not self._scripts:
            return await self.async_step_init()

        if user_input is not None:
            script_id = user_input.get(CONF_SCRIPT_ID)
            removed = [s[CONF_SCRIPT_NAME] for s in self._scripts if s[CONF_SCRIPT_ID] == script_id]
            self._scripts = [s for s in self._scripts if s[CONF_SCRIPT_ID] != script_id]
            if removed:
                _LOGGER.debug("Removed script '%s'", removed[0])
            return await self.async_step_init()

        select_options = [
            SelectOptionDict(value=s[CONF_SCRIPT_ID], label=s[CONF_SCRIPT_NAME])
            for s in self._scripts
        ]

        return self.async_show_form(
            step_id="remove_script",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCRIPT_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=select_options,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Persist the current script list and close the options flow."""
        return self.async_create_entry(
            title="",
            data={CONF_SCRIPTS: self._scripts},
        )
