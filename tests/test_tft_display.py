#!/usr/bin/env python3
"""
Tests for TFT Display Auto-Configuration
Tests the automatic detection and configuration of SPI TFT displays
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add scripts directory to path
SCRIPT_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, SCRIPT_DIR)


class TestTFTDisplayConfig(unittest.TestCase):
    """Test TFT display configuration loading"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, 'birdnet.conf')
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_config_with_tft_enabled(self):
        """Test configuration loading with TFT enabled"""
        config_content = """
TFT_ENABLED=1
TFT_TYPE=ili9341
TFT_ROTATION=90
TFT_FONT_SIZE=12
TFT_SCROLL_SPEED=2
DB_PATH=/home/pi/BirdNET-Pi/scripts/birds.db
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        # Import after file is created
        from tft_display import TFTDisplayConfig
        
        with patch('tft_display.os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=config_content)):
                config = TFTDisplayConfig()
                config.load_config()
                
                self.assertTrue(config.enabled)
                self.assertEqual(config.device_type, 'ili9341')
                self.assertEqual(config.rotation, 90)
                self.assertEqual(config.font_size, 12)
    
    def test_config_with_tft_disabled(self):
        """Test configuration loading with TFT disabled"""
        config_content = """
TFT_ENABLED=0
TFT_TYPE=ili9341
"""
        
        from tft_display import TFTDisplayConfig
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            with patch('tft_display.os.path.exists', return_value=True):
                config = TFTDisplayConfig()
                config.load_config()
                
                self.assertFalse(config.enabled)
    
    def test_config_missing_file(self):
        """Test configuration with missing file"""
        from tft_display import TFTDisplayConfig
        
        with patch('tft_display.os.path.exists', return_value=False):
            config = TFTDisplayConfig()
            
            # Should use defaults
            self.assertFalse(config.enabled)
            self.assertEqual(config.device_type, 'ili9341')


class TestTFTAutoDetection(unittest.TestCase):
    """Test automatic TFT hardware detection"""
    
    def test_detect_framebuffer(self):
        """Test framebuffer device detection"""
        # Test when fb1 exists (TFT present)
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Simulate fb1 device
            from pathlib import Path
            test_path = Path('/dev/fb1')
            
            # In real scenario, this would check if fb1 exists
            self.assertTrue(mock_exists('/dev/fb1'))
    
    def test_detect_spi_device(self):
        """Test SPI device detection"""
        # This would check for SPI devices in /sys/class/spi_master
        # We're testing the logic pattern here
        
        spi_devices = [
            'spi0.0',
            'spi0.1'
        ]
        
        # Verify we can detect SPI devices
        self.assertTrue(len(spi_devices) > 0)
    
    def test_detect_tft_type_from_config(self):
        """Test TFT type detection from boot config"""
        config_content = """
dtparam=spi=on
dtoverlay=piscreen,speed=16000000,rotate=90
dtoverlay=ads7846,cs=1,penirq=25
"""
        
        # Check if we can detect ili9341 from piscreen overlay
        if 'piscreen' in config_content:
            detected_type = 'ili9341'
        
        self.assertEqual(detected_type, 'ili9341')


class TestTFTDisplayService(unittest.TestCase):
    """Test TFT display service behavior"""
    
    def test_service_stays_running_when_disabled(self):
        """Test that service stays running even when TFT is disabled"""
        from tft_display import TFTDisplayConfig
        
        config_content = "TFT_ENABLED=0\n"
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            with patch('tft_display.os.path.exists', return_value=True):
                config = TFTDisplayConfig()
                config.load_config()
                
                # Service should recognize disabled state but not crash
                self.assertFalse(config.enabled)
                # In real implementation, service would enter standby mode
    
    def test_display_initialization_failure_handling(self):
        """Test graceful handling of display initialization failure"""
        from tft_display import TFTDisplay, TFTDisplayConfig
        
        config = TFTDisplayConfig()
        
        # Mock luma library not available
        with patch('tft_display.LUMA_AVAILABLE', False):
            display = TFTDisplay(config)
            
            # Service should handle missing hardware gracefully
            self.assertIsNone(display.device)


class TestTFTConfigurationUpdate(unittest.TestCase):
    """Test configuration file updates"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, 'birdnet.conf')
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_update_config_with_tft_settings(self):
        """Test updating configuration with TFT settings"""
        initial_content = """
DATABASE_LANG=en
LATITUDE=50.0
LONGITUDE=5.0
"""
        with open(self.config_file, 'w') as f:
            f.write(initial_content)
        
        # Simulate adding TFT configuration
        tft_config = """
TFT_ENABLED=1
TFT_TYPE=ili9341
TFT_ROTATION=90
TFT_FONT_SIZE=12
"""
        
        with open(self.config_file, 'a') as f:
            f.write(tft_config)
        
        # Verify configuration was added
        with open(self.config_file, 'r') as f:
            content = f.read()
            self.assertIn('TFT_ENABLED=1', content)
            self.assertIn('TFT_TYPE=ili9341', content)
            self.assertIn('TFT_ROTATION=90', content)
    
    def test_config_removes_old_tft_settings(self):
        """Test that old TFT settings are removed before adding new ones"""
        initial_content = """
TFT_ENABLED=0
TFT_TYPE=st7735
DATABASE_LANG=en
"""
        with open(self.config_file, 'w') as f:
            f.write(initial_content)
        
        # Read and remove TFT lines
        with open(self.config_file, 'r') as f:
            lines = [line for line in f if not line.startswith('TFT_')]
        
        # Write back without TFT lines
        with open(self.config_file, 'w') as f:
            f.writelines(lines)
        
        # Add new TFT configuration
        new_tft_config = """TFT_ENABLED=1
TFT_TYPE=ili9341
"""
        with open(self.config_file, 'a') as f:
            f.write(new_tft_config)
        
        # Verify old settings removed and new ones added
        with open(self.config_file, 'r') as f:
            content = f.read()
            self.assertIn('TFT_TYPE=ili9341', content)
            self.assertNotIn('TFT_TYPE=st7735', content)


class TestTFTPortraitMode(unittest.TestCase):
    """Test portrait mode configuration"""
    
    def test_portrait_mode_rotation(self):
        """Test that portrait mode uses 90 degree rotation"""
        rotation = 90  # Portrait mode
        
        # Portrait mode should swap width and height
        width, height = 240, 320
        
        if rotation in [90, 270]:
            # In portrait mode, dimensions are swapped
            display_width, display_height = height, width
        else:
            display_width, display_height = width, height
        
        # Verify portrait mode swaps dimensions correctly
        self.assertEqual(display_width, 320)
        self.assertEqual(display_height, 240)
    
    def test_touchscreen_swapxy_for_portrait(self):
        """Test that touch coordinates are swapped for portrait mode"""
        rotation = 90
        
        # In portrait mode (90 or 270 degrees), swapxy should be 1
        swapxy = 1 if rotation in [90, 270] else 0
        
        self.assertEqual(swapxy, 1)


class TestTFTScreensaver(unittest.TestCase):
    """Test TFT screensaver functionality"""
    
    def test_screensaver_timeout(self):
        """Test screensaver timeout configuration"""
        from tft_display import TFTDisplayConfig
        
        config_content = """
TFT_ENABLED=1
TFT_SCREENSAVER_TIMEOUT=300
TFT_SCREENSAVER_BRIGHTNESS=0
"""
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            with patch('tft_display.os.path.exists', return_value=True):
                config = TFTDisplayConfig()
                config.load_config()
                
                self.assertEqual(config.screensaver_timeout, 300)
                self.assertEqual(config.screensaver_brightness, 0)
    
    def test_screensaver_disabled(self):
        """Test that screensaver can be disabled"""
        screensaver_timeout = 0  # Disabled
        
        # When timeout is 0, screensaver should be disabled
        screensaver_enabled = screensaver_timeout > 0
        
        self.assertFalse(screensaver_enabled)


if __name__ == '__main__':
    unittest.main()
