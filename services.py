from typing import Optional

import voluptuous as vol

from homeassistant.core import ServiceCall, callback
from .synology_dsm import SynologyDSM

from . import const
from .synology_dsm.api.audio_station import SynoAudioStation, SongSortMode, RemotePlayerAction, QueueMode
from .shared import LOGGER

nasByIdSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
    }
),

playerByUuidSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
    }
)

playerUpdateSongsSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
        vol.Required(const.SERVICE_INPUT_SONGS): str,
    }
)

playerArtistSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
        vol.Required(const.SERVICE_INPUT_ARTIST): str,
    }
)

playerAlbumSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
        vol.Required(const.SERVICE_INPUT_ALBUM_NAME): str,
        vol.Required(const.SERVICE_INPUT_ALBUM_ARTIST): str,
    }
)

playerVolumeSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
        vol.Required(const.SERVICE_INPUT_VOLUME): int,
    }
)

playerPlayerControlSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYERUUID): str,
        vol.Required(const.SERVICE_INPUT_ACTION): str,
    }
)


class DsAudioServices:
    """Class that holds our services that should be published to hass."""

    def __init__(self, hass):
        """Initialize with hass """
        self._hass = hass

    @callback
    async def async_register(self):
        """Register all our services."""
        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_GETPLAYER_STATUS,
            self.get_player_status,
            playerByUuidSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_GETPLAYERS,
            self.get_players,
            nasByIdSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAY_SONGS,
            self.remote_update_play_songs,
            playerUpdateSongsSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAY_ARTIST,
            self.remote_update_play_artist,
            playerArtistSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAY_ALBUM,
            self.remote_update_play_album,
            playerAlbumSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAYER_CONTROL,
            self.remote_player_control,
            playerPlayerControlSchema
        )

        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAYER_VOLUME,
            self.remote_player_volume,
            playerVolumeSchema
        )
        
        self._hass.services.async_register(
            const.DOMAIN,
            const.SERVICE_FUNC_REMOTE_PLAYER_CLEAR_PLAYLIST,
            self.remote_player_clear_playlist,
            playerByUuidSchema
        )

    def __resolve_dsm(self, call: ServiceCall) -> Optional[SynologyDSM]:
        serial = call.data.get(const.CONF_SERIAL)
        dsm_devices = self._hass.data[const.DOMAIN]

        if serial:
            dsm_device = dsm_devices.get(serial)
        elif len(dsm_devices) == 1:
            dsm_device = next(iter(dsm_devices.values()))
            serial = next(iter(dsm_devices))
        else:
            LOGGER.error(
                "More than one DSM configured, must specify one of serials %s",
                sorted(dsm_devices),
            )
            return

        if not dsm_device:
            LOGGER.error("DSM with specified serial %s not found", serial)
            return

        syno_api = dsm_device[const.SYNO_API]
        return syno_api.dsm

    def __resolve_audio_station(self, call: ServiceCall) -> Optional[SynoAudioStation]:
        dsm_api = self.__resolve_dsm(call)
        if not dsm_api:
            return None

        return SynoAudioStation(dsm_api)

    async def get_player_status(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        res = await self._hass.async_add_executor_job(audio.get_player_status, player_uuid)
        LOGGER.info(res)

    async def get_players(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        res = await self._hass.async_add_executor_job(audio.get_players)
        LOGGER.info(res)

    async def remote_update_play_songs(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        songs = call.data.get(const.SERVICE_INPUT_SONGS)
        mode = QueueMode.replace
        play_directly = True

        res = await self._hass.async_add_executor_job(audio.remote_player_play_songs, player_uuid, songs, mode,
                                                      play_directly)
        LOGGER.info(res)

    async def remote_update_play_artist(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        artist = call.data.get(const.SERVICE_INPUT_ARTIST)
        mode = QueueMode.replace
        play_directly = True

        res = await self._hass.async_add_executor_job(audio.remote_player_play_artist, player_uuid, artist,
                                                      SongSortMode.album, mode, play_directly)
        LOGGER.info(res)

    async def remote_update_play_album(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        album_artist = call.data.get(const.SERVICE_INPUT_ALBUM_ARTIST)
        album_name = call.data.get(const.SERVICE_INPUT_ALBUM_NAME)

        mode = QueueMode.replace
        play_directly = True

        res = await self._hass.async_add_executor_job(audio.remote_player_play_album, player_uuid, album_name,
                                                      album_artist, SongSortMode.track, mode, play_directly)
        LOGGER.info(res)

    async def remote_player_control(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        action = RemotePlayerAction(call.data.get(const.SERVICE_INPUT_ACTION))

        res = await self._hass.async_add_executor_job(audio.remote_player_control, player_uuid, action)
        LOGGER.info(res)

    async def remote_player_volume(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)
        volume = call.data.get(const.SERVICE_INPUT_VOLUME)
        res = await self._hass.async_add_executor_job(audio.remote_player_volume, player_uuid, volume)
        LOGGER.info(res)

    async def remote_player_clear_playlist(self, call: ServiceCall) -> None:
        audio = self.__resolve_audio_station(call)
        if not audio:
            return

        player_uuid = call.data.get(const.SERVICE_INPUT_PLAYERUUID)

        res = await self._hass.async_add_executor_job(audio.remote_player_clear_playlist, player_uuid)
        LOGGER.info(res)
