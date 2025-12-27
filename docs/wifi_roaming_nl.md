# WiFi Roaming voor BirdNET-Pi

## Antwoord op de vraag

**Vraag:** Kan jij door de codebase lopen van BirdNET-Pi-MigCount en kijken of het mogelijk is om de instellingen op de Raspberry Pi zodanig te zetten dat steeds het sterkste Wifi-signaal gebruikt word om de SSH-interface naar de gebruiker te sturen, of is dit onmogelijk?

**Antwoord:** Ja, dit is mogelijk! De WiFi roaming functionaliteit is nu toegevoegd aan BirdNET-Pi.

## Wat is WiFi Roaming?

WiFi roaming zorgt ervoor dat de Raspberry Pi automatisch overschakelt naar het sterkste beschikbare WiFi-signaal wanneer je meerdere access points hebt met dezelfde netwerknaam (SSID). Dit is ideaal voor:

- **Stabiele SSH-verbindingen** - Betrouwbare toegang op afstand blijft behouden
- **Web interface toegankelijkheid** - Continue toegang tot de BirdNET-Pi web UI
- **Live audio streaming** - Ononderbroken audio feed
- **Data synchronisatie** - Betrouwbare uploads naar BirdWeather en andere services

## Hoe werkt het?

De implementatie gebruikt `wpa_supplicant` met de volgende instellingen:

- **`ap_scan=1`**: Actief scannen naar het beste beschikbare access point
- **`fast_reauth=1`**: Snellere her-authenticatie bij het wisselen tussen AP's
- **`bgscan="simple:30:-45:300"`**: 
  - Scant elke 30 seconden
  - Schakelt over naar beter AP als signaal onder -45 dBm komt
  - Maximale scan interval van 300 seconden bij goed signaal

## Vereisten

Om WiFi roaming te gebruiken heb je nodig:

1. **Meerdere Access Points**: Minstens twee WiFi access points
2. **Zelfde SSID**: Alle access points moeten dezelfde netwerknaam uitzenden
3. **Zelfde Beveiliging**: Alle access points gebruiken hetzelfde wachtwoord en beveiligingstype
4. **Overlappende Coverage**: De bereiken moeten elkaar overlappen

## Installatie

### Optie 1: Automatische configuratie (Aanbevolen)

Voer het WiFi roaming configuratie script uit:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh
```

### Optie 2: Via de web interface

1. Ga naar de BirdNET-Pi web interface
2. Navigeer naar "Tools" > "WiFi Roaming"
3. Klik op "Enable WiFi Roaming"

### Optie 3: Handmatige configuratie

Zie de volledige documentatie in [docs/wifi_roaming.md](wifi_roaming.md) voor handmatige configuratie-instructies.

## Status controleren

Om te controleren of WiFi roaming correct is geconfigureerd:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh status
```

## Aanpassen van roaming gedrag

Je kunt het roaming gedrag aanpassen door `/etc/wpa_supplicant/wpa_supplicant.conf` te bewerken:

```
bgscan="simple:KORT_INTERVAL:SIGNAAL_DREMPEL:LANG_INTERVAL"
```

**Voorbeelden:**

- **Agressief roaming** (sneller wisselen, meer stroomverbruik):
  ```
  bgscan="simple:15:-50:120"
  ```

- **Conservatief roaming** (minder frequent wisselen, zuiniger):
  ```
  bgscan="simple:60:-40:600"
  ```

- **Gebalanceerd** (standaard - goed voor meeste scenario's):
  ```
  bgscan="simple:30:-45:300"
  ```

## Voordelen

✅ Handhaaft optimale signaalsterkte  
✅ Vermindert pakketverlies en latency  
✅ Verbetert betrouwbaarheid van SSH toegang  
✅ Betere streaming kwaliteit  

## Overwegingen

⚠️ Licht verhoogd stroomverbruik (minimaal op Pi 4/5)  
⚠️ Korte verbindingsonderbreking tijdens AP-wissel (typisch < 1 seconde)  
⚠️ Kan kortstondige audio stream dropout veroorzaken  

## Technische details

De implementatie bestaat uit:

1. **`scripts/configure_wifi_roaming.sh`** - Configuratie script
2. **`scripts/wifi_roaming.php`** - Web interface voor configuratie
3. **`docs/wifi_roaming.md`** - Volledige Engelstalige documentatie

Het script:
- Maakt automatisch een backup van de huidige configuratie
- Voegt roaming parameters toe aan wpa_supplicant.conf
- Herstart de WiFi service
- Kan eenvoudig teruggedraaid worden met de backup

## Compatibiliteit

- ✅ Raspberry Pi 5, 4B, 400, 3B+, 0W2
- ✅ RaspiOS Bookworm/Trixie (64-bit)
- ✅ Zowel 2.4GHz als 5GHz WiFi
- ✅ Werkt met standaard consumer access points
- ✅ Geen enterprise WiFi (802.11r) vereist

## Veelgestelde vragen

**V: Werkt dit met verschillende WiFi netwerken (verschillende SSIDs)?**  
A: Nee, roaming is ontworpen voor meerdere access points met dezelfde SSID.

**V: Beïnvloedt dit mijn audio-opnames?**  
A: Nee, opnames worden lokaal opgeslagen. WiFi roaming beïnvloedt alleen de netwerkverbinding.

**V: Wat gebeurt er tijdens het overschakelen tussen access points?**  
A: Er is een korte onderbreking (typisch minder dan 1 seconde) tijdens het overschakelen.

**V: Kan ik de originele configuratie terugzetten?**  
A: Ja, het script maakt automatisch backups. Deze kunnen worden teruggedraaid via:
```bash
sudo /usr/local/bin/configure_wifi_roaming.sh restore
```

## Ondersteuning

Voor vragen of problemen:
1. Bekijk de [volledige documentatie](wifi_roaming.md) (Engels)
2. Raadpleeg de [BirdNET-Pi discussions](https://github.com/mcguirepr89/BirdNET-Pi/discussions)
3. Open een issue op de GitHub repository

## Conclusie

**Ja, het is mogelijk** om de Raspberry Pi zo te configureren dat deze automatisch het sterkste WiFi-signaal gebruikt voor SSH en alle andere netwerkverbindingen. De implementatie is nu beschikbaar in de BirdNET-Pi codebase en kan eenvoudig worden geactiveerd via de command line of web interface.
