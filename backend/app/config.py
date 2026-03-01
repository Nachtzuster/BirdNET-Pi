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
            'MODEL': 'BirdNET_GLOBAL_6K_V2.4_Model_FP16',
            'CONFIDENCE': '0.7',
            'SENSITIVITY': '1.0',
            'OVERLAP': '0.0',
            'RECS_DIR': os.path.expanduser('~/BirdSongs'),
            'EXTRACTED': os.path.expanduser('~/BirdSongs/Extracted'),
            'BIRDWEATHER_ID': '',
            'APPRISE_NOTIFICATION_TITLE': 'New BirdNET Detection',
            'APPRISE_NOTIFICATION_BODY': '$comname was detected with confidence $confidencepct',
        }

    @property
    def config(self) -> dict:
        return self._load_config()

    def reload(self):
        """Force reload configuration from file."""
        self._load_config(force_reload=True)

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

    # Model settings
    @property
    def model(self) -> str:
        return self.config.get('MODEL', 'BirdNET_GLOBAL_6K_V2.4_Model_FP16')

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
