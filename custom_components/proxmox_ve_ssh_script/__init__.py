"""Proxmox VE SSH Script integration for Home Assistant.

Allows running bash scripts on a Proxmox VE node via SSH.
Each configured script is exposed as a button entity in Home Assistant.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxmox VE SSH Script from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Merge data (connection info) and options (scripts) for easy access
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload integration when options are updated so button entities reflect changes
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
