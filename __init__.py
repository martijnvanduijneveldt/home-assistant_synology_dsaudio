"""The Synology DSM component."""
from __future__ import annotations

from typing import Any

from synology_dsm.exceptions import (
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

from .services import DsAudioServices
from .api.SynoApi import SynoApi
from .const import (
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    EXCEPTION_DETAILS,
    EXCEPTION_UNKNOWN,
    SYNO_API,
)

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
    hass.data[DOMAIN][entry.unique_id] = {
        # UNDO_UPDATE_LISTENER: entry.add_update_listener(_async_update_listener),
        SYNO_API: api,
    }

    # hass.data[DOMAIN]["devices"] = devices

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    # Services
    ds_service = DsAudioServices(hass)
    await ds_service.async_register()

    # For SSDP compat
    if not entry.data.get(CONF_MAC):
        network = await hass.async_add_executor_job(getattr, api.dsm, "network")
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_MAC: network.macs}
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Synology DSM sensors."""

    entry_data = hass.data[DOMAIN][entry.unique_id]
    # entry_data[UNDO_UPDATE_LISTENER]()
    await entry_data[SYNO_API].async_unload()
    hass.data[DOMAIN].pop(entry.unique_id)

    return True


class SynologyDSMBaseEntity(CoordinatorEntity):
    """Representation of a Synology NAS entry."""

    entity_description: EntityDescription
    unique_id: str
    _attr_attribution = ATTRIBUTION

    def __init__(
            self,
            api: SynoApi,
            coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
            description: EntityDescription,
    ) -> None:
        """Initialize the Synology DSM entity."""
        super().__init__(coordinator)
        self.entity_description = description

        self._api = api
        self._attr_name = f"{api.information.model} {description.name}"
        self._attr_unique_id: str = (
            f"{api.information.serial}_{api.information.API_KEY}:{description.key}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._api.information.serial)},
            name="Synology NAS",
            manufacturer="Synology",
            model=self._api.information.model,
            sw_version=self._api.information.version_string,
            configuration_url=self._api.config_url,
        )

    async def async_added_to_hass(self) -> None:
        """Register entity for updates from API."""
        self.async_on_remove(
            self._api.subscribe(self.entity_description.api_key, self.unique_id)
        )
        await super().async_added_to_hass()


