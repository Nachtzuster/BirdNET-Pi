# TFT Display Service Exit Code 2 - Samenvatting voor Gebruiker

## Vraag
U vroeg om te onderzoeken wat de volgende foutmelding betekent en of deze op fouten slaat:

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 18:44:12 CET; 1s ago
 Invocation: fa0ab4ca1ea14be5af0a25579d6a2d71
    Process: 33777 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=2)
   Main PID: 33777 (code=exited, status=2)
        CPU: 74ms
```

## Antwoord

**Ja, dit is een fout**. Exit code 2 betekent dat het TFT display script niet kan starten.

### Oorzaak

Wanneer u een `git pull` doet zonder de RPi 4B opnieuw op te starten, en vervolgens de TFT Display service inschakelt via de webinterface, gebruikt de service een **verouderde versie** van het script die nog in `/usr/local/bin/tft_display.py` staat. De nieuwe code staat wel in uw repository (`~/BirdNET-Pi/scripts/tft_display.py`), maar de service gebruikt de oude kopie.

### Oplossing Geïmplementeerd

Ik heb een **automatische update-mechanisme** toegevoegd dat ervoor zorgt dat het script altijd up-to-date is wanneer de service start:

1. **Wrapper script** (`tft_display_wrapper.sh`):
   - Controleert automatisch of de repository versie nieuwer is
   - Werkt het script bij indien nodig
   - Start vervolgens het TFT display script
   - Logt alle acties voor troubleshooting

2. **Service file aangepast**: De service gebruikt nu het wrapper script

3. **Installatie scripts aangepast**: Alle installatie- en update scripts installeren nu het wrapper script

### Wat Nu Te Doen?

#### Als u de TFT service al hebt geïnstalleerd en exit code 2 krijgt:

```bash
# 1. Haal de nieuwste code op (deze fix)
cd ~/BirdNET-Pi
git pull

# 2. Update de scripts (installeert het wrapper script)
sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh

# 3. Herlaad systemd
sudo systemctl daemon-reload

# 4. Herstart de service
sudo systemctl restart tft_display.service

# 5. Controleer de status - zou nu moeten werken
sudo systemctl status tft_display.service
```

#### Voor nieuwe installaties:

Alles werkt automatisch! Het wrapper script zorgt ervoor dat het TFT display script altijd up-to-date is.

### Voordelen

✅ **Geen handmatige stappen meer** na een git pull
✅ **Automatische update** wanneer de service start
✅ **Duidelijke logs** voor troubleshooting
✅ **Backwards compatible** met bestaande installaties

### Documentatie

Voor meer details, zie:
- **Nederlands**: `docs/TFT_EXIT_CODE_2_FIX_NL.md`
- **English**: `docs/TFT_EXIT_CODE_2_FIX.md`

### Technische Details

De fout trad op omdat:
1. Python exit code 2 betekent meestal dat een script niet kan worden gevonden of uitgevoerd
2. De service probeerde een verouderde versie van het script te starten
3. Deze oude versie was niet compatibel met de nieuwe code

Het wrapper script lost dit op door bij elke service start te controleren of het script up-to-date is en het zo nodig automatisch bij te werken.

## Samenvatting

**Dit is een echte fout geweest** die optrad na een git pull zonder heropstart. De fix die ik heb geïmplementeerd zorgt ervoor dat dit probleem niet meer voorkomt door het script automatisch bij te werken wanneer de service start. U hoeft alleen de bovenstaande stappen te volgen om de fix toe te passen.
