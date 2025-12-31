# TFT Display Service Exit Code 1 - Probleemoplossing

## Probleembeschrijving

Bij het inschakelen van de TFT display service met `sudo systemctl enable --now tft_display.service` faalt de service met exit code 1:

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 16:44:13 CET; 990ms ago
 Invocation: a305a0e5bd4c46a28fcaae273382291e
    Process: 24012 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=1/FAILURE)
   Main PID: 24012 (code=exited, status=1/FAILURE)
```

## Snelle Diagnose

**EERSTE STAP**: Bekijk de foutmelding in de logs:

```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

Zoek naar specifieke foutmeldingen. De meest voorkomende oorzaken zijn:

### Oorzaak 1: Ontbrekende Python Bibliotheken (Meest Voorkomend)

**Foutmelding in logs:**
```
[ERROR] Required libraries not available
[ERROR] Install with: pip install Pillow luma.lcd
```

**Oplossing:**
```bash
# Navigeer naar BirdNET-Pi directory
cd ~/BirdNET-Pi

# Activeer virtual environment
source birdnet/bin/activate

# Installeer vereiste packages
pip install Pillow luma.lcd luma.core

# Deactiveer virtual environment
deactivate

# Herstart de service
sudo systemctl restart tft_display.service

# Controleer status
sudo systemctl status tft_display.service
```

### Oorzaak 2: Database Niet Gevonden

**Foutmelding in logs:**
```
[ERROR] Database not found
```

**Oplossing:**
```bash
# Controleer of database bestaat
ls -la ~/BirdNET-Pi/scripts/birds.db

# Als deze niet bestaat, maak hem aan
cd ~/BirdNET-Pi
bash scripts/createdb.sh

# Herstart de service
sudo systemctl restart tft_display.service
```

### Oorzaak 3: Configuratiebestand Ontbreekt of TFT Niet Ingeschakeld

**Foutmelding in logs:**
```
[WARNING] Configuration file not found: /etc/birdnet/birdnet.conf
```
of
```
[INFO] TFT display is disabled in configuration
```

**Oplossing:**
```bash
# Controleer of config bestaat
ls -la /etc/birdnet/birdnet.conf

# Schakel TFT in configuratie in
# Bewerk het bestand en voeg deze regel toe/wijzig:
sudo nano /etc/birdnet/birdnet.conf

# Voeg toe of wijzig:
TFT_ENABLED=1
TFT_TYPE=ili9486

# Opslaan en afsluiten (Ctrl+O, Enter, Ctrl+X)

# Herstart de service
sudo systemctl restart tft_display.service
```

## Geautomatiseerd Fix Script

Gebruik het quick fix script dat alle veelvoorkomende problemen oplost:

```bash
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

Dit script zal:
- ✓ Het tft_display.py script bijwerken
- ✓ Vereiste Python packages installeren/bijwerken
- ✓ De service herstarten
- ✓ De status tonen

## Python Omgeving Testen

Test voordat je de service inschakelt of alle vereiste packages zijn geïnstalleerd:

```bash
# Test met het speciale test script
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py
```

Dit toont je precies welke packages ontbreken (indien van toepassing).

## Handmatige Stap-voor-Stap Probleemoplossing

### Stap 1: Bekijk Recente Logs

```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

### Stap 2: Controleer of Python het Script Kan Vinden

```bash
ls -la /usr/local/bin/tft_display.py
```

Verwachte output:
```
-rwxr-xr-x 1 root root 24xxx Dec 31 16:44 /usr/local/bin/tft_display.py
```

Als het bestand niet bestaat of een symlink is:
```bash
sudo rm -f /usr/local/bin/tft_display.py
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
```

### Stap 3: Test Python Script Direct

```bash
# Dit toont je de exacte foutmelding
~/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py
```

Druk Ctrl+C om te stoppen nadat je de foutmelding hebt gezien.

### Stap 4: Verifieer Virtual Environment Heeft Vereiste Packages

```bash
# Controleer of Pillow is geïnstalleerd
~/BirdNET-Pi/birdnet/bin/python3 -c "import PIL; print('PIL:', PIL.__version__)"

# Controleer of luma.lcd is geïnstalleerd
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; print('luma.lcd:', luma.lcd.__version__)"

# Controleer of luma.core is geïnstalleerd
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.core; print('luma.core:', luma.core.__version__)"
```

Als één van deze faalt met "ModuleNotFoundError", installeer de ontbrekende packages:
```bash
cd ~/BirdNET-Pi
source birdnet/bin/activate
pip install Pillow luma.lcd luma.core
deactivate
```

### Stap 5: Controleer Configuratie

```bash
# Bekijk TFT-gerelateerde configuratie
grep "TFT_" /etc/birdnet/birdnet.conf
```

Je zou minstens moeten zien:
```
TFT_ENABLED=1
TFT_TYPE=ili9486
```

Zo niet, voeg ze toe:
```bash
echo "TFT_ENABLED=1" | sudo tee -a /etc/birdnet/birdnet.conf
echo "TFT_TYPE=ili9486" | sudo tee -a /etc/birdnet/birdnet.conf
```

### Stap 6: Controleer of Database Bestaat

```bash
ls -la ~/BirdNET-Pi/scripts/birds.db
```

Als deze niet bestaat, maak hem aan:
```bash
cd ~/BirdNET-Pi
bash scripts/createdb.sh
```

## Verwachte Succesvolle Opstart

Als de service succesvol start, zou je deze logs moeten zien:

```bash
sudo journalctl -u tft_display.service -f
```

Verwachte output:
```
[INFO] BirdNET-Pi TFT Display starting...
[INFO] Configuration loaded successfully
[INFO] TFT Enabled: True
[INFO] Display Type: ili9486
[INFO] Rotation: 90°
[INFO] Found database at: /home/yves/BirdNET-Pi/scripts/birds.db
[INFO] Initializing display...
[INFO] Display initialized: 320x480 (ili9486)
[INFO] Font loaded: DejaVuSans.ttf (12pt)
[INFO] Entering main display loop
[INFO] Initial update: X detections loaded
```

## Debian Trixie Specifieke Opmerkingen

De gebruiker vroeg of er iets in Debian Trixie zelf geïnstalleerd moet worden. Het antwoord is **NEE** - de fout is niet gerelateerd aan ontbrekende Debian packages.

De TFT display service gebruikt:
- **Python packages** (geïnstalleerd in virtual environment): `Pillow`, `luma.lcd`, `luma.core`
- **Systeem packages** (al geïnstalleerd door install_tft.sh): `python3-dev`, `libfreetype-dev`, etc.
- **Kernel drivers**: Automatisch geladen wanneer dtoverlay geconfigureerd is in `/boot/firmware/config.txt`

De exit code 1 is bijna altijd te wijten aan ontbrekende Python packages in de virtual environment, niet aan ontbrekende Debian systeem packages.

## Werkt het Nog Steeds Niet?

Als je alles hierboven hebt geprobeerd en de service nog steeds faalt:

1. **Verzamel diagnostische informatie:**
   ```bash
   # Bewaar logs in een bestand
   sudo journalctl -u tft_display.service -n 100 --no-pager > ~/tft_logs.txt
   
   # Test hardware
   bash ~/BirdNET-Pi/scripts/test_tft_hardware.sh > ~/tft_hardware.txt 2>&1
   
   # Test Python omgeving
   ~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py > ~/tft_python.txt 2>&1
   
   # Controleer configuratie
   grep "TFT_" /etc/birdnet/birdnet.conf > ~/tft_config.txt
   ```

2. **Bekijk de verzamelde bestanden:**
   - `~/tft_logs.txt` - Service logs
   - `~/tft_hardware.txt` - Hardware detectie resultaten
   - `~/tft_python.txt` - Python package test resultaten
   - `~/tft_config.txt` - TFT configuratie

3. **Deel de diagnostische informatie** bij het vragen om hulp, samen met:
   - Raspberry Pi model
   - Debian versie: `cat /etc/os-release | grep VERSION`
   - TFT display model (bijv. ILI9486)

## Belangrijkste Commandos

```bash
# Bekijk service status
sudo systemctl status tft_display.service

# Bekijk recente logs
sudo journalctl -u tft_display.service -n 50 --no-pager

# Bekijk live logs (Ctrl+C om af te sluiten)
sudo journalctl -u tft_display.service -f

# Herstart service
sudo systemctl restart tft_display.service

# Test Python omgeving
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py

# Voer quick fix script uit
cd ~/BirdNET-Pi && bash scripts/quick_fix_tft.sh
```

## Antwoord op Jouw Vraag

> "Het lijkt erop dat er ergens een bestand in de kernel van de Trixie Distributie niet gevonden kan worden? Of begrijp ik dat verkeerd?"

**Antwoord:** Je begrijpt dat verkeerd. De fout heeft **NIETS** te maken met de Debian Trixie kernel of ontbrekende systeem bestanden.

De exit code 1 komt vrijwel zeker door:
1. **Ontbrekende Python libraries** in de virtual environment (Pillow, luma.lcd, luma.core)
2. **Ontbrekende database** (birds.db)
3. **TFT niet ingeschakeld** in configuratie (TFT_ENABLED=1)

De kernel drivers voor het TFT scherm (SPI) zijn al geladen als je de juiste dtoverlay hebt in `/boot/firmware/config.txt`.

**Om dit op te lossen:**
```bash
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

Dit lost automatisch de meeste problemen op!
