from functools import wraps
from typing import Optional

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_STOP,
    SUPPORT_PLAY,
    SUPPORT_PAUSE, MEDIA_TYPE_MUSIC, REPEAT_MODES, REPEAT_MODE_ALL, REPEAT_MODE_ONE,
    SUPPORT_CLEAR_PLAYLIST, SUPPORT_SHUFFLE_SET, SUPPORT_REPEAT_SET, SUPPORT_PREVIOUS_TRACK, SUPPORT_NEXT_TRACK,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_PLAYING, STATE_IDLE, STATE_PAUSED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .shared import LOGGER
from .synology_dsm.exceptions import SynologyDSMAPIErrorException

from .api.SynoApi import SynoApi
from .synology_dsm.api.dsm.information import SynoDSMInformation
from .synology_dsm.api.audio_station import RemotePlayerAction, RepeatMode, SynoAudioStation, Player, \
    RemotePlayerStatus
from .synology_dsm.api.audio_station.models.playlist_status import PlaylistStatus
from .const import DOMAIN, SYNO_API

SUPPORT_DLNA_PLAYER = (
        SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET
        | SUPPORT_STOP | SUPPORT_PLAY | SUPPORT_PAUSE
        | SUPPORT_CLEAR_PLAYLIST | SUPPORT_SHUFFLE_SET | SUPPORT_REPEAT_SET
        | SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK
)

PLAY_STATE_TO_STATE = {
    PlaylistStatus.transitioning: STATE_PLAYING,
    PlaylistStatus.playing: STATE_PLAYING,
    PlaylistStatus.pause: STATE_PAUSED,
    PlaylistStatus.stopped: STATE_IDLE,
    PlaylistStatus.none: STATE_IDLE,
}


def log_command_error(command: str):
    """Return decorator that logs command failure."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except (SynologyDSMAPIErrorException, ValueError) as ex:
                LOGGER.error("Unable to %s: %s", command, ex)

        return wrapper

    return decorator


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the SynologyDlnaMediaPlayer devices."""

    data = hass.data[DOMAIN][config_entry.entry_id]
    api: SynoApi = data[SYNO_API]

    players = await hass.async_add_executor_job(api.dsm.audio_station.remote_player_get_players)

    devices = [SynologyDlnaMediaPlayer(hass, api.information, api.dsm.audio_station, player) for player in players]
    async_add_entities(devices, True)


# noinspection PyAbstractClass
class SynologyDlnaMediaPlayer(MediaPlayerEntity):
    """SynologyDlnaMediaPlayer. """

    def __init__(self, hass: HomeAssistant, info: SynoDSMInformation, audio_station: SynoAudioStation, player: Player):
        """Initialize the media player."""
        self._hass = hass
        self._api = audio_station
        self._info = info
        self._player = player
        self._status: Optional[RemotePlayerStatus] = None

    @property
    def name(self):
        """Return the display name of this TV."""
        return self._player.name

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DLNA_PLAYER

    @property
    def should_poll(self) -> bool:
        """Polling needed for this device."""
        return True

    async def async_update(self):
        """Update player info."""
        self._status = await self._hass.async_add_executor_job(self._api.remote_player_get_player_status,
                                                               self._player.id)

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._player is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Get attributes about the device."""
        info = self._player
        return DeviceInfo(
            identifiers={(DOMAIN, info.id)},
            name=info.name,
            via_device=(DOMAIN, self._info.serial),
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return str(self._player.id)

    @log_command_error("move to previous track")
    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._hass.async_add_executor_job(self._api.remote_player_control, self._player.id,
                                                RemotePlayerAction.prev)
        await self.async_update()

    @log_command_error("move to next track")
    async def async_media_next_track(self):
        """Send next track command."""
        await self._hass.async_add_executor_job(self._api.remote_player_control, self._player.id,
                                                RemotePlayerAction.next)
        await self.async_update()

    @log_command_error("stop")
    async def async_media_stop(self):
        """Send stop command."""
        await self._hass.async_add_executor_job(self._api.remote_player_control, self._player.id,
                                                RemotePlayerAction.stop)
        await self.async_update()

    @log_command_error("pause")
    async def async_media_pause(self):
        """Send pause command."""
        await self._hass.async_add_executor_job(self._api.remote_player_control, self._player.id,
                                                RemotePlayerAction.pause)
        await self.async_update()

    @log_command_error("play")
    async def async_media_play(self):
        """Send play command."""
        await self._hass.async_add_executor_job(self._api.remote_player_control, self._player.id,
                                                RemotePlayerAction.play)
        await self.async_update()

    @log_command_error("clear playlist")
    async def async_clear_playlist(self):
        """Clear players playlist."""
        await self._hass.async_add_executor_job(self._api.remote_player_clear_playlist, self._player.id)
        await self.async_update()

    @log_command_error("set shuffle")
    async def async_set_shuffle(self, shuffle: bool):
        """Enable/disable shuffle mode."""
        await self._hass.async_add_executor_job(self._api.remote_player_shuffle, self._player.id, shuffle)
        await self.async_update()

    @log_command_error("set repeat")
    async def async_set_repeat(self, repeat: REPEAT_MODES):
        """Enable/disable shuffle mode."""
        if repeat == REPEAT_MODE_ALL:
            await self._hass.async_add_executor_job(self._api.remote_player_repeat, self._player.id, RepeatMode.all)
        elif repeat == REPEAT_MODE_ONE:
            await self._hass.async_add_executor_job(self._api.remote_player_repeat, self._player.id, RepeatMode.one)
        else:
            await self._hass.async_add_executor_job(self._api.remote_player_repeat, self._player.id, RepeatMode.none)
        await self.async_update()

    @log_command_error("set volume level")
    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        await self._hass.async_add_executor_job(self._api.remote_player_volume, self._player.id, int(volume * 100))
        await self.async_update()

    @property
    def media_album_name(self) -> Optional[str]:
        """Album name of current playing media, music track only."""
        if self._status.song:
            return self._status.song.additional.song_tag.album
        return None

    @property
    def media_artist(self) -> Optional[str]:
        """Artist of current playing media, music track only."""
        if self._status.song:
            return self._status.song.additional.song_tag.artist
        return None

    @property
    def media_content_id(self) -> Optional[str]:
        """Content ID of current playing media."""
        if self._status.song:
            return self._status.song.id
        return None

    @property
    def media_content_type(self) -> str:
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        if self._status.song:
            duration = self._status.song.additional.song_audio.duration
            if isinstance(duration, int):
                return duration / 1000
        return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        return self._status.position / 1000

    @property
    def media_image_remotely_accessible(self) -> bool:
        """If the image url is remotely accessible."""
        return True

    # @property
    # def media_image(self) -> bytearray:
    #     """Image url of current playing media."""
    #     # return self._player.

    @property
    def media_title(self) -> Optional[str]:
        """Title of current playing media."""
        if self._status.song:
            return self._status.song.title
        return None

    @property
    def shuffle(self) -> bool:
        """Boolean if shuffle is enabled."""
        return self._status.play_mode.play_mode_shuffle

    @property
    def repeat(self) -> str:
        """Boolean if repeat is enabled."""
        return self._status.play_mode.play_mode_repeat

    @property
    def state(self) -> str:
        """State of the player."""
        return PLAY_STATE_TO_STATE[self._status.state]

    @property
    def volume_level(self) -> float:
        """Volume level of the media player (0..1)."""
        return self._status.volume / 100
