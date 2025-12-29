# TFT Screen Support Audit - XPT2046 Touch Controller

## Overview
Dit document beschrijft de implementatie van TFT scherm ondersteuning voor BirdNET-Pi met de XPT2046 touch controller, met simultane HDMI output.

## Huidige Situatie

### Bestaande Systeem Architectuur
1. **Display Output**: Momenteel geen dedicated display output functionaliteit
2. **Services**: Systemd services voor core functionaliteit (analyse, recording, stats)
3. **Installatie**: `newinstaller.sh` → `install_birdnet.sh` → `install_services.sh`
4. **Configuratie**: `/etc/birdnet/birdnet.conf` voor system settings
5. **Python Environment**: Virtual environment in `~/BirdNET-Pi/birdnet/`

### Detectie Systeem
- BirdNET analyseren continu audio in `birdnet_analysis.py`
- Detecties worden geschreven naar SQLite database
- Real-time notificaties via Apprise mogelijk
- Streamlit-based web interface voor statistieken

## Vereisten voor TFT Screen Support

### Hardware Vereisten
- Raspberry Pi 4B (getest op Trixie distributie)
- TFT scherm met XPT2046 touch controller
- SPI interface connectie (typisch GPIO pins)
- HDMI blijft beschikbaar voor monitor

### Software Vereisten

#### Kernel Drivers
- `fbtft` module voor framebuffer support
- `spi` modules voor SPI communicatie
- Touch controller drivers

#### User-space Tools
- `fbcp-ili9341` of vergelijkbare framebuffer copy tool voor dual display
- `evtest` voor touchscreen testing
- `xinput-calibrator` voor touchscreen calibratie (indien X11)
- `tslib` voor touchscreen library support

#### Python Packages
- `Pillow` (PIL) - reeds geïnstalleerd
- `pygame` of `luma.lcd` voor framebuffer rendering
- Optioneel: `evdev` voor direct input handling

### Configuratie Vereisten
1. `/boot/firmware/config.txt` aanpassingen voor display driver
2. Device tree overlays voor touchscreen
3. Framebuffer device configuration
4. X11 configuratie voor dual display (indien GUI needed)

## Voorgestelde Implementatie

### 1. Detectie Script (`scripts/detect_tft.sh`)
```bash
# Detecteert aanwezigheid van:
# - XPT2046 touchscreen controller
# - SPI TFT displays
# - Geeft terug: found/not-found status
```

### 2. Installatie Script (`scripts/install_tft.sh`)
```bash
# Installeert benodigde packages:
# - fbcp-ili9341 (compile van source)
# - touchscreen libraries
# - Configureert /boot/firmware/config.txt
# - Backup maken van originele configuraties
```

### 3. TFT Display Service (`scripts/tft_display.py`)
```python
# Python daemon die:
# - Leest laatste detecties uit database
# - Toont scrollende lijst van species + confidence
# - Portrait mode orientatie
# - Update elke N seconden
# - Graceful fallback als display niet beschikbaar
```

### 4. Configuratie Opties (`/etc/birdnet/birdnet.conf`)
```bash
TFT_ENABLED=0                    # Enable/disable TFT display
TFT_DEVICE=/dev/fb1             # Framebuffer device
TFT_ROTATION=90                 # 0, 90, 180, 270 (portrait = 90 or 270)
TFT_FONT_SIZE=12                # Font size for species text
TFT_SCROLL_SPEED=2              # Scroll speed (lines per second)
TFT_MAX_DETECTIONS=20           # Number of recent detections to show
TFT_UPDATE_INTERVAL=5           # Seconds between updates
```

### 5. Rollback Script (`scripts/rollback_tft.sh`)
```bash
# Herstel originele configuratie:
# - Restore /boot/firmware/config.txt backup
# - Stop en disable TFT service
# - Verwijder display-specific configuraties
```

## Implementatie Stappen

### Stap 1: Detectie Infrastructuur
- [x] Audit document aanmaken
- [ ] `detect_tft.sh` script aanmaken
- [ ] Detectie testen voor XPT2046
- [ ] Detectie testen voor SPI displays

### Stap 2: Package Installatie
- [ ] `install_tft.sh` aanmaken met package dependencies
- [ ] fbcp-ili9341 build script
- [ ] Touchscreen library installatie
- [ ] Config.txt modificatie scripts

### Stap 3: Display Applicatie
- [ ] `tft_display.py` basis structuur
- [ ] Database query voor recente detecties
- [ ] Framebuffer rendering code
- [ ] Portrait mode orientatie
- [ ] Scrolling text implementatie

### Stap 4: Service Integratie
- [ ] Systemd service file voor TFT display
- [ ] Integratie in `install_services.sh`
- [ ] Auto-start configuratie
- [ ] Dependency management (start na database)

### Stap 5: Configuratie & Testing
- [ ] Config opties toevoegen aan birdnet.conf
- [ ] Rollback script implementeren
- [ ] Test zonder TFT (fallback)
- [ ] Test met TFT
- [ ] HDMI + TFT simultaan testen

## Risico's en Mitigaties

### Risico 1: Hardware Incompatibiliteit
**Mitigatie**: Detectie script en graceful fallback

### Risico 2: Performance Impact
**Mitigatie**: Configureerbare update interval, low-priority service

### Risico 3: SPI/GPIO Conflicts
**Mitigatie**: Documenteer GPIO pin usage, detecteer conflicts

### Risico 4: Boot Failures na Config Changes
**Mitigatie**: Backup van config files, rollback script

## Technische Details

### Framebuffer Architecture
```
┌─────────────┐
│   HDMI      │ /dev/fb0 (primary)
└─────────────┘
       │
       ↓
┌─────────────┐
│  fbcp tool  │ Copy fb0 → fb1
└─────────────┘
       │
       ↓
┌─────────────┐
│  TFT Screen │ /dev/fb1 (secondary)
└─────────────┘
```

### Data Flow
```
BirdNET Analysis → SQLite DB → TFT Display Script → Framebuffer → TFT Screen
                                                  → HDMI (via fb0)
```

### Service Dependencies
```
birdnet_analysis.service
       ↓
 (database writes)
       ↓
tft_display.service (After=birdnet_analysis.service)
```

## Testing Strategie

### Unit Tests
- Detectie script logic
- Config parsing
- Database queries

### Integration Tests
- Service start/stop
- Fallback bij geen TFT
- HDMI + TFT simultaan

### Hardware Tests (Raspberry Pi 4B)
- XPT2046 detectie
- Display rendering
- Touchscreen functionaliteit
- Portrait orientatie
- Rollback procedure

## Documentatie Vereisten

1. **Installatie Guide**: Stap-voor-stap TFT setup
2. **Configuration Guide**: Alle TFT config opties
3. **Troubleshooting Guide**: Veelvoorkomende problemen
4. **Hardware Compatibility List**: Geteste TFT displays
5. **Rollback Procedure**: Hoe terug naar origineel

## Conclusie

Deze implementatie voorziet in:
- ✅ Simultane HDMI + TFT output
- ✅ Portrait mode display
- ✅ Scrollende species detecties
- ✅ Graceful fallback zonder TFT
- ✅ Rollback mogelijkheid
- ✅ Trixie distributie support
- ✅ XPT2046 touchscreen support

Volgende stap: Begin met implementatie van detectie en installatie scripts.
