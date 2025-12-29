#!/usr/bin/env python3
"""
TFT Display Daemon for BirdNET-Pi
Displays detected bird species with confidence scores in scrolling portrait mode
"""

import os
import sys
import time
import signal
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Try to import display libraries
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. Install with: pip install Pillow")

try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.lcd.device import ili9341, st7735, st7789v, ili9488
    LUMA_AVAILABLE = True
except ImportError:
    LUMA_AVAILABLE = False
    print("Warning: luma.lcd not available. Install with: pip install luma.lcd")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger('tft_display')

# Global shutdown flag
shutdown = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown
    log.info(f'Received signal {signum}, shutting down...')
    shutdown = True


class TFTDisplayConfig:
    """Configuration for TFT display"""
    
    def __init__(self):
        """Load configuration from /etc/birdnet/birdnet.conf"""
        self.enabled = False
        self.device_type = 'ili9341'
        self.rotation = 90
        self.font_size = 12
        self.scroll_speed = 2
        self.max_detections = 20
        self.update_interval = 5
        self.db_path = None
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from birdnet.conf"""
        config_file = '/etc/birdnet/birdnet.conf'
        
        if not os.path.exists(config_file):
            log.warning(f'Configuration file not found: {config_file}')
            return
        
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if key == 'TFT_ENABLED':
                            self.enabled = value == '1'
                        elif key == 'TFT_TYPE':
                            self.device_type = value.lower()
                        elif key == 'TFT_ROTATION':
                            self.rotation = int(value)
                        elif key == 'TFT_FONT_SIZE':
                            self.font_size = int(value)
                        elif key == 'TFT_SCROLL_SPEED':
                            self.scroll_speed = int(value)
                        elif key == 'TFT_MAX_DETECTIONS':
                            self.max_detections = int(value)
                        elif key == 'TFT_UPDATE_INTERVAL':
                            self.update_interval = int(value)
                        elif key == 'DB_PATH':
                            self.db_path = value
            
            log.info('Configuration loaded successfully')
            log.info(f'TFT Enabled: {self.enabled}')
            log.info(f'Display Type: {self.device_type}')
            log.info(f'Rotation: {self.rotation}°')
            
        except Exception as e:
            log.error(f'Error loading configuration: {e}')
    
    def get_db_path(self):
        """Get database path"""
        if self.db_path:
            return self.db_path
        
        # Try common locations
        home = os.environ.get('HOME', '/home/pi')
        possible_paths = [
            f'{home}/BirdNET-Pi/scripts/birds.db',
            f'{home}/BirdSongs/Extracted/birds.db',
            '/var/lib/birdnet/birds.db',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                log.info(f'Found database at: {path}')
                return path
        
        log.warning('Database not found in common locations')
        return None


class TFTDisplay:
    """TFT Display handler"""
    
    def __init__(self, config):
        """Initialize TFT display"""
        self.config = config
        self.device = None
        self.font = None
        self.width = 240
        self.height = 320
        self.scroll_offset = 0
        self.detections = []
        
        self.initialize_display()
        self.load_font()
    
    def initialize_display(self):
        """Initialize the display device"""
        if not LUMA_AVAILABLE:
            log.error('luma.lcd library not available')
            return False
        
        try:
            # Create SPI interface
            serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
            
            # Create device based on type
            device_type = self.config.device_type.lower()
            
            if device_type == 'ili9341':
                self.device = ili9341(serial, rotate=self.config.rotation // 90)
                self.width, self.height = 240, 320
            elif device_type in ['st7735', 'st7735r']:
                self.device = st7735(serial, rotate=self.config.rotation // 90)
                self.width, self.height = 128, 160
            elif device_type == 'st7789':
                self.device = st7789v(serial, rotate=self.config.rotation // 90)
                self.width, self.height = 240, 240
            elif device_type == 'ili9488':
                self.device = ili9488(serial, rotate=self.config.rotation // 90)
                self.width, self.height = 320, 480
            else:
                log.error(f'Unknown display type: {device_type}')
                return False
            
            # Adjust width/height for portrait mode
            if self.config.rotation in [90, 270]:
                self.width, self.height = self.height, self.width
            
            log.info(f'Display initialized: {self.width}x{self.height}')
            return True
            
        except Exception as e:
            log.error(f'Failed to initialize display: {e}')
            self.device = None
            return False
    
    def load_font(self):
        """Load font for text rendering"""
        if not PIL_AVAILABLE:
            return
        
        try:
            # Try to load a TrueType font
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self.font = ImageFont.truetype(font_path, self.config.font_size)
                    log.info(f'Loaded font: {font_path}')
                    return
            
            # Fallback to default font
            self.font = ImageFont.load_default()
            log.warning('Using default font')
            
        except Exception as e:
            log.error(f'Error loading font: {e}')
            self.font = ImageFont.load_default()
    
    def render_frame(self):
        """Render current frame to display"""
        if not self.device:
            return
        
        try:
            with canvas(self.device) as draw:
                # Clear background
                draw.rectangle((0, 0, self.width, self.height), fill='black')
                
                # Title
                title = "BirdNET-Pi Detections"
                draw.text((5, 5), title, fill='white', font=self.font)
                
                # Separator line
                draw.line((0, 25, self.width, 25), fill='white')
                
                # Render detections
                y_pos = 30 - self.scroll_offset
                line_height = self.config.font_size + 4
                
                for detection in self.detections:
                    if y_pos > -line_height and y_pos < self.height:
                        # Format: "Common Name (Confidence%)"
                        text = f"{detection['common_name']}"
                        draw.text((5, y_pos), text, fill='white', font=self.font)
                        
                        # Confidence on next line
                        conf_text = f"  {detection['confidence']:.1f}%"
                        draw.text((5, y_pos + line_height), conf_text, fill='lightgreen', font=self.font)
                        
                        y_pos += line_height * 2 + 2
                    else:
                        y_pos += line_height * 2 + 2
                
                # Draw timestamp at bottom
                now = datetime.now().strftime('%H:%M:%S')
                draw.text((5, self.height - 15), now, fill='gray', font=self.font)
                
        except Exception as e:
            log.error(f'Error rendering frame: {e}')
    
    def update_scroll(self):
        """Update scroll position"""
        total_height = len(self.detections) * (self.config.font_size + 4) * 2
        max_scroll = max(0, total_height - self.height + 50)
        
        self.scroll_offset += self.config.scroll_speed
        
        if self.scroll_offset > max_scroll:
            self.scroll_offset = 0
    
    def update_detections(self, detections):
        """Update detection list"""
        self.detections = detections
        self.scroll_offset = 0
    
    def show_message(self, message):
        """Show a simple message on screen"""
        if not self.device:
            return
        
        try:
            with canvas(self.device) as draw:
                draw.rectangle((0, 0, self.width, self.height), fill='black')
                
                # Center text
                text_width = len(message) * 8
                x = (self.width - text_width) // 2
                y = self.height // 2
                
                draw.text((x, y), message, fill='white', font=self.font)
                
        except Exception as e:
            log.error(f'Error showing message: {e}')


class DetectionReader:
    """Read bird detections from database"""
    
    def __init__(self, db_path):
        """Initialize database reader"""
        self.db_path = db_path
    
    def get_recent_detections(self, max_count=20, hours=24):
        """Get recent bird detections"""
        if not self.db_path or not os.path.exists(self.db_path):
            log.warning('Database not available')
            return []
        
        try:
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            cursor = conn.cursor()
            
            # Get detections from last N hours
            since = datetime.now() - timedelta(hours=hours)
            
            query = """
                SELECT Com_Name, Confidence, Date, Time
                FROM detections
                WHERE Date >= ?
                ORDER BY Date DESC, Time DESC
                LIMIT ?
            """
            
            cursor.execute(query, (since.strftime('%Y-%m-%d'), max_count))
            rows = cursor.fetchall()
            
            detections = []
            for row in rows:
                detections.append({
                    'common_name': row[0],
                    'confidence': row[1] * 100,  # Convert to percentage
                    'date': row[2],
                    'time': row[3]
                })
            
            conn.close()
            log.debug(f'Retrieved {len(detections)} detections')
            return detections
            
        except Exception as e:
            log.error(f'Error reading detections: {e}')
            return []


def main():
    """Main function"""
    global shutdown
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log.info('BirdNET-Pi TFT Display starting...')
    
    # Load configuration
    config = TFTDisplayConfig()
    
    if not config.enabled:
        log.info('TFT display is disabled in configuration')
        log.info('Enable it by setting TFT_ENABLED=1 in /etc/birdnet/birdnet.conf')
        sys.exit(0)
    
    # Check for required libraries
    if not PIL_AVAILABLE or not LUMA_AVAILABLE:
        log.error('Required libraries not available')
        log.error('Install with: pip install Pillow luma.lcd')
        sys.exit(1)
    
    # Initialize display
    display = TFTDisplay(config)
    
    if not display.device:
        log.error('Failed to initialize display. Running in fallback mode.')
        log.info('Display will not be available, but service will continue running.')
        
        # Keep running but do nothing (fallback mode)
        while not shutdown:
            time.sleep(config.update_interval)
        
        log.info('TFT Display daemon stopped (fallback mode)')
        sys.exit(0)
    
    # Show startup message
    display.show_message('BirdNET-Pi\nStarting...')
    time.sleep(2)
    
    # Initialize detection reader
    db_path = config.get_db_path()
    if not db_path:
        log.error('Database not found')
        display.show_message('Database\nNot Found')
        time.sleep(5)
        sys.exit(1)
    
    reader = DetectionReader(db_path)
    
    # Main loop
    log.info('Entering main display loop')
    last_update = 0
    frame_counter = 0
    
    while not shutdown:
        try:
            current_time = time.time()
            
            # Update detections periodically
            if current_time - last_update > config.update_interval:
                detections = reader.get_recent_detections(
                    max_count=config.max_detections,
                    hours=24
                )
                
                if detections:
                    display.update_detections(detections)
                    log.info(f'Updated display with {len(detections)} detections')
                else:
                    log.info('No recent detections')
                
                last_update = current_time
            
            # Render frame
            display.render_frame()
            
            # Update scroll
            display.update_scroll()
            
            # Control frame rate
            frame_counter += 1
            if frame_counter % 10 == 0:
                log.debug(f'Rendered {frame_counter} frames')
            
            time.sleep(0.1)  # ~10 FPS
            
        except Exception as e:
            log.error(f'Error in main loop: {e}')
            time.sleep(1)
    
    # Cleanup
    log.info('TFT Display daemon stopped')
    if display.device:
        display.show_message('BirdNET-Pi\nStopped')
        time.sleep(1)


if __name__ == '__main__':
    main()
