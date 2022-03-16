"""Synology AudioStation API wrapper."""
from typing import List, Optional

from .playlist import Playlist
from .remote_player_action import RemotePlayerAction
from .remote_player_status import RemotePlayerStatus
from .player_list import PlayerList


def comma_join(value) -> str:
    return ",".join(value) if isinstance(value, list) else value


class SynoAudioStation:
    """An implementation of a Synology AudioStation."""

    API_KEY = "SYNO.AudioStation.*"
    REMOTE_PLAYER_KEY = "SYNO.AudioStation.RemotePlayer"
    REMOTE_PLAYER_STATUS_KEY = "SYNO.AudioStation.RemotePlayerStatus"

    def __init__(self, dsm):
        """Initialize a Download Station."""
        self._dsm = dsm

    def get_player_status(self, player_uuid) -> RemotePlayerStatus:
        """Get status of remote player"""
        res = self._dsm.get(
            self.REMOTE_PLAYER_STATUS_KEY,
            "getstatus",
            {
                "id": "uuid:" + player_uuid,
                "additional": "song_tag,song_audio,subplayer_volume"
            },
        )
        return RemotePlayerStatus(res)

    def get_players(self) -> PlayerList:
        """Get list of remote players"""
        res = self._dsm.get(
            self.REMOTE_PLAYER_KEY,
            "list",
            {
                "type": "all",
                "additional": "subplayer_list"
            },
        )

        return PlayerList(res["data"])

    def remote_current_playlist(self, player_uuid: str) -> Playlist:
        opts = {
            "id": "uuid:" + player_uuid,
            "offset": 0,
            "limit": 8192,
            "additional": "song_tag,song_audio,song_rating",
            "version": 3,
        }

        res = self._dsm.post(self.REMOTE_PLAYER_KEY, "getplaylist", opts)

        return Playlist(res["data"])

    def __remote_update_playlist(self, player_uuid: str, song_ids: Optional[List[str]],
                                 containers_json: Optional[List[dict[str, str]]],
                                 clear_playlist: bool) -> bool:
        """Update playlist of remote player"""

        opts = {
            "id": "uuid:" + player_uuid,
            "library": "shared",
            "keep_shuffle_order": False,
            "play": True,
            "version": 3,
        }

        if song_ids:
            opts["songs"]: comma_join(song_ids)

        if containers_json:
            opts["containers_json"]: containers_json

        if clear_playlist:
            opts["offset"] = 0
            opts["updated_index"] = 8192
            opts["updated_index"] = -1
        else:
            # current_playlist = self.remote_current_playlist(player_uuid)
            # current_size = current_playlist.total
            opts["offset"] = -1
            opts["limit"] = 0

        res = self._dsm.post(self.REMOTE_PLAYER_KEY, "updateplaylist", opts)

        return res["success"]

    def remote_player_play_songs(self, player_uuid: str, song_ids: List[str],
                                 clear_playlist: bool) -> bool:
        """Play songs using their ids"""

        return self.__remote_update_playlist(player_uuid, song_ids, None, clear_playlist)

    def remote_player_play_album(self, player_uuid: str, album_name: str, album_artist: str,
                                 clear_playlist: bool) -> bool:
        """Play an album using album name and album artist"""

        container_json = {
            "type": "album",
            "sort_by": "title",
            "sort_direction": "ASC",
            "album": album_name,
            "album_artist": album_artist
        }

        return self.__remote_update_playlist(player_uuid, None, [container_json], clear_playlist)

    def remote_player_control(self, player_uuid: str, action: RemotePlayerAction) -> bool:
        """Change player current playing status"""
        res = self._dsm.post(
            self.REMOTE_PLAYER_KEY,
            "control",
            {
                "id": "uuid:" + player_uuid,
                "action": action
            },
        )

        return res["success"]

    def remote_player_volume(self, player_uuid: str, volume: int) -> bool:
        """Change player current vlome"""

        if not 0 <= volume <= 100:
            raise ValueError('Volume should be between 0 and 100')

        res = self._dsm.post(
            self.REMOTE_PLAYER_KEY,
            "control",
            {
                "id": "uuid:" + player_uuid,
                "action": "set_volume",
                "value": volume
            },
        )

        return res["success"]
