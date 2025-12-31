# TFT Display Boot Sequence Uitleg (Nederlands)

## Vraag van Gebruiker

> "Kan jij niet ergens het activeren van het TFT scherm activeren bij het opstarten van de RPi 4B zelf, nog voordat BirdNET-Pi-MigCount opgestart is?"

## Antwoord: Dit Gebeurt Al!

Het TFT scherm wordt **AL** geactiveerd tijdens het opstarten van de Raspberry Pi, **VOORDAT** BirdNET-Pi start. Dit is hoe het werkt:

## Boot Volgorde

### 1. Raspberry Pi Bootloader (Eerste Fase)
```
[0s] Raspberry Pi opstart
     ↓
[1s] Bootloader leest /boot/firmware/config.txt
     ↓
```

### 2. Kernel Initialization (Tweede Fase)
```
[2s] Linux kernel start
     ↓
[3s] Kernel laadt device tree overlays uit config.txt:
     - dtparam=spi=on           → SPI interface activeren
     - dtoverlay=waveshare35a   → ILI9486 TFT driver laden
     - dtoverlay=ads7846        → XPT2046 touch driver laden
     ↓
[4s] Hardware drivers initialiseren:
     - SPI bus /dev/spidev0.0 beschikbaar
     - TFT framebuffer /dev/fb1 aangemaakt
     - Touchscreen /dev/input/eventX aangemaakt
     ↓
```

### 3. Systemd Services (Derde Fase)
```
[5s] Systemd start
     ↓
[6s] Basis services starten
     ↓
[7s] Netwerk services starten
     ↓
[8s] BirdNET-Pi services starten:
     - birdnet_analysis.service
     - tft_display.service  ← Dit toont vogels op het scherm
     ↓
```

## Wat Betekent Dit?

### Hardware Activatie (Gebeurt Al)

De **hardware** van je TFT scherm (ILI9486) wordt geactiveerd in **stap 2** door de kernel, lang voordat BirdNET-Pi start.

**Configuratie in `/boot/firmware/config.txt`:**
```bash
# SPI activeren (nodig voor TFT communicatie)
dtparam=spi=on

# TFT display driver laden
dtoverlay=waveshare35a,speed=16000000,rotate=90

# Touchscreen driver laden
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=1,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
```

Deze regels zorgen ervoor dat:
1. De kernel de juiste driver laadt
2. Het scherm geïnitialiseerd wordt
3. Een framebuffer `/dev/fb1` aangemaakt wordt
4. Het scherm klaar is om gebruikt te worden

### Software Activatie (BirdNET Display)

De `tft_display.service` is een **aparte laag** die:
- Draait **NA** de hardware initialisatie
- Verbindt met de database
- Haalt vogel detecties op
- Toont ze op het scherm

## Hoe Kun Je Controleren?

### 1. Controleer Hardware Initialisatie

Kijk of het TFT scherm herkend is door de kernel:

```bash
# Controleer of framebuffer bestaat
ls -la /dev/fb1

# Verwacht resultaat:
# crw-rw---- 1 root video 29, 1 Dec 31 12:34 /dev/fb1
```

```bash
# Controleer dmesg voor TFT initialisatie
dmesg | grep -i "fb1\|spi\|ili9486\|ads7846"

# Verwacht resultaat:
# [    3.456789] fbtft: module is from the staging directory
# [    3.567890] fb_ili9486: module is from the staging directory
# [    3.678901] graphics fb1: fb_ili9486 frame buffer device
# [    4.123456] input: ADS7846 Touchscreen as /devices/...
```

### 2. Controleer Config.txt

```bash
# Bekijk TFT configuratie
grep -E "spi=on|waveshare|ili9486|ads7846" /boot/firmware/config.txt

# Verwacht resultaat:
# dtparam=spi=on
# dtoverlay=waveshare35a,speed=16000000,rotate=90
# dtoverlay=ads7846,cs=1,penirq=25,...
```

### 3. Test Framebuffer Direct

Je kunt direct naar de framebuffer schrijven (zonder BirdNET-Pi):

```bash
# Maak scherm wit
sudo cat /dev/zero > /dev/fb1

# Of gebruik fbi om een afbeelding te tonen
sudo fbi -T 1 -d /dev/fb1 -noverbose -a jouw_afbeelding.png
```

Als dit werkt, dan is de hardware correct geïnitialiseerd door de kernel!

## Wat Als Het Scherm Niet Werkt?

### Scenario 1: Scherm Blijft Wit/Zwart Na Opstart

**Diagnose:**
```bash
# Check of framebuffer bestaat
ls /dev/fb1

# Check of driver geladen is
lsmod | grep -i "ili9486\|fbtft"

# Check kernel log
dmesg | grep -i "fb1\|ili"
```

**Mogelijke oorzaken:**
1. ❌ `dtoverlay` niet correct in config.txt
2. ❌ SPI niet ingeschakeld
3. ❌ Hardware verbinding probleem

**Oplossing:**
```bash
# Voer installatie opnieuw uit
cd ~/BirdNET-Pi
bash scripts/install_tft.sh

# Of configureer handmatig
sudo nano /boot/firmware/config.txt
# Voeg toe:
# dtparam=spi=on
# dtoverlay=waveshare35a,speed=16000000,rotate=90

# Reboot
sudo reboot
```

### Scenario 2: Hardware Werkt, Maar tft_display.service Niet

**Diagnose:**
```bash
# Check service status
sudo systemctl status tft_display.service

# Check logs
sudo journalctl -u tft_display.service -n 50 --no-pager
```

**Mogelijke oorzaken:**
1. ❌ Python bibliotheken ontbreken (zie `TFT_EXIT_CODE_1_FIX_NL.md`)
2. ❌ Database niet gevonden
3. ❌ TFT_ENABLED=0 in configuratie

**Oplossing:**
```bash
# Voer quick fix uit
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

## Console Op TFT Tonen (Optioneel)

Als je de **Linux console** op het TFT scherm wilt zien tijdens boot (in plaats van alleen vogels):

### Stap 1: Configureer Console

Bewerk `/boot/firmware/cmdline.txt`:
```bash
sudo nano /boot/firmware/cmdline.txt
```

Voeg toe aan het einde van de regel:
```
fbcon=map:10
```

Dit zegt aan de kernel om de console naar fb1 (het TFT scherm) te sturen.

### Stap 2: Reboot

```bash
sudo reboot
```

Nu zou je boot berichten moeten zien op het TFT scherm!

**Let op:** Dit kan conflicteren met `tft_display.service`. Kies een van beide:
- **Console op TFT**: Zie boot messages en terminal
- **BirdNET display op TFT**: Zie vogel detecties (standaard)

## Boot Splash Screen (Optioneel)

Je kunt ook een boot splash screen toevoegen die verschijnt voordat BirdNET-Pi start:

```bash
# Installeer plymouth
sudo apt-get install plymouth plymouth-themes

# Configureer om fb1 te gebruiken
sudo plymouth-set-default-theme -R spinner

# Bewerk grub/boot config om splash te activeren
```

Dit is echter complex en meestal niet nodig.

## Samenvatting

**Antwoord op je vraag:**

✅ **JA**, het TFT scherm wordt AL geactiveerd bij boot, voordat BirdNET-Pi start.

Dit gebeurt door:
1. **Bootloader** leest `/boot/firmware/config.txt`
2. **Kernel** laadt de device tree overlays (ILI9486 driver)
3. **Hardware** wordt geïnitialiseerd, framebuffer `/dev/fb1` gemaakt
4. **Daarna** start BirdNET-Pi en kan het scherm gebruiken

Er is **geen extra configuratie nodig** - het systeem is al correct ingesteld door `install_tft.sh`.

Als je scherm niet werkt:
- Het is **NIET** omdat de hardware niet geactiveerd wordt
- Het is waarschijnlijk:
  - Python bibliotheken ontbreken → Gebruik `quick_fix_tft.sh`
  - Hardware verbinding probleem → Check bedrading
  - Config.txt niet correct → Voer `install_tft.sh` opnieuw uit

## Gerelateerde Documentatie

- `TFT_EXIT_CODE_1_FIX_NL.md` - Exit code 1 problemen oplossen
- `TFT_SCREEN_SETUP.md` - Complete setup guide
- `TFT_TESTING_GUIDE.md` - Hardware testing procedures
- `TFT_ARCHITECTURE.md` - Technical architecture details

## Hulp Nodig?

Als je scherm nog steeds niet werkt, verzamel deze informatie:

```bash
# Hardware check
ls -la /dev/fb1
lsmod | grep fbtft

# Kernel log
dmesg | grep -i "fb1\|ili" > ~/tft_dmesg.txt

# Config check
grep -E "spi|overlay" /boot/firmware/config.txt > ~/tft_config.txt

# Service check
sudo systemctl status tft_display.service > ~/tft_service.txt
sudo journalctl -u tft_display.service -n 50 --no-pager > ~/tft_logs.txt
```

Deel deze bestanden voor verdere hulp.
