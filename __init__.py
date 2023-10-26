"""The Synology DSM component."""
from __future__ import annotations

from itertools import chain
from typing import Any

from homeassistant.helpers.device_registry import DeviceEntry

from .synology_dsm.exceptions import (
    SynologyDSMLogin2SARequiredException,
    SynologyDSMLoginDisabledAccountException,
    SynologyDSMLoginFailedException,
    SynologyDSMLoginInvalidException,
    SynologyDSMLoginPermissionDeniedException,
    SynologyDSMRequestException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    CONF_VERIFY_SSL, Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api.SynoApi import SynoApi
from .const import (
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    EXCEPTION_DETAILS,
    EXCEPTION_UNKNOWN,
    SYNO_API,
)
from .services import async_setup_services

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)

ATTRIBUTION = "Data provided by Synology"

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Synology DSM sensors."""

    # Migrate existing entry configuration
    if entry.data.get(CONF_VERIFY_SSL) is None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_VERIFY_SSL: DEFAULT_VERIFY_SSL}
        )

    # Continue setup
    api = SynoApi(hass, entry)
    try:
        await api.async_setup()
    except (
            SynologyDSMLogin2SARequiredException,
            SynologyDSMLoginDisabledAccountException,
            SynologyDSMLoginInvalidException,
            SynologyDSMLoginPermissionDeniedException,
    ) as err:
        if err.args[0] and isinstance(err.args[0], dict):
            # pylint: disable=no-member
            details = err.args[0].get(EXCEPTION_DETAILS, EXCEPTION_UNKNOWN)
        else:
            details = EXCEPTION_UNKNOWN
        raise ConfigEntryAuthFailed(f"reason: {details}") from err
    except (SynologyDSMLoginFailedException, SynologyDSMRequestException) as err:
        if err.args[0] and isinstance(err.args[0], dict):
            # pylint: disable=no-member
            details = err.args[0].get(EXCEPTION_DETAILS, EXCEPTION_UNKNOWN)
        else:
            details = EXCEPTION_UNKNOWN
        raise ConfigEntryNotReady(details) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        SYNO_API: api,
    }

    # hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


    # Services
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
        hass: HomeAssistant, entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove synology_dsm config entry from a device."""
    api: SynoApi = hass.data[DOMAIN][entry.entry_id].SYNO_API
    serial = api.information.serial

    current = await hass.async_add_executor_job(api.dsm.audio_station.remote_player_get_players)

    device_ids = chain(
        (player.id for player in current),
    )

    return not device_entry.identifiers.intersection(
        (
            (DOMAIN, serial),  # Base device
            *((DOMAIN, f"{serial}_{id}") for id in device_ids),  # Storage and cameras
        )
    )

