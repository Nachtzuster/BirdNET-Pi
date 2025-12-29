# TFT Screen Support for BirdNET-Pi

## English Guide

### Overview
BirdNET-Pi now supports small TFT displays with XPT2046 touch controllers. The display shows detected bird species with their confidence scores in a scrolling portrait mode, while simultaneously maintaining HDMI output to your monitor.

### Supported Hardware
- **Raspberry Pi**: Tested on Raspberry Pi 4B with Trixie distribution
- **TFT Displays**:
  - ILI9341 (240x320) - Most common cheap displays
  - ST7735 (128x160) - Small displays  
  - ST7789 (240x240) - Square displays
  - ILI9488 (320x480) - Larger displays
- **Touch Controller**: XPT2046 (ADS7846 compatible)

### Features
- ✅ Simultaneous HDMI + TFT output
- ✅ Portrait mode display orientation
- ✅ Scrolling species list with confidence scores
- ✅ Automatic fallback if TFT not connected
- ✅ Easy rollback to original configuration
- ✅ Configurable update intervals and display settings

### Installation

#### Step 1: Detect TFT Display
First, check if your TFT display is detected:

```bash
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

If your display is not detected, proceed with installation.

#### Step 2: Install TFT Support
Run the installation script:

```bash
cd ~/BirdNET-Pi/scripts
./install_tft.sh
```

The installer will:
1. Backup your current configuration
2. Install required packages
3. Configure your display type
4. Set up touchscreen support
5. Add TFT configuration to BirdNET-Pi

Follow the prompts to select your display type.

#### Step 3: Reboot
After installation, reboot your Raspberry Pi:

```bash
sudo reboot
```

#### Step 4: Verify Installation
After reboot, verify the TFT is detected:

```bash
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

#### Step 5: Enable TFT Display
Edit the BirdNET-Pi configuration:

```bash
sudo nano /etc/birdnet/birdnet.conf
```

Find the TFT configuration section and set:
```bash
TFT_ENABLED=1
```

Save and exit (Ctrl+X, Y, Enter).

#### Step 6: Start the Display Service
Enable and start the TFT display service:

```bash
sudo systemctl enable tft_display.service
sudo systemctl start tft_display.service
```

Check the service status:
```bash
sudo systemctl status tft_display.service
```

### Configuration Options

Edit `/etc/birdnet/birdnet.conf` to customize:

```bash
# TFT Display Configuration
TFT_ENABLED=1                    # 0=disabled, 1=enabled
TFT_DEVICE=/dev/fb1             # Framebuffer device
TFT_ROTATION=90                 # 0, 90, 180, 270 (portrait = 90 or 270)
TFT_FONT_SIZE=12                # Font size for species text
TFT_SCROLL_SPEED=2              # Scroll speed (lines per second)
TFT_MAX_DETECTIONS=20           # Number of recent detections to show
TFT_UPDATE_INTERVAL=5           # Seconds between database updates
TFT_TYPE=ili9341                # Display type
```

After changing configuration, restart the service:
```bash
sudo systemctl restart tft_display.service
```

### Troubleshooting

#### Display shows nothing
1. Check if SPI is enabled: `ls /dev/spi*`
2. Check framebuffer devices: `ls /dev/fb*`
3. Verify service is running: `sudo systemctl status tft_display.service`
4. Check logs: `journalctl -u tft_display.service -f`

#### Touch not working
1. Check input devices: `ls /dev/input/event*`
2. Test with evtest: `sudo evtest`
3. Verify XPT2046 in device tree: `sudo dmesg | grep -i xpt2046`

#### Wrong orientation
Edit `/etc/birdnet/birdnet.conf` and change `TFT_ROTATION`:
- 0 = Normal landscape
- 90 = Portrait (rotated right)
- 180 = Inverted landscape
- 270 = Portrait (rotated left)

#### Performance issues
Increase `TFT_UPDATE_INTERVAL` to reduce CPU usage:
```bash
TFT_UPDATE_INTERVAL=10  # Update every 10 seconds instead of 5
```

### Rollback

To remove TFT support and restore original configuration:

```bash
cd ~/BirdNET-Pi/scripts
./rollback_tft.sh
```

This will:
1. Stop and disable the TFT service
2. Restore original configuration files
3. Remove TFT-specific settings
4. Optionally remove installed packages

After rollback, reboot your system.

### Technical Details

#### GPIO Pin Usage
Typical SPI TFT connection uses:
- **GPIO 8 (CE0)**: SPI Chip Select
- **GPIO 10 (MOSI)**: SPI Data Out
- **GPIO 9 (MISO)**: SPI Data In
- **GPIO 11 (SCLK)**: SPI Clock
- **GPIO 24**: Display DC (Data/Command)
- **GPIO 25**: Display Reset (or XPT2046 IRQ)

#### Display Architecture
```
┌─────────────────┐
│   HDMI Monitor  │ ← /dev/fb0 (Primary framebuffer)
└─────────────────┘
         ↓
    (mirrored to)
         ↓
┌─────────────────┐
│   TFT Display   │ ← /dev/fb1 (Secondary framebuffer)
└─────────────────┘
```

#### Service Dependencies
```
birdnet_analysis.service (Detects birds)
         ↓
    birds.db (SQLite database)
         ↓
tft_display.service (Reads and displays)
```

---

## Nederlandse Gids

### Overzicht
BirdNET-Pi ondersteunt nu kleine TFT schermen met XPT2046 touch controllers. Het scherm toont gedetecteerde vogelsoorten met hun waarschijnlijkheidsscores in scrollende portrait modus, terwijl de HDMI output naar uw monitor behouden blijft.

### Ondersteunde Hardware
- **Raspberry Pi**: Getest op Raspberry Pi 4B met Trixie distributie
- **TFT Displays**:
  - ILI9341 (240x320) - Meest voorkomende goedkope displays
  - ST7735 (128x160) - Kleine displays
  - ST7789 (240x240) - Vierkante displays
  - ILI9488 (320x480) - Grotere displays
- **Touch Controller**: XPT2046 (ADS7846 compatibel)

### Functies
- ✅ Simultane HDMI + TFT output
- ✅ Portrait mode weergave orientatie
- ✅ Scrollende soortenlijst met waarschijnlijkheidsscores
- ✅ Automatische fallback als TFT niet aangesloten
- ✅ Eenvoudige rollback naar originele configuratie
- ✅ Configureerbare update intervallen en display instellingen

### Installatie

#### Stap 1: Detecteer TFT Display
Controleer eerst of uw TFT display wordt gedetecteerd:

```bash
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

Als uw display niet wordt gedetecteerd, ga verder met installatie.

#### Stap 2: Installeer TFT Ondersteuning
Voer het installatie script uit:

```bash
cd ~/BirdNET-Pi/scripts
./install_tft.sh
```

De installer zal:
1. Uw huidige configuratie backuppen
2. Benodigde pakketten installeren
3. Uw display type configureren
4. Touchscreen ondersteuning instellen
5. TFT configuratie toevoegen aan BirdNET-Pi

Volg de prompts om uw display type te selecteren.

#### Stap 3: Herstart
Na installatie, herstart uw Raspberry Pi:

```bash
sudo reboot
```

#### Stap 4: Verifieer Installatie
Na herstart, verifieer dat de TFT gedetecteerd wordt:

```bash
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

#### Stap 5: Schakel TFT Display In
Bewerk de BirdNET-Pi configuratie:

```bash
sudo nano /etc/birdnet/birdnet.conf
```

Zoek de TFT configuratie sectie en stel in:
```bash
TFT_ENABLED=1
```

Opslaan en afsluiten (Ctrl+X, Y, Enter).

#### Stap 6: Start de Display Service
Schakel in en start de TFT display service:

```bash
sudo systemctl enable tft_display.service
sudo systemctl start tft_display.service
```

Controleer de service status:
```bash
sudo systemctl status tft_display.service
```

### Configuratie Opties

Bewerk `/etc/birdnet/birdnet.conf` om aan te passen:

```bash
# TFT Display Configuratie
TFT_ENABLED=1                    # 0=uitgeschakeld, 1=ingeschakeld
TFT_DEVICE=/dev/fb1             # Framebuffer apparaat
TFT_ROTATION=90                 # 0, 90, 180, 270 (portrait = 90 of 270)
TFT_FONT_SIZE=12                # Lettergrootte voor soorten tekst
TFT_SCROLL_SPEED=2              # Scroll snelheid (regels per seconde)
TFT_MAX_DETECTIONS=20           # Aantal recente detecties om te tonen
TFT_UPDATE_INTERVAL=5           # Seconden tussen database updates
TFT_TYPE=ili9341                # Display type
```

Na het wijzigen van de configuratie, herstart de service:
```bash
sudo systemctl restart tft_display.service
```

### Probleemoplossing

#### Display toont niets
1. Controleer of SPI is ingeschakeld: `ls /dev/spi*`
2. Controleer framebuffer apparaten: `ls /dev/fb*`
3. Verifieer dat service draait: `sudo systemctl status tft_display.service`
4. Controleer logs: `journalctl -u tft_display.service -f`

#### Touch werkt niet
1. Controleer input apparaten: `ls /dev/input/event*`
2. Test met evtest: `sudo evtest`
3. Verifieer XPT2046 in device tree: `sudo dmesg | grep -i xpt2046`

#### Verkeerde orientatie
Bewerk `/etc/birdnet/birdnet.conf` en wijzig `TFT_ROTATION`:
- 0 = Normaal landschap
- 90 = Portrait (rechts gedraaid)
- 180 = Omgekeerd landschap
- 270 = Portrait (links gedraaid)

#### Prestatie problemen
Verhoog `TFT_UPDATE_INTERVAL` om CPU gebruik te verminderen:
```bash
TFT_UPDATE_INTERVAL=10  # Update elke 10 seconden i.p.v. 5
```

### Rollback

Om TFT ondersteuning te verwijderen en originele configuratie te herstellen:

```bash
cd ~/BirdNET-Pi/scripts
./rollback_tft.sh
```

Dit zal:
1. De TFT service stoppen en uitschakelen
2. Originele configuratie bestanden herstellen
3. TFT-specifieke instellingen verwijderen
4. Optioneel geïnstalleerde pakketten verwijderen

Na rollback, herstart uw systeem.

### Technische Details

#### GPIO Pin Gebruik
Typische SPI TFT connectie gebruikt:
- **GPIO 8 (CE0)**: SPI Chip Select
- **GPIO 10 (MOSI)**: SPI Data Out
- **GPIO 9 (MISO)**: SPI Data In
- **GPIO 11 (SCLK)**: SPI Clock
- **GPIO 24**: Display DC (Data/Command)
- **GPIO 25**: Display Reset (of XPT2046 IRQ)

#### Display Architectuur
```
┌─────────────────┐
│   HDMI Monitor  │ ← /dev/fb0 (Primaire framebuffer)
└─────────────────┘
         ↓
    (gespiegeld naar)
         ↓
┌─────────────────┐
│   TFT Display   │ ← /dev/fb1 (Secundaire framebuffer)
└─────────────────┘
```

#### Service Afhankelijkheden
```
birdnet_analysis.service (Detecteert vogels)
         ↓
    birds.db (SQLite database)
         ↓
tft_display.service (Leest en toont)
```

## Support

Voor vragen of problemen:
1. Check de audit document: `docs/TFT_SCREEN_AUDIT.md`
2. Controleer de logs: `journalctl -u tft_display.service`
3. Open een issue op GitHub met:
   - Output van `detect_tft.sh`
   - Output van `sudo systemctl status tft_display.service`
   - Relevant log output

## License

This TFT display support is part of BirdNET-Pi and follows the same license terms.
