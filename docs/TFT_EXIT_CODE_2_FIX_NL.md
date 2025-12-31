# TFT Display Service Exit Code 2 - Oplossing

## Probleembeschrijving

Na het uitvoeren van een `git pull` zonder het systeem opnieuw op te starten, en vervolgens het inschakelen van de TFT display service via "Tools → Services → TFT Display - Enable" in de webinterface, faalt de service met exit code 2:

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 18:44:12 CET; 1s ago
 Invocation: fa0ab4ca1ea14be5af0a25579d6a2d71
    Process: 33777 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=2)
   Main PID: 33777 (code=exited, status=2)
        CPU: 74ms
```

## Wat betekent Exit Code 2?

Exit code 2 van Python betekent gewoonlijk:
- **Bestandsfout**: Het Python-script bestaat niet of is niet leesbaar
- **Verouderd script**: Het script in `/usr/local/bin/tft_display.py` is een oude versie die niet compatibel is
- **Import error**: Een kritieke module kan niet worden geïmporteerd (zeer zeldzaam)

## Oorzaak van het Probleem

Wanneer je een `git pull` doet, wordt de code in de repository `~/BirdNET-Pi/scripts/tft_display.py` bijgewerkt. Echter, de TFT service gebruikt een kopie van dit script die is geïnstalleerd in `/usr/local/bin/tft_display.py`. Deze kopie wordt **niet automatisch bijgewerkt** wanneer je alleen "Enable" klikt in de webinterface.

Het proces is als volgt:
1. ✅ `git pull` bijwerkt `~/BirdNET-Pi/scripts/tft_display.py`
2. ❌ `/usr/local/bin/tft_display.py` blijft de oude versie
3. ❌ Service probeert de oude versie te starten → exit code 2

## Oplossing

Deze fix voegt een **wrapper script** toe dat automatisch controleert of het TFT display script up-to-date is voordat de service start. Dit betekent dat na een `git pull` en het inschakelen van de service via de webinterface, het script automatisch wordt bijgewerkt.

### Wat is er veranderd?

1. **Nieuw wrapper script**: `tft_display_wrapper.sh`
   - Controleert of `/usr/local/bin/tft_display.py` up-to-date is
   - Werkt het script automatisch bij indien nodig
   - Start vervolgens het TFT display script

2. **Service file aangepast**: De service gebruikt nu het wrapper script:
   ```
   ExecStart=/usr/local/bin/tft_display_wrapper.sh
   ```
   
3. **Update scripts aangepast**: 
   - `install_services.sh`
   - `install_tft_service.sh`
   - `update_birdnet_snippets.sh`
   
   Alle scripts installeren nu zowel het Python script als het wrapper script.

### Hoe de Fix Te Gebruiken

#### Voor Bestaande Installaties

Als je de TFT service al hebt geïnstalleerd en exit code 2 krijgt:

```bash
# 1. Haal de laatste code op
cd ~/BirdNET-Pi
git pull

# 2. Update de scripts (dit installeert de nieuwe wrapper)
sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh

# 3. Herlaad systemd om de nieuwe service configuratie te laden
sudo systemctl daemon-reload

# 4. Herstart de service
sudo systemctl restart tft_display.service

# 5. Controleer de status
sudo systemctl status tft_display.service
```

#### Voor Nieuwe Installaties

Voor nieuwe installaties werkt alles automatisch:
1. Installeer via de webinterface: "Tools → Services → TFT Display → Install TFT Support"
2. Enable de service via "Enable" knop
3. Het wrapper script zorgt ervoor dat alles up-to-date is

### Wat Doet Het Wrapper Script?

Het wrapper script (`tft_display_wrapper.sh`) voert de volgende controles uit:

1. **Controleert of repository script bestaat**
   ```bash
   if [ ! -f "$REPO_SCRIPT" ]; then
       echo "ERROR: Repository script not found"
       exit 1
   fi
   ```

2. **Vergelijkt timestamps**
   ```bash
   if [ "$REPO_SCRIPT" -nt "$TARGET_SCRIPT" ]; then
       echo "Repository script is newer, will update"
       # Update script...
   fi
   ```

3. **Update script indien nodig**
   - Kopieert nieuwe versie via een tijdelijk bestand
   - Verplaatst naar `/usr/local/bin/tft_display.py`
   - Stelt execute permissies in

4. **Start het Python script**
   ```bash
   exec "$PYTHON" "$TARGET_SCRIPT"
   ```

### Voordelen van Deze Oplossing

✅ **Automatisch**: Geen handmatige stappen nodig na git pull
✅ **Veilig**: Gebruikt tijdelijke bestanden om conflicten te voorkomen
✅ **Duidelijk**: Logs tonen wanneer een update plaatsvindt
✅ **Backwards compatible**: Werkt met bestaande installaties
✅ **Betrouwbaar**: Controleert alle voorwaarden voordat start

### Logs Controleren

Om te zien wat het wrapper script doet:

```bash
sudo journalctl -u tft_display.service -n 100 --no-pager
```

Je zou moeten zien:
```
[2025-12-31 18:44:12] Updating TFT display script from repository...
[2025-12-31 18:44:12] TFT display script updated successfully
[2025-12-31 18:44:12] Using Python from virtual environment: /home/yves/BirdNET-Pi/birdnet/bin/python3
[2025-12-31 18:44:12] Starting TFT display service...
[2025-12-31 18:44:12] [tft_display] [INFO] BirdNET-Pi TFT Display starting...
```

## Alternatieve Oplossing (Handmatig)

Als je om een of andere reden niet het wrapper script wilt gebruiken, kun je altijd handmatig het script bijwerken:

```bash
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
sudo systemctl restart tft_display.service
```

## Veelgestelde Vragen

**Q: Moet ik dit na elke git pull doen?**
A: Nee! Met het nieuwe wrapper script wordt het script automatisch bijgewerkt wanneer de service start.

**Q: Wat als ik nog steeds exit code 2 krijg?**
A: Controleer de logs met `sudo journalctl -u tft_display.service -n 100`. Als het wrapper script niet is geïnstalleerd, voer dan `sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh` uit.

**Q: Heeft dit invloed op de performance?**
A: Nee, de controle is zeer snel (timestamp vergelijking) en vindt alleen plaats bij service start, niet tijdens het draaien.

**Q: Wat als het Python virtual environment niet bestaat?**
A: Het wrapper script gebruikt automatisch system Python (`/usr/bin/python3`) als fallback.

## Samenvatting

Exit code 2 betekende dat het script niet kon starten, meestal omdat `/usr/local/bin/tft_display.py` verouderd was na een git pull. Het nieuwe wrapper script lost dit op door automatisch te controleren en bij te werken wanneer nodig, waardoor je niet meer handmatig hoeft in te grijpen na een code update.
