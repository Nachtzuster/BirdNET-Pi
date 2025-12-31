# BELANGRIJK: Update Instructies na Git Pull

## Probleem

Na een `git pull` werkt de TFT display service nog steeds niet omdat:
1. Het bijgewerkte script moet gekopieerd worden naar `/usr/local/bin/`
2. Python packages moeten geïnstalleerd zijn in de virtual environment

## Snelle Oplossing (AANBEVOLEN)

Voer dit script uit dat alles automatisch doet:

```bash
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

Dit script doet automatisch:
- ✓ Kopieert het bijgewerkte script naar `/usr/local/bin/`
- ✓ Installeert/update Python packages (luma.lcd, luma.core, Pillow)
- ✓ Herstart de service
- ✓ Controleert of alles werkt

## Handmatige Stappen

Als je het stap voor stap wilt doen:

### Stap 1: Kopieer het bijgewerkte script

```bash
cd ~/BirdNET-Pi
sudo cp scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
```

### Stap 2: Installeer Python packages in virtual environment

```bash
cd ~/BirdNET-Pi
source birdnet/bin/activate
pip install --upgrade luma.lcd luma.core Pillow
deactivate
```

### Stap 3: Herstart de service

```bash
sudo systemctl restart tft_display.service
```

### Stap 4: Controleer de status

```bash
sudo systemctl status tft_display.service
```

## Controleer of het werkt

### Bekijk de logs

```bash
sudo journalctl -u tft_display.service -f
```

Je zou moeten zien:
- `[INFO] BirdNET-Pi TFT Display starting...`
- `[INFO] Display initialized: 320x480` (of je scherm resolutie)
- `[INFO] Entering main display loop`
- `[INFO] Updated display with X detections`

### Veelvoorkomende Fouten

#### Fout 1: "Required libraries not available"

**Probleem**: Python packages niet geïnstalleerd in virtual environment

**Oplossing**:
```bash
cd ~/BirdNET-Pi
source birdnet/bin/activate
pip install luma.lcd luma.core Pillow
deactivate
sudo systemctl restart tft_display.service
```

#### Fout 2: Service blijft restarting

**Probleem**: Oud script draait nog steeds

**Oplossing**:
```bash
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
sudo systemctl restart tft_display.service
```

#### Fout 3: Wit scherm blijft bestaan

**Probleem**: De oude versie van het script draait nog

**Oplossing**:
1. Controleer welke versie draait:
```bash
head -20 /usr/local/bin/tft_display.py
```

2. Als het niet de nieuwste is, kopieer opnieuw:
```bash
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo systemctl restart tft_display.service
```

## Waarom is dit nodig?

De service draait `/usr/local/bin/tft_display.py`, niet het bestand in de git repository.

Wanneer je `git pull` doet:
- ✓ `~/BirdNET-Pi/scripts/tft_display.py` wordt bijgewerkt (in repository)
- ✗ `/usr/local/bin/tft_display.py` wordt NIET automatisch bijgewerkt

Je moet het script handmatig kopiëren na elke git pull!

## Test Tools

Na de update, test of alles werkt:

```bash
# Hardware test
bash ~/BirdNET-Pi/scripts/test_tft_hardware.sh

# Python packages test
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py
```

## Verwacht Resultaat

Na de update zou je scherm moeten tonen:
- Zwarte achtergrond (niet wit!)
- Witte tekst voor vogelnamen
- Felgroene confidence scores voor detecties >75%
- Donkergroene confidence scores voor detecties ≤75%
- Scrollende detectie lijst

## Hulp Nodig?

Als het nog steeds niet werkt:

1. Controleer de logs:
```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

2. Test Python packages:
```bash
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; import PIL; print('OK')"
```

3. Controleer script versie:
```bash
grep "confidence > 75" /usr/local/bin/tft_display.py
```
Als dit geen output geeft, is het script niet bijgewerkt!
