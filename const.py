DOMAIN = "synology_dsaudio"
VERSION = "1.0.0"

CONF_SERIAL = "serial"
CONF_DEVICE_TOKEN = "device_token"
CONF_OTP_CODE = "otp_code"

# Defaults
DEFAULT_USE_SSL = True
DEFAULT_VERIFY_SSL = False
DEFAULT_PORT = 5000
DEFAULT_PORT_SSL = 5001
DEFAULT_TIMEOUT = 10  # sec

EXCEPTION_DETAILS = "details"
EXCEPTION_UNKNOWN = "unknown"

SYNO_API = "syno_api"

# Service keys

SERVICE_FUNC_GETPLAYERS = "get_players"
SERVICE_FUNC_GETPLAYER_STATUS = "get_player_status"
SERVICE_FUNC_REMOTE_PLAY_SONGS = "remote_player_play_songs"
SERVICE_FUNC_REMOTE_PLAY_ALBUM = "remote_player_play_album"
SERVICE_FUNC_REMOTE_PLAYER_CONTROL = "remote_player_control"
SERVICE_FUNC_REMOTE_PLAYER_VOLUME = "remote_player_volume"
SERVICE_FUNC_REMOTE_SLEEP_TIMER = "remote_player_volume"

# Service input keys
SERVICE_INPUT_SONGS = "songs"
SERVICE_INPUT_ALBUM_ARTIST = "album_artist"
SERVICE_INPUT_ALBUM_NAME = "album_name"
SERVICE_INPUT_CLEAR_PLAYLIST = "clear_playlist"
SERVICE_INPUT_ACTION = "action"
SERVICE_INPUT_PLAYERUUID = "player_uuid"
SERVICE_INPUT_VOLUME = "volume"
SERVICE_INPUT_SLEEP_TIMER = "sleep_timer"
