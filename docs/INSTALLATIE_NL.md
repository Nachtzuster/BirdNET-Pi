# BirdNET-Pi Installatie vanaf YvedD Repository

## Nieuwe Installatie (Schone Raspberry Pi)

### Stap 1: Raspberry Pi Voorbereiden

1. Download **Raspberry Pi OS (64-bit) Lite** (Bookworm of Trixie) via [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash het OS naar een SD-kaart
3. Start de Raspberry Pi op
4. Log in met de standaard gebruikersnaam (de gebruikersnaam die u tijdens setup heeft aangemaakt)

### Stap 2: Passwordless Sudo Configureren

```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/010_$USER-nopasswd
sudo chmod 0440 /etc/sudoers.d/010_$USER-nopasswd
```

### Stap 3: BirdNET-Pi Installeren

```bash
curl -s https://raw.githubusercontent.com/YvedD/BirdNET-Pi-MigCount/main/newinstaller.sh | bash
```

### Stap 4: WiFi Configuratie (Indien geen netwerk)

Als u geen internetverbinding heeft tijdens de installatie:

1. De installer start automatisch een WiFi setup webpagina
2. **Open uw browser** op een ander apparaat (telefoon, laptop, etc.)
3. Ga naar: **http://birdnetpi.local:8080** of gebruik het IP-adres van de Pi
4. Selecteer uw WiFi netwerk uit de lijst
5. Voer het wachtwoord in
6. Klik op "Verbinden"
7. De installatie gaat automatisch verder

### Stap 5: Na Installatie

Na de installatie herstart de Raspberry Pi automatisch. Daarna kunt u toegang krijgen tot BirdNET-Pi via:

- **http://birdnetpi.local** (aanbevolen)
- Of via het IP-adres van uw Raspberry Pi

**Standaard inloggegevens:**
- Gebruikersnaam: `birdnet`
- Wachtwoord: (leeg - stel dit in via Tools > Settings > Advanced Settings)

---

## Update van Bestaande Installatie (Nachtzuster → YvedD)

Als u al BirdNET-Pi heeft geïnstalleerd vanaf de Nachtzuster repository:

### **GEEN Uninstall Nodig!**

U kunt direct updaten zonder eerst te verwijderen:

```bash
cd ~/BirdNET-Pi

# Verwijder oude remote
git remote remove origin

# Voeg nieuwe remote toe
git remote add origin https://github.com/YvedD/BirdNET-Pi-MigCount.git

# Haal laatste versie op
git fetch origin

# Update naar nieuwe versie
git reset --hard origin/main

# Voer update script uit
./scripts/update_birdnet.sh
```

**Na de update:**
- De Raspberry Pi herstart automatisch
- WiFi roaming wordt automatisch geconfigureerd (indien WiFi in gebruik)
- Al uw data en instellingen blijven behouden

---

## WiFi Roaming

Na installatie of update is WiFi roaming automatisch geconfigureerd. Dit betekent:

- ✅ Raspberry Pi verbindt automatisch met het sterkste WiFi signaal
- ✅ Schakelt automatisch over tussen access points met dezelfde SSID
- ✅ Ideaal voor grote gebouwen met meerdere WiFi access points
- ✅ Stabiele SSH verbinding
- ✅ Betrouwbare web interface toegang

### WiFi Roaming Beheren

U kunt WiFi roaming beheren via:

**Web Interface:**
- Ga naar: http://birdnetpi.local/scripts/wifi_roaming.php

**Command Line:**
```bash
# Status controleren
sudo /usr/local/bin/configure_wifi_roaming.sh status

# Opnieuw configureren
sudo /usr/local/bin/configure_wifi_roaming.sh configure

# Backup herstellen
sudo /usr/local/bin/configure_wifi_roaming.sh restore /path/to/backup
```

---

## Vereisten

### Hardware
- Raspberry Pi 5, 4B, 400, 3B+, of 0W2
- SD-kaart (minimaal 16GB aanbevolen)
- USB microfoon of geluidskaart
- Internetverbinding (WiFi of Ethernet)

### Software
- Raspberry Pi OS (64-bit) - Bookworm of Trixie
- Passwordless sudo moet ingeschakeld zijn

---

## WiFi Setup Details

### Web Interface Functionaliteit

De WiFi configuratie interface biedt:

1. **Automatische Netwerk Scan**
   - Toont alle beschikbare WiFi netwerken
   - Signaalsterkte indicator (5 balken)
   - Gesorteerd op signaalsterkte (sterkste eerst)

2. **Visuele Interface**
   - Moderne, gebruiksvriendelijke interface
   - Responsive design (werkt op telefoon, tablet, desktop)
   - Nederlandse taal
   - Real-time feedback

3. **Veilige Configuratie**
   - Automatische backup van bestaande configuratie
   - Ondersteunt WPA/WPA2 en open netwerken
   - Wachtwoord wordt niet getoond tijdens invoer

4. **Directe Feedback**
   - Verbindingsstatus in real-time
   - Duidelijke foutmeldingen
   - Automatisch doorgang naar installatie na verbinding

### Toegang tot WiFi Setup

De WiFi setup interface is toegankelijk via:

- **http://birdnetpi.local:8080** (via mDNS/Bonjour)
- **http://[IP-ADRES]:8080** (via IP-adres van de Pi)

**Tip:** Als u het IP-adres niet weet, sluit dan een monitor aan op de Raspberry Pi. Het IP-adres wordt getoond tijdens de boot.

---

## Troubleshooting

### WiFi Setup Interface Niet Bereikbaar

1. **Controleer of de Pi is opgestart**
   - Groene LED moet knipperen (SD-kaart activiteit)
   - Wacht minimaal 1-2 minuten na opstarten

2. **Probeer het IP-adres**
   - Sluit een monitor aan of check uw router
   - Gebruik http://[IP-ADRES]:8080

3. **Controleer netwerk**
   - Zorg dat uw apparaat op hetzelfde netwerk is
   - WiFi setup draait op poortnummer 8080

### Installatie Faalt

1. **Check internetverbinding**
   ```bash
   ping -c 4 google.com
   ```

2. **Controleer disk ruimte**
   ```bash
   df -h
   ```

3. **Bekijk installatie log**
   ```bash
   cat ~/installation-$(date +%F).txt
   ```

### WiFi Verbinding Mislukt

1. **Controleer wachtwoord**
   - Let op hoofd/kleine letters
   - Speciale karakters correct ingevoerd

2. **Signaalsterkte**
   - Zorg voor voldoende signaalsterkte
   - Plaats Pi dichterbij access point

3. **Handmatige configuratie**
   ```bash
   sudo raspi-config
   # System Options → Wireless LAN
   ```

---

## Support & Documentatie

### Documentatie
- **WiFi Roaming (EN):** `docs/wifi_roaming.md`
- **WiFi Roaming (NL):** `docs/wifi_roaming_nl.md`
- **Implementation Summary:** `docs/WIFI_ROAMING_SUMMARY.md`

### GitHub Repository
- **Issues:** https://github.com/YvedD/BirdNET-Pi-MigCount/issues
- **Discussions:** https://github.com/YvedD/BirdNET-Pi-MigCount/discussions

### Originele BirdNET-Pi
- **Wiki:** https://github.com/mcguirepr89/BirdNET-Pi/wiki
- **Discussions:** https://github.com/mcguirepr89/BirdNET-Pi/discussions

---

## Kenmerken van Deze Fork

Deze fork (YvedD/BirdNET-Pi-MigCount) bevat:

✅ **Web-gebaseerde WiFi Setup**
- Grafische interface voor WiFi configuratie
- Toegankelijk via browser (birdnetpi.local:8080)
- Automatische netwerk scanning
- Nederlandse interface

✅ **Automatische WiFi Roaming**
- Schakelt automatisch over naar sterkste signaal
- Geïntegreerd in installatie
- Web interface voor beheer
- Complete documentatie

✅ **Verbeterde Installatie**
- Automatische WiFi detectie
- Geen handmatige configuratie vereist
- Update zonder uninstall
- Behoud van data bij update

---

## Licentie

BirdNET-Pi is gelicenseerd onder Creative Commons BY-NC-SA 4.0. Dit betekent:

- ✅ Persoonlijk gebruik toegestaan
- ✅ Delen met bronvermelding toegestaan
- ❌ **Commercieel gebruik NIET toegestaan**
- ❌ Mag niet gebruikt worden voor commerciële producten

Zie [LICENSE](../LICENSE) voor volledige details.

---

**Veel succes met BirdNET-Pi!** 🐦
