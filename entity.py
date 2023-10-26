"""Entities for Synology DSM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import SynoApi
from .const import DOMAIN


@dataclass
class SynologyDSMRequiredKeysMixin:
    """Mixin for required keys."""

    api_key: str


@dataclass
class SynologyDSMEntityDescription(EntityDescription, SynologyDSMRequiredKeysMixin):
    """Generic Synology DSM entity description."""


class SynologyDSMBaseEntity(
    CoordinatorEntity[DataUpdateCoordinator[dict[str, dict[str, Any]]]]
):
    """Representation of a Synology NAS entry."""

    entity_description: SynologyDSMEntityDescription
    unique_id: str

    def __init__(
        self,
        api: SynoApi,
        coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
        description: SynologyDSMEntityDescription,
    ) -> None:
        """Initialize the Synology DSM entity."""
        super().__init__(coordinator)
        self.entity_description = description

        self._api = api
        self._attr_name = f"{api.network.hostname} {description.name}"
        self._attr_unique_id: str = (
            f"{api.information.serial}_{description.api_key}:{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._api.information.serial)},
            name=self._api.network.hostname,
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


