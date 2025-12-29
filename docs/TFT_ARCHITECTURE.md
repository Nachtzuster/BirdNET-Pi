# TFT Screen Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BirdNET-Pi System                            │
│                                                                   │
│  ┌─────────────────┐         ┌──────────────────┐               │
│  │ Microphone      │────────▶│ birdnet_         │               │
│  │ Audio Input     │         │ recording.service│               │
│  └─────────────────┘         └────────┬─────────┘               │
│                                        │                         │
│                                        ▼                         │
│                              ┌──────────────────┐                │
│                              │ Audio Files      │                │
│                              │ (WAV)            │                │
│                              └────────┬─────────┘                │
│                                        │                         │
│                                        ▼                         │
│                              ┌──────────────────┐                │
│                              │ birdnet_         │                │
│                              │ analysis.service │                │
│                              └────────┬─────────┘                │
│                                        │                         │
│                                        ▼                         │
│                              ┌──────────────────┐                │
│                              │ SQLite Database  │                │
│                              │ birds.db         │                │
│                              └────────┬─────────┘                │
│                                        │                         │
│                    ┌───────────────────┼───────────────────┐    │
│                    │                   │                   │    │
│                    ▼                   ▼                   ▼    │
│          ┌──────────────┐    ┌──────────────┐   ┌──────────────┐│
│          │ Web Interface│    │ TFT Display  │   │ Notifications││
│          │ (Caddy/PHP)  │    │ Service ⭐   │   │ (Apprise)    ││
│          └──────────────┘    └──────┬───────┘   └──────────────┘│
│                                      │                            │
└──────────────────────────────────────┼────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Display Hardware                               │
│                                                                   │
│  ┌─────────────────┐              ┌──────────────────┐          │
│  │ /dev/fb0        │              │ /dev/fb1         │          │
│  │ HDMI Monitor    │              │ TFT Display      │          │
│  │                 │              │                  │          │
│  │ 1920x1080       │              │ 240x320          │          │
│  │ (Primary)       │              │ (Portrait)       │          │
│  │                 │              │                  │          │
│  │ Web Interface   │              │ ┌──────────────┐ │          │
│  │ Statistics      │              │ │BirdNET-Pi    │ │          │
│  │ Spectrograms    │              │ │Detections    │ │          │
│  │                 │              │ ├──────────────┤ │          │
│  │                 │              │ │              │ │          │
│  │                 │              │ │Common Name   │ │          │
│  │                 │              │ │  85.3%       │ │          │
│  │                 │              │ │              │ │          │
│  │                 │              │ │Species 2     │ │          │
│  │                 │              │ │  78.1%       │ │          │
│  │                 │              │ │              │ │          │
│  │                 │              │ │...scrolling  │ │          │
│  │                 │              │ │              │ │          │
│  │                 │              │ │18:43:47      │ │          │
│  └─────────────────┘              │ └──────────────┘ │          │
│                                   │                  │          │
│                                   │  XPT2046 Touch   │          │
│                                   │  Controller      │          │
│                                   └──────────────────┘          │
└──────────────────────────────────────────────────────────────────┘
```

## Installation Flow

```
User runs: ./install_tft.sh
         │
         ▼
┌────────────────────┐
│ Create Backups     │ → ~/BirdNET-Pi/tft_backups/
│ - config.txt       │   - config.txt.TIMESTAMP
│ - birdnet.conf     │   - birdnet.conf.TIMESTAMP
└────────┬───────────┘   - last_backup.txt
         │
         ▼
┌────────────────────┐
│ Install Packages   │ → apt: build-essential, cmake, evtest, etc.
│ System Level       │   pip: luma.lcd, luma.core
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Select Display     │ → User chooses:
│ Type               │   - ILI9341, ST7735, ST7789, ILI9488, ILI9486, etc.
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Configure          │ → /boot/firmware/config.txt:
│ Boot Config        │   - dtparam=spi=on
└────────┬───────────┘   - dtoverlay=piscreen,rotate=90
         │               - dtoverlay=ads7846 (touchscreen)
         ▼
┌────────────────────┐
│ Configure          │ → /etc/birdnet/birdnet.conf:
│ BirdNET-Pi         │   - TFT_ENABLED=0 (default off)
└────────┬───────────┘   - TFT_ROTATION=90
         │               - TFT_FONT_SIZE=12
         │               - etc.
         ▼
┌────────────────────┐
│ Reboot Required    │
└────────────────────┘
         │
         ▼
┌────────────────────┐
│ User Enables TFT   │ → Edit birdnet.conf:
│ in Config          │   TFT_ENABLED=1
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Start Service      │ → systemctl enable tft_display.service
└────────────────────┘   systemctl start tft_display.service
```

## Service Dependencies

```
System Boot
     │
     ▼
Multi-user.target
     │
     ├──────────────────────┐
     │                      │
     ▼                      ▼
birdnet_recording      birdnet_analysis
  .service               .service
     │                      │
     │                      ▼
     │                  birds.db
     │                      │
     │                      ▼
     │              ┌───────────────┐
     │              │ tft_display   │ ⭐ NEW
     │              │ .service      │
     │              │               │
     │              │ After=        │
     │              │ birdnet_      │
     │              │ analysis      │
     │              └───────────────┘
     │
     └────────────▶ Other services...
```

## Data Flow

```
┌──────────────┐
│ Audio Stream │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ BirdNET Analysis │ → AI Detection
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ SQLite Database (birds.db)           │
│                                      │
│ Table: detections                    │
│ ├─ Com_Name    (Common Name)         │
│ ├─ Sci_Name    (Scientific Name)     │
│ ├─ Confidence  (0.0 - 1.0)           │
│ ├─ Date        (YYYY-MM-DD)          │
│ └─ Time        (HH:MM:SS)            │
└──────┬───────────────────────────────┘
       │
       ├─────────────────┬──────────────┐
       │                 │              │
       ▼                 ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Web          │  │ TFT Display  │  │ Notifications│
│ Interface    │  │ Daemon       │  │              │
│              │  │              │  │              │
│ PHP queries  │  │ Python reads │  │ Apprise      │
│ Display      │  │ Query:       │  │ alerts       │
│ charts,      │  │              │  │              │
│ tables,      │  │ SELECT       │  │              │
│ stats        │  │ Com_Name,    │  │              │
│              │  │ Confidence   │  │              │
│              │  │ FROM         │  │              │
│              │  │ detections   │  │              │
│              │  │ WHERE        │  │              │
│              │  │ Date >= ?    │  │              │
│              │  │ ORDER BY     │  │              │
│              │  │ Date DESC    │  │              │
│              │  │ LIMIT 20     │  │              │
│              │  │              │  │              │
│              │  └──────┬───────┘  │              │
│              │         │          │              │
└──────────────┘         ▼          └──────────────┘
                  ┌──────────────┐
                  │ Format &     │
                  │ Render       │
                  │              │
                  │ Species Name │
                  │   85.3%      │
                  │              │
                  │ Scroll ↑     │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ luma.lcd     │
                  │ library      │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ /dev/fb1     │
                  │ Framebuffer  │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ TFT Display  │
                  │ Hardware     │
                  └──────────────┘
```

## Fallback Mechanism

```
tft_display.service starts
         │
         ▼
    ┌─────────┐
    │ Check   │
    │ Config  │
    └────┬────┘
         │
    TFT_ENABLED?
         │
    ┌────┴────┐
    │         │
   NO        YES
    │         │
    │         ▼
    │    ┌─────────┐
    │    │ Init    │
    │    │ Display │
    │    └────┬────┘
    │         │
    │    Hardware OK?
    │         │
    │    ┌────┴────┐
    │   NO        YES
    │    │         │
    ▼    ▼         ▼
┌──────────────┐ ┌──────────────┐
│ Exit with    │ │ Start        │
│ status 0     │ │ Main Loop    │
│              │ │              │
│ Log:         │ │ - Query DB   │
│ "Disabled"   │ │ - Render     │
│ or           │ │ - Scroll     │
│ "Fallback"   │ │ - Update     │
│              │ └──────────────┘
│ No impact    │
│ on system    │
└──────────────┘
```

## Rollback Process

```
User runs: ./rollback_tft.sh
         │
         ▼
┌────────────────────┐
│ Show Available     │
│ Backups            │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Confirm Rollback?  │────▶ NO ───▶ Exit
└────────┬───────────┘
         │ YES
         ▼
┌────────────────────┐
│ Stop Service       │ → systemctl stop tft_display.service
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Disable Service    │ → systemctl disable tft_display.service
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Restore Configs    │ → cp backups/* to original locations
│ - config.txt       │
│ - birdnet.conf     │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Remove Service     │ → rm templates/tft_display.service
│ File               │   systemctl daemon-reload
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Remove Packages?   │────▶ Optional
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Remove Backups?    │────▶ Optional
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Reboot Required    │
└────────────────────┘
         │
         ▼
    System restored
    to pre-TFT state
```

## File Structure

```
BirdNET-Pi/
│
├── docs/
│   ├── TFT_SCREEN_AUDIT.md              ⭐ Technical audit
│   ├── TFT_SCREEN_SETUP.md              ⭐ User guide (EN+NL)
│   ├── TFT_TESTING_GUIDE.md             ⭐ Testing procedures
│   ├── TFT_IMPLEMENTATION_SUMMARY.md    ⭐ Dutch summary
│   └── TFT_ARCHITECTURE.md              ⭐ This file
│
├── scripts/
│   ├── detect_tft.sh                    ⭐ Detection script
│   ├── install_tft.sh                   ⭐ Installation
│   ├── rollback_tft.sh                  ⭐ Rollback
│   ├── tft_display.py                   ⭐ Display daemon
│   ├── install_services.sh              ✏️  Modified
│   │
│   └── ... (other BirdNET-Pi scripts)
│
├── templates/
│   ├── tft_display.service              ⭐ Created at runtime
│   └── ... (other service templates)
│
└── tft_backups/                         ⭐ Created by install_tft.sh
    ├── config.txt.TIMESTAMP
    ├── birdnet.conf.TIMESTAMP
    └── last_backup.txt
```

## Configuration Files

```
/boot/firmware/config.txt:
┌─────────────────────────────────────┐
│ # Enable SPI                        │
│ dtparam=spi=on                      │
│                                     │
│ # TFT Display overlay               │
│ dtoverlay=piscreen,speed=16000000,  │
│           rotate=90                 │
│                                     │
│ # XPT2046 Touchscreen               │
│ dtoverlay=ads7846,cs=1,penirq=25,   │
│           speed=50000,swapxy=0      │
└─────────────────────────────────────┘

/etc/birdnet/birdnet.conf:
┌─────────────────────────────────────┐
│ # TFT Display Configuration         │
│ TFT_ENABLED=0                       │
│ TFT_DEVICE=/dev/fb1                 │
│ TFT_ROTATION=90                     │
│ TFT_FONT_SIZE=12                    │
│ TFT_SCROLL_SPEED=2                  │
│ TFT_MAX_DETECTIONS=20               │
│ TFT_UPDATE_INTERVAL=5               │
│ TFT_TYPE=ili9341                    │
└─────────────────────────────────────┘
```

---

**Legend:**
- ⭐ New files added
- ✏️  Existing files modified
- → Action or data flow
- ▼ Sequential flow
