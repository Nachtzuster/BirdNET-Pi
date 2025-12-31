# Audit: Mogelijkheid om Soorten te Filteren uit het BirdNET Model

**Datum**: 18 december 2025  
**Model**: BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite  
**Audit Type**: Technische haalbaarheidsanalyse voor soorten filtering

## Samenvatting

**Ja, het is mogelijk om bepaalde soorten uit het BirdNET model te filteren.** Het systeem biedt momenteel drie verschillende filtermechanismen die na de model-inferentie werken. De filtering gebeurt niet in het .tflite model zelf, maar in de verwerkingslogica die de modeloutput verwerkt.

## Huidige Filtermechanismen

### 1. Include Species List (Inclusie Lijst)
**Bestand**: `~/BirdNET-Pi/include_species_list.txt`  
**Functie**: Witte lijst - Alleen soorten op deze lijst worden herkend  
**Gebruik**: Voor gebruikers die ALLEEN specifieke soorten willen detecteren  
**Waarschuwing**: Als deze lijst ENIGE soorten bevat, worden ALLE andere soorten uitgesloten

**Implementatie locatie**: 
- `scripts/utils/analysis.py`, regels 141, 166-167
- Web interface: `homepage/views.php`, regel 185

### 2. Exclude Species List (Exclusie Lijst)
**Bestand**: `~/BirdNET-Pi/exclude_species_list.txt`  
**Functie**: Zwarte lijst - Soorten op deze lijst worden NIET herkend  
**Gebruik**: Voor gebruikers die specifieke soorten willen uitsluiten  

**Implementatie locatie**:
- `scripts/utils/analysis.py`, regels 142, 168-169
- Web interface: `homepage/views.php`, regel 193

### 3. Whitelist Species List (Witte Lijst voor Drempelwaarde)
**Bestand**: `~/BirdNET-Pi/whitelist_species_list.txt`  
**Functie**: Overschrijft de Species Occurrence Frequency drempelwaarde  
**Gebruik**: Soorten worden gedetecteerd zelfs als ze onder de geografische voorkomingsdrempel vallen  
**Opmerking**: Niet de aanbevolen werkwijze - eerst Species Occurrence models v1 en v2.4 proberen

**Implementatie locatie**:
- `scripts/utils/analysis.py`, regels 143, 170-171
- Web interface: `homepage/views.php`, regel 201

## Technische Details

### Model Architectuur

Het BirdNET model bestaat uit meerdere componenten:

1. **Classificatie Model**: `BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite`
   - Primair model voor audio-classificatie
   - Genereert 6522 voorspellingen (één per soort)
   - Werkt onafhankelijk van filtering

2. **Meta Data Models**: 
   - `BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite` (versie 1)
   - `BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite` (versie 2)
   - Gebruikt voor geografische en temporele filtering
   - Gebaseerd op latitude, longitude en weeknummer

3. **Labels Bestand**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt`
   - Bevat 6522 soortnamen in wetenschappelijke notatie
   - Bijvoorbeeld: `Pica pica`, `Accipiter nisus`, etc.

### Verwerkingspipeline

```
Audio Input
    ↓
[BirdNET Model Inferentie] ← Geen filtering hier (6522 soorten)
    ↓
[Alle voorspellingen gesorteerd op confidence]
    ↓
[Top 10 per audio chunk behouden]
    ↓
[Privacy Filter] ← Verwijdert menselijke geluiden
    ↓
[Confidence Drempel Filter] ← Minimum betrouwbaarheidsscore
    ↓
[Include List Filter] ← Als lijst niet leeg: alleen deze soorten
    ↓
[Exclude List Filter] ← Verwijder deze soorten
    ↓
[Species Occurrence Filter] ← Geografische/temporele filtering
    ↓
[Whitelist Override] ← Toestaan ondanks lage occurrence
    ↓
Definitieve Detecties
```

### Code Implementatie

De filtering wordt uitgevoerd in `scripts/utils/analysis.py`, functie `run_analysis()`:

```python
# Laad de drie species lijsten
include_list = loadCustomSpeciesList("~/BirdNET-Pi/include_species_list.txt")
exclude_list = loadCustomSpeciesList("~/BirdNET-Pi/exclude_species_list.txt")
whitelist_list = loadCustomSpeciesList("~/BirdNET-Pi/whitelist_species_list.txt")

# Voor elke detectie met voldoende confidence:
if sci_name not in include_list and len(include_list) != 0:
    # Uitgesloten: niet in include lijst
elif sci_name in exclude_list and len(exclude_list) != 0:
    # Uitgesloten: in exclude lijst
elif sci_name not in predicted_species_list and sci_name not in whitelist_list:
    # Uitgesloten: onder geografische drempel
else:
    # Geaccepteerd
```

## Web Interface

De gebruiker kan soorten beheren via de web interface:

**Navigatie**: Tools → Settings → Species Lists
- **Included Species**: Manage include lijst
- **Excluded Species**: Manage exclude lijst  
- **Whitelisted Species**: Manage whitelist

**Features**:
- Zoekfunctionaliteit voor snelle toegang tot soorten
- Drag-and-drop interface voor toevoegen/verwijderen
- Real-time validatie

**Implementatie**: 
- `scripts/species_list.php` - UI rendering
- `homepage/views.php` - Server-side verwerking

## Beperkingen en Overwegingen

### 1. Het .tflite Model Zelf kan NIET worden Aangepast
- Het TensorFlow Lite model is een gecompileerd binair bestand
- Soorten kunnen niet permanent uit het model verwijderd worden
- Het model genereert altijd voorspellingen voor alle 6522 soorten
- Filtering gebeurt alleen post-inferentie in Python code

### 2. Performance Implicaties
- **Geen performance voordeel**: Het model draait altijd volledige inferentie
- **Filtering is snel**: String matching in Python is verwaarloosbaar
- **Memory gebruik**: Onveranderd - volledige model blijft in geheugen

### 3. Geografische Filtering (Meta Data Model)
- Gebruikt Species Occurrence Frequency drempelwaarde
- Gebaseerd op eBird data en voorkomingspatronen
- Kan worden geconfigureerd via `SF_THRESH` parameter
- Twee versies beschikbaar (v1 en v2.4) met verschillende algoritmes

### 4. Bestandsformaat
De species list bestanden gebruiken een specifiek formaat:
```
Genus_species
```
Bijvoorbeeld:
```
Pica_pica
Turdus_merula
Erithacus_rubecula
```

**Belangrijk**: Gebruik wetenschappelijke namen zoals in `labels.txt`

## Aanbevolen Werkwijze

### Voor Eenvoudige Filtering (< 50 soorten)
1. Gebruik de **Exclude List** om ongewenste soorten te blokkeren
2. Beheer via web interface (Tools → Settings → Excluded Species)
3. Soorten worden nog steeds geanalyseerd maar niet opgeslagen

### Voor Specifieke Projecten (Alleen bepaalde soorten)
1. Gebruik de **Include List** voor exacte controle
2. **LET OP**: Alle niet-genoemde soorten worden genegeerd
3. Test eerst met kleine lijst voordat u live gaat

### Voor Geografische Filtering
1. Configureer latitude/longitude correct in Settings
2. Pas `SF_THRESH` (Species Frequency Threshold) aan
   - Hogere waarde = minder soorten (meer restrictief)
   - Lagere waarde = meer soorten (minder restrictief)
3. Test beide Meta Data model versies (v1 vs v2.4)
4. Gebruik `scripts/species.py` om voorspelde soorten te zien

### Voor Uitzonderingen
1. Gebruik **Whitelist** voor soorten die normaal gefilterd zouden worden
2. Combineer met geografische filtering voor optimale resultaten

## Configuratie Parameters

Alle parameters worden beheerd in `/etc/birdnet/birdnet.conf`:

```ini
LATITUDE=52.3676        # Voor geografische filtering
LONGITUDE=4.9041        # Voor geografische filtering
CONFIDENCE=0.7          # Minimum betrouwbaarheidsscore (0.0-1.0)
SENSITIVITY=1.0         # Model gevoeligheid (0.5-1.5)
SF_THRESH=0.05          # Species Occurrence drempelwaarde
DATA_MODEL_VERSION=2    # Meta data model versie (1 of 2)
PRIVACY_THRESHOLD=0     # Privacy filter voor menselijke geluiden
```

## Test Commando

Om te zien welke soorten het systeem voor uw locatie voorspelt:

```bash
python3 scripts/species.py --threshold 0.05
```

Dit toont alle soorten die boven de threshold liggen voor uw locatie en huidige week.

## Backup en Restore

De species lists worden meegenomen in backup/restore operaties:
- `scripts/backup_data.sh` bevat alle drie de lijsten
- Lijsten worden bewaard tijdens systeem updates
- Symlinks in `~/BirdNET-Pi/scripts/` verwijzen naar hoofdlijsten

## Conclusie

**Antwoord op de vraag**: Ja, het is zeker mogelijk om soorten uit het BirdNET model te filteren, met de volgende kanttekeningen:

✅ **WAT WEL KAN**:
- Soorten blokkeren via exclude list
- Alleen specifieke soorten detecteren via include list
- Geografische filtering via Meta Data models
- Drempelwaarde overrides via whitelist
- Alle filtering via web interface te beheren

❌ **WAT NIET KAN**:
- Het .tflite model zelf aanpassen
- Performance verbetering door filtering (model draait volledig)
- Nieuwe soorten toevoegen die niet in het model zitten
- Model permanent verkleinen

**AANBEVELING**: Voor de meeste gebruikers is de combinatie van geografische filtering (Meta Data model) en een gerichte exclude list de beste aanpak. Dit geeft goede resultaten zonder te restrictief te zijn.

## Referenties

### Code Locaties
- **Analyse pipeline**: `scripts/utils/analysis.py`
- **Model management**: `scripts/utils/models.py`
- **Species lijst UI**: `scripts/species_list.php`
- **Web interface**: `homepage/views.php`
- **Helper functies**: `scripts/utils/helpers.py`

### Model Bestanden
- **Labels**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt` (6522 soorten)
- **Classificatie model**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite`
- **Meta data v1**: `model/BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite`
- **Meta data v2**: `model/BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite`

### Configuratie
- **Species lists**: `~/BirdNET-Pi/{include,exclude,whitelist}_species_list.txt`
- **Systeem config**: `/etc/birdnet/birdnet.conf`

---

*Dit audit document beschrijft de huidige staat van het systeem zonder wijzigingen aan te brengen, zoals verzocht.*
