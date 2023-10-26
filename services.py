import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import ServiceCall, callback, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
)
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.util.read_only_dict import ReadOnlyDict

from . import const
from .api.SynoApi import SynoApi
from .shared import LOGGER
from .synology_dsm.api.audio_station import SynoAudioStation, SongSortMode, RemotePlayerAction, Player
from .synology_dsm.api.audio_station.models.queue_mode import QueueMode

nasByIdSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
    }
)

playerByUuidSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
    }
)

playerUpdateSongsSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_SONGS): str,
    }
)

playerArtistSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_ARTIST): str,
    }
)

playerAlbumSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_ALBUM_NAME): str,
        vol.Required(const.SERVICE_INPUT_ALBUM_ARTIST): str,
    }
)

playerVolumeSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_VOLUME): int,
    }
)

playerShuffleSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_SHUFFLE): bool,
    }
)

playerPlayerControlSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_ACTION): str,
    }
)

playerJumpToSongSchema = vol.Schema(
    {
        vol.Optional(const.CONF_SERIAL): str,
        vol.Required(const.SERVICE_INPUT_PLAYER_ID): cv.entity_domain("media_player"),
        vol.Required(const.SERVICE_INPUT_POSITION): str,
    }
)

SERVICE_RECONNECT_CLIENT = "reconnect_client"
SERVICE_REMOVE_CLIENTS = "remove_clients"

SERVICE_RECONNECT_CLIENT_SCHEMA = vol.All(
    vol.Schema({vol.Required(ATTR_DEVICE_ID): str})
)

SUPPORTED_SERVICES = (
    const.SERVICE_FUNC_GETPLAYER_STATUS,
    const.SERVICE_FUNC_GETPLAYERS,
    const.SERVICE_FUNC_REMOTE_PLAY_SONGS,
    const.SERVICE_FUNC_REMOTE_PLAY_ARTIST,
    const.SERVICE_FUNC_REMOTE_PLAY_ALBUM,
    const.SERVICE_FUNC_REMOTE_PLAYER_CONTROL,
    const.SERVICE_FUNC_REMOTE_PLAYER_JUMP_TO_SONG,
    const.SERVICE_FUNC_REMOTE_PLAYER_VOLUME,
    const.SERVICE_FUNC_REMOTE_SHUFFLE,
    const.SERVICE_FUNC_REMOTE_PLAYER_CLEAR_PLAYLIST,
)

SERVICE_TO_SCHEMA = {
    const.SERVICE_FUNC_GETPLAYER_STATUS: playerByUuidSchema,
    const.SERVICE_FUNC_GETPLAYERS: nasByIdSchema,
    const.SERVICE_FUNC_REMOTE_PLAY_SONGS: playerUpdateSongsSchema,
    const.SERVICE_FUNC_REMOTE_PLAY_ARTIST: playerArtistSchema,
    const.SERVICE_FUNC_REMOTE_PLAY_ALBUM: playerAlbumSchema,
    const.SERVICE_FUNC_REMOTE_PLAYER_CONTROL: playerPlayerControlSchema,
    const.SERVICE_FUNC_REMOTE_PLAYER_JUMP_TO_SONG: playerJumpToSongSchema,
    const.SERVICE_FUNC_REMOTE_PLAYER_VOLUME: playerVolumeSchema,
    const.SERVICE_FUNC_REMOTE_SHUFFLE: playerShuffleSchema,
    const.SERVICE_FUNC_REMOTE_PLAYER_CLEAR_PLAYLIST: playerByUuidSchema,
}


def get_entity_config(
        hass: HomeAssistant, config_entry_id: str
) -> SynoApi | None:
    """Find the SynologyDSM instance for the config entry id."""
    domain_data = hass.data[const.DOMAIN]
    if config_entry_id in domain_data:
        return domain_data[config_entry_id][const.SYNO_API]
    return None


@callback
def _get_dsm_instance_for_entity(hass: HomeAssistant, entity_entry: RegistryEntry) -> SynoApi:
    if not (dsm := get_entity_config(hass, entity_entry.config_entry_id)):
        raise HomeAssistantError(
            f"No config found for entity: {entity_entry.id}, config {entity_entry.config_entry_id}")

    return dsm


@callback
def _get_entity_by_player_id(hass: HomeAssistant, entity_id: str) -> RegistryEntry:
    entity_registry = er.async_get(hass)
    if not (entity_entry := entity_registry.async_get(entity_id)):
        raise HomeAssistantError(f"No entity found for id: {entity_id}")

    return entity_entry


@callback
async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for integration."""

    dsm_services = {
        const.SERVICE_FUNC_GETPLAYERS: get_players,
    }

    media_player_services = {
        const.SERVICE_FUNC_GETPLAYER_STATUS: get_player_status,
        const.SERVICE_FUNC_REMOTE_PLAY_SONGS: remote_update_play_songs,
        const.SERVICE_FUNC_REMOTE_PLAY_ARTIST: remote_update_play_artist,
        const.SERVICE_FUNC_REMOTE_PLAY_ALBUM: remote_update_play_album,
        const.SERVICE_FUNC_REMOTE_PLAYER_CONTROL: remote_player_control,
        const.SERVICE_FUNC_REMOTE_PLAYER_JUMP_TO_SONG: remote_player_jump_to_song,
        const.SERVICE_FUNC_REMOTE_PLAYER_VOLUME: remote_player_volume,
        const.SERVICE_FUNC_REMOTE_SHUFFLE: remote_player_shuffle,
        const.SERVICE_FUNC_REMOTE_PLAYER_CLEAR_PLAYLIST: remote_player_clear_playlist,
    }

    async def async_call_syno_service(service_call: ServiceCall) -> None:
        """Call correct DSM service."""

        # call with a media player
        ha_player_id = service_call.data.get(const.SERVICE_INPUT_PLAYER_ID)

        entity = _get_entity_by_player_id(hass, ha_player_id)
        syno_api = _get_dsm_instance_for_entity(hass, entity)

        audio_station = syno_api.dsm.audio_station

        dsm_player_id = entity.unique_id

        res = await hass.async_add_executor_job(
            media_player_services[service_call.service], audio_station, dsm_player_id, service_call.data)

        LOGGER.info(res)

    for service in SUPPORTED_SERVICES:
        hass.services.async_register(
            const.DOMAIN,
            service,
            async_call_syno_service,
            schema=SERVICE_TO_SCHEMA[service],
        )


@callback
def async_unload_services(hass) -> None:
    """Unload UniFi Network services."""
    for service in SUPPORTED_SERVICES:
        hass.services.async_remove(const.DOMAIN, service)


async def get_players(audio_station: SynoAudioStation, data: ReadOnlyDict) -> list[Player]:
    return audio_station.remote_player_get_players()


def get_player_status(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> None:
    return audio_station.remote_player_get_player_status(player_id)


def remote_update_play_songs(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    songs = data.get(const.SERVICE_INPUT_SONGS)
    mode = QueueMode.replace
    play_directly = True

    return audio_station.remote_player_play_songs(player_id, songs, mode, play_directly)


def remote_update_play_artist(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    artist = data.get(const.SERVICE_INPUT_ARTIST)
    mode = QueueMode.replace
    play_directly = True

    return audio_station.remote_player_play_artist(player_id, artist, SongSortMode.album, mode, play_directly)


def remote_update_play_album(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    album_artist = data.get(const.SERVICE_INPUT_ALBUM_ARTIST)
    album_name = data.get(const.SERVICE_INPUT_ALBUM_NAME)

    mode = QueueMode.replace
    play_directly = True

    return audio_station.remote_player_play_album(player_id, album_name,
                                                  album_artist, SongSortMode.track, mode, play_directly)


def remote_player_shuffle(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    shuffle_mode = data.get(const.SERVICE_INPUT_SHUFFLE)

    return audio_station.remote_player_shuffle(player_id, shuffle_mode)


def remote_player_control(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    action = RemotePlayerAction(data.get(const.SERVICE_INPUT_ACTION))

    return audio_station.remote_player_control(player_id, action)


def remote_player_jump_to_song(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    position = int(data.get(const.SERVICE_INPUT_POSITION))

    return audio_station.remote_player_jump_to_song(player_id, position)


def remote_player_volume(audio_station: SynoAudioStation, player_id: str, data: ReadOnlyDict) -> bool:
    volume = data.get(const.SERVICE_INPUT_VOLUME)
    return audio_station.remote_player_volume(player_id, volume)


def remote_player_clear_playlist(audio_station: SynoAudioStation, player_id: str,
                                 data: ReadOnlyDict) -> bool:
    return audio_station.remote_player_clear_playlist(player_id)
