"""Synology AudioStation API wrapper."""
from typing import List, Dict, Any

from .player_list import PlayerList
from .playlist import Playlist
from .remote_player_action import RemotePlayerAction
from .remote_player_status import RemotePlayerStatus

import json


def comma_join(value) -> str:
    return ",".join(value) if isinstance(value, list) else value


class SynoAudioStation:
    """An implementation of a Synology AudioStation."""

    API_KEY = "SYNO.AudioStation.*"
    REMOTE_PLAYER_KEY = "SYNO.AudioStation.RemotePlayer"
    REMOTE_PLAYER_STATUS_KEY = "SYNO.AudioStation.RemotePlayerStatus"

    def __init__(self, dsm):
        """Initialize Audio Station."""
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

        res = self._dsm.post(self.REMOTE_PLAYER_KEY, "getplaylist", data=opts)

        return Playlist(res["data"])

    def __remote_update_playlist(self, player_uuid: str, opts: Dict[str, Any]) -> bool:
        """Update playlist of remote player"""

        base_opts = {
            "id": "uuid:" + player_uuid,
            "version": 3,
        }

        final_opts = {**base_opts, **opts}
        res = self._dsm.post(self.REMOTE_PLAYER_KEY, "updateplaylist", data=final_opts)

        return res["success"]

    def remote_player_clear_playlist(self, player_uuid: str) -> bool:
        """Clear current playlist"""

        current = self.remote_current_playlist(player_uuid)

        opts = {
            "offset": 0,
            "limit": current.total,
            "updated_index": -1,
            "song": ""
        }

        return self.__remote_update_playlist(player_uuid, opts)

    def remote_player_play_songs(self, player_uuid: str, song_ids: List[str]) -> bool:
        """Play songs using their ids"""

        opts = {
            "offset": -1,
            "limit": 0,
            "songs": comma_join(song_ids),
            "library": "shared",
            "keep_shuffle_order": "false",
            "play": "true"
        }

        return self.__remote_update_playlist(player_uuid, opts)

    def remote_player_play_album(self, player_uuid: str, album_name: str, album_artist: str) -> bool:
        """Play an album using album name and album artist"""

        container_json = {
            "type": "album",
            "sort_by": "track",
            "sort_direction": "ASC",
            "album": album_name,
            "album_artist": album_artist
        }

        opts = {
            "library": "shared",
            "keep_shuffle_order": "false",
            "play": "true",
            "containers_json": json.dumps([container_json]),
            "offset": 0,
            "limit": 0
        }

        return self.__remote_update_playlist(player_uuid, opts)

    def remote_player_control(self, player_uuid: str, action: RemotePlayerAction) -> bool:
        """Change player current playing status"""
        res = self._dsm.post(
            self.REMOTE_PLAYER_KEY,
            "control",
            data={
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
            data={
                "id": "uuid:" + player_uuid,
                "action": "set_volume",
                "value": volume
            },
        )

        return res["success"]
