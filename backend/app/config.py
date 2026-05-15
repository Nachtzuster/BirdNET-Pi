"""Configuration management for BirdNET-Pi API.

Reuses the existing config parsing from scripts/utils/helpers.py
"""
import os
import sys
from functools import lru_cache

# Add scripts to path to reuse existing utilities
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(BACKEND_DIR)
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from utils.helpers import get_settings as _get_settings, BASE_PATH, DB_PATH, MODEL_PATH  # noqa: E402


class Settings:
    """Application settings loaded from /etc/birdnet/birdnet.conf."""

    def __init__(self, config_path: str = '/etc/birdnet/birdnet.conf'):
        self._config_path = config_path
        self._config = None

    def _load_config(self, force_reload: bool = False):
        if self._config is None or force_reload:
            try:
                self._config = dict(_get_settings(self._config_path, force_reload))
            except FileNotFoundError:
                # Use defaults for development/testing
                self._config = self._get_defaults()
        return self._config

    def _get_defaults(self) -> dict:
        """Default configuration for development/testing."""
        return {
            'SITE_NAME': 'BirdNET-Pi',
            'LATITUDE': '0.0',
            'LONGITUDE': '0.0',
            'CADDY_PWD': 'birdnet',
            'DATABASE_LANG': 'en',
            'COLOR_SCHEME': 'light',
            'UPDATE_CHANNEL': 'stable',
            'MODEL': 'BirdNET_GLOBAL_6K_V2.4_Model_FP16',
            'SF_THRESH': '0.03',
            'DATA_MODEL_VERSION': '1',
            'CONFIDENCE': '0.7',
            'SENSITIVITY': '1.0',
            'OVERLAP': '0.0',
            'RECS_DIR': os.path.expanduser('~/BirdSongs'),
            'EXTRACTED': os.path.expanduser('~/BirdSongs/Extracted'),
            'BIRDWEATHER_ID': '',
            'APPRISE_NOTIFY_EACH_DETECTION': '0',
            'APPRISE_NOTIFY_NEW_SPECIES': '0',
            'APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY': '0',
            'APPRISE_WEEKLY_REPORT': '1',
            'APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES': '0',
            'APPRISE_ONLY_NOTIFY_SPECIES_NAMES': '',
            'APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2': '',
            'APPRISE_NOTIFICATION_TITLE': 'New BirdNET Detection',
            'APPRISE_NOTIFICATION_BODY': '$comname was detected with confidence $confidencepct',
            'INFO_SITE': 'ALLABOUTBIRDS',
            'IMAGE_PROVIDER': 'wikipedia',
            'FLICKR_API_KEY': '',
            'FLICKR_FILTER_EMAIL': '',
            'BIRDNETPI_URL': '',
            'RTSP_STREAM': '',
            'RTSP_STREAM_TO_LIVESTREAM': '0',
            'ACTIVATE_FREQSHIFT_IN_LIVESTREAM': 'false',
            'FULL_DISK': 'purge',
            'PURGE_THRESHOLD': '95',
            'MAX_FILES_SPECIES': '0',
            'REC_CARD': 'default',
            'CHANNELS': '2',
            'RECORDING_LENGTH': '15',
            'EXTRACTION_LENGTH': '',
            'AUDIOFMT': 'mp3',
            'PRIVACY_THRESHOLD': '0',
            'SILENCE_UPDATE_INDICATOR': '0',
            'AUTOMATIC_UPDATE': '0',
            'RAW_SPECTROGRAM': '0',
            'CUSTOM_IMAGE': '',
            'CUSTOM_IMAGE_TITLE': '',
            'RARE_SPECIES_THRESHOLD': '30',
            'FREQSHIFT_TOOL': 'sox',
            'FREQSHIFT_HI': '6000',
            'FREQSHIFT_LO': '3000',
            'FREQSHIFT_RECONNECT_DELAY': '4000',
            'FREQSHIFT_PITCH': '-1500',
            'LogLevel_BirdnetRecordingService': 'error',
            'LogLevel_LiveAudioStreamService': 'error',
            'LogLevel_SpectrogramViewerService': 'error',
        }

    @property
    def config(self) -> dict:
        return self._load_config()

    def _get_bool(self, key: str, default: bool = False) -> bool:
        raw = str(self.config.get(key, str(int(default)))).strip().strip('"').lower()
        return raw in {'1', 'true', 'yes', 'on'}

    def _get_int(self, key: str, default: int) -> int:
        try:
            return int(str(self.config.get(key, default)).strip().strip('"'))
        except (TypeError, ValueError):
            return default

    def _get_optional_int(self, key: str) -> int | None:
        raw = str(self.config.get(key, '')).strip().strip('"')
        if raw == '':
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def reload(self):
        """Force reload configuration from file."""
        self._load_config(force_reload=True)

    @property
    def config_path(self) -> str:
        return self._config_path

    # Site settings
    @property
    def site_name(self) -> str:
        return self.config.get('SITE_NAME', 'BirdNET-Pi')

    @property
    def latitude(self) -> float:
        return float(self.config.get('LATITUDE', 0))

    @property
    def longitude(self) -> float:
        return float(self.config.get('LONGITUDE', 0))

    # Authentication
    @property
    def caddy_password(self) -> str:
        return self.config.get('CADDY_PWD', '')

    # Display settings
    @property
    def database_lang(self) -> str:
        return self.config.get('DATABASE_LANG', 'en')

    @property
    def color_scheme(self) -> str:
        return self.config.get('COLOR_SCHEME', 'light')

    @property
    def update_channel(self) -> str:
        return self.config.get('UPDATE_CHANNEL', 'stable')

    @property
    def info_site(self) -> str:
        return self.config.get('INFO_SITE', 'ALLABOUTBIRDS')

    # Model settings
    @property
    def model(self) -> str:
        return self.config.get('MODEL', 'BirdNET_GLOBAL_6K_V2.4_Model_FP16')

    @property
    def sf_thresh(self) -> float:
        return float(self.config.get('SF_THRESH', 0.03))

    @property
    def data_model_version(self) -> int:
        return int(self.config.get('DATA_MODEL_VERSION', 1))

    @property
    def confidence(self) -> float:
        return float(self.config.get('CONFIDENCE', 0.7))

    @property
    def sensitivity(self) -> float:
        return float(self.config.get('SENSITIVITY', 1.0))

    @property
    def overlap(self) -> float:
        return float(self.config.get('OVERLAP', 0.0))

    # Directories
    @property
    def recs_dir(self) -> str:
        return self.config.get('RECS_DIR', os.path.expanduser('~/BirdSongs'))

    @property
    def extracted_dir(self) -> str:
        return self.config.get('EXTRACTED', os.path.expanduser('~/BirdSongs/Extracted'))

    # Integration settings
    @property
    def birdweather_id(self) -> str:
        return self.config.get('BIRDWEATHER_ID', '')

    @property
    def flickr_api_key(self) -> str:
        return self.config.get('FLICKR_API_KEY', '')

    @property
    def image_provider(self) -> str:
        return self.config.get('IMAGE_PROVIDER', 'wikipedia')

    @property
    def flickr_filter_email(self) -> str:
        return self.config.get('FLICKR_FILTER_EMAIL', '')

    @property
    def birdnetpi_url(self) -> str:
        return self.config.get('BIRDNETPI_URL', '')

    @property
    def rtsp_stream(self) -> str:
        return self.config.get('RTSP_STREAM', '')

    @property
    def rtsp_stream_to_livestream(self) -> int:
        return self._get_int('RTSP_STREAM_TO_LIVESTREAM', 0)

    @property
    def activate_freqshift_in_livestream(self) -> bool:
        return self._get_bool('ACTIVATE_FREQSHIFT_IN_LIVESTREAM', False)

    @property
    def apprise_notification_title(self) -> str:
        return self.config.get('APPRISE_NOTIFICATION_TITLE', 'New BirdNET Detection')

    @property
    def apprise_notify_each_detection(self) -> bool:
        return self._get_bool('APPRISE_NOTIFY_EACH_DETECTION', False)

    @property
    def apprise_notify_new_species(self) -> bool:
        return self._get_bool('APPRISE_NOTIFY_NEW_SPECIES', False)

    @property
    def apprise_notify_new_species_each_day(self) -> bool:
        return self._get_bool('APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY', False)

    @property
    def apprise_weekly_report(self) -> bool:
        return self._get_bool('APPRISE_WEEKLY_REPORT', True)

    @property
    def apprise_minimum_seconds_between_notifications_per_species(self) -> int:
        return self._get_int('APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES', 0)

    @property
    def apprise_only_notify_species_names(self) -> str:
        return self.config.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES', '')

    @property
    def apprise_only_notify_species_names_2(self) -> str:
        return self.config.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2', '')

    @property
    def privacy_threshold(self) -> int:
        return self._get_int('PRIVACY_THRESHOLD', 0)

    @property
    def full_disk(self) -> str:
        return self.config.get('FULL_DISK', 'purge')

    @property
    def purge_threshold(self) -> int:
        return self._get_int('PURGE_THRESHOLD', 95)

    @property
    def max_files_species(self) -> int:
        return self._get_int('MAX_FILES_SPECIES', 0)

    @property
    def rec_card(self) -> str:
        return self.config.get('REC_CARD', 'default')

    @property
    def channels(self) -> int:
        return self._get_int('CHANNELS', 2)

    @property
    def recording_length(self) -> int:
        return self._get_int('RECORDING_LENGTH', 15)

    @property
    def extraction_length(self) -> int | None:
        return self._get_optional_int('EXTRACTION_LENGTH')

    @property
    def audiofmt(self) -> str:
        return self.config.get('AUDIOFMT', 'mp3')

    @property
    def silence_update_indicator(self) -> bool:
        return self._get_bool('SILENCE_UPDATE_INDICATOR', False)

    @property
    def automatic_update(self) -> bool:
        return self._get_bool('AUTOMATIC_UPDATE', False)

    @property
    def raw_spectrogram(self) -> bool:
        return self._get_bool('RAW_SPECTROGRAM', False)

    @property
    def rare_species_threshold(self) -> int:
        return self._get_int('RARE_SPECIES_THRESHOLD', 30)

    @property
    def custom_image(self) -> str:
        return self.config.get('CUSTOM_IMAGE', '')

    @property
    def custom_image_title(self) -> str:
        return self.config.get('CUSTOM_IMAGE_TITLE', '')

    @property
    def freqshift_tool(self) -> str:
        return self.config.get('FREQSHIFT_TOOL', 'sox')

    @property
    def freqshift_hi(self) -> int:
        return self._get_int('FREQSHIFT_HI', 6000)

    @property
    def freqshift_lo(self) -> int:
        return self._get_int('FREQSHIFT_LO', 3000)

    @property
    def freqshift_reconnect_delay(self) -> int:
        return self._get_int('FREQSHIFT_RECONNECT_DELAY', 4000)

    @property
    def freqshift_pitch(self) -> int:
        return self._get_int('FREQSHIFT_PITCH', -1500)

    @property
    def log_level_birdnet_recording_service(self) -> str:
        return self.config.get('LogLevel_BirdnetRecordingService', 'error')

    @property
    def log_level_live_audio_stream_service(self) -> str:
        return self.config.get('LogLevel_LiveAudioStreamService', 'error')

    @property
    def log_level_spectrogram_viewer_service(self) -> str:
        return self.config.get('LogLevel_SpectrogramViewerService', 'error')

    # Paths
    @property
    def base_path(self) -> str:
        return BASE_PATH

    @property
    def db_path(self) -> str:
        return DB_PATH

    @property
    def model_path(self) -> str:
        return MODEL_PATH

    @property
    def charts_dir(self) -> str:
        return os.path.join(self.extracted_dir, 'Charts')

    @property
    def by_date_dir(self) -> str:
        return os.path.join(self.extracted_dir, 'By_Date')


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
