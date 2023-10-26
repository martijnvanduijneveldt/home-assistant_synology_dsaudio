from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback

from ..synology_dsm.api.audio_station import SynoAudioStation
from ..synology_dsm import SynologyDSM
from ..synology_dsm.api.dsm.information import SynoDSMInformation
from ..synology_dsm.exceptions import (
    SynologyDSMAPIErrorException,
    SynologyDSMLoginFailedException,
    SynologyDSMRequestException
)

from ..shared import LOGGER
from ..const import CONF_DEVICE_TOKEN


class SynoApi:
    """Class to interface with Synology DSM API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the API wrapper class."""
        self._hass = hass
        self._entry = entry
        if entry.data.get(CONF_SSL):
            self.config_url = f"https://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        else:
            # noinspection HttpUrlsUsage
            self.config_url = f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"

        self.initialized = False
        # DSM APIs
        self.dsm: SynologyDSM | None = None
        self.information: SynoDSMInformation | None = None

        # Should we fetch them
        self._fetching_entities: dict[str, set[str]] = {}
        self._with_information = True

        LOGGER.debug("__name__ = " + __name__)

    async def async_setup(self) -> None:
        """Start interacting with the NAS."""
        self.dsm = SynologyDSM(
            self._entry.data[CONF_HOST],
            self._entry.data[CONF_PORT],
            self._entry.data[CONF_USERNAME],
            self._entry.data[CONF_PASSWORD],
            self._entry.data[CONF_SSL],
            self._entry.data[CONF_VERIFY_SSL],
            timeout=self._entry.options.get(CONF_TIMEOUT),
            device_token=self._entry.data.get(CONF_DEVICE_TOKEN),
        )
        await self._hass.async_add_executor_job(self.dsm.login)

        self._async_setup_api_requests()

        await self._hass.async_add_executor_job(self._fetch_device_configuration)
        await self.async_update()
        self.initialized = True

    @callback
    def subscribe(self, api_key: str, unique_id: str) -> Callable[[], None]:
        """Subscribe an entity to API fetches."""
        LOGGER.debug("Subscribe new entity: %s", unique_id)
        if api_key not in self._fetching_entities:
            self._fetching_entities[api_key] = set()
        self._fetching_entities[api_key].add(unique_id)

        @callback
        def unsubscribe() -> None:
            """Unsubscribe an entity from API fetches (when disable)."""
            LOGGER.debug("Unsubscribe entity: %s", unique_id)
            self._fetching_entities[api_key].remove(unique_id)
            if len(self._fetching_entities[api_key]) == 0:
                self._fetching_entities.pop(api_key)

        return unsubscribe

    @callback
    def _async_setup_api_requests(self) -> None:
        """Determine if we should fetch each API, if one entity needs it."""
        # Entities not added yet, fetch all
        if not self._fetching_entities:
            LOGGER.debug(
                "Entities not added yet, fetch all for '%s'", self._entry.unique_id
            )
            return

    def _fetch_device_configuration(self) -> None:
        """Fetch initial device config."""
        self.information = self.dsm.information

    async def async_unload(self) -> None:
        """Stop interacting with the NAS and prepare for removal from hass."""
        try:
            await self._hass.async_add_executor_job(self.dsm.logout)
        except (SynologyDSMAPIErrorException, SynologyDSMRequestException) as err:
            LOGGER.debug(
                "Logout from '%s' not possible:%s", self._entry.unique_id, err
            )

    async def async_update(self) -> None:
        """Update function for updating API information."""
        LOGGER.debug("Start data update for '%s'", self._entry.unique_id)
        self._async_setup_api_requests()
        try:
            await self._hass.async_add_executor_job(
                self.dsm.update, self._with_information
            )
        except (SynologyDSMLoginFailedException, SynologyDSMRequestException) as err:
            if not self.initialized:
                raise err

            LOGGER.warning(
                "Connection error during update, fallback by reloading the entry"
            )
            LOGGER.debug(
                "Connection error during update of '%s' with exception: %s",
                self._entry.unique_id,
                err,
            )
            await self._hass.config_entries.async_reload(self._entry.entry_id)
            return
