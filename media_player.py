from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_STOP,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

SUPPORT_DLNA_PLAYER = (
        SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET | SUPPORT_STOP | SUPPORT_PLAY | SUPPORT_PAUSE
)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_devices: AddEntitiesCallback,
) -> None:
    """Create the SynologyDlnaMediaPlayer devices."""

    all_entities = [
        SynologyDlnaMediaPlayer("test", "test")
    ]

    async_add_devices(all_entities)


# noinspection PyAbstractClass
class SynologyDlnaMediaPlayer(MediaPlayerEntity):
    """An entity using CoordinatorEntity. """

    def __init__(self, nas_serial: str, player_uuid: str):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__()
        self.nas_serial = nas_serial
        self.player_uuid = player_uuid

    @property
    def name(self):
        """Return the display name of this TV."""
        return "blabla"

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DLNA_PLAYER

    @property
    def device_class(self):
        """Return the class of this entity."""
        return 'speaker'
