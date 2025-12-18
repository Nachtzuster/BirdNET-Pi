# Species Filtering Quick Reference Guide

## Quick Start

### Web Interface (Recommended)
1. Navigate to: **Tools → Settings → Species Lists**
2. Choose one of three lists:
   - **Included Species** - Only these species (whitelist)
   - **Excluded Species** - Never these species (blacklist)
   - **Whitelisted Species** - Override geographic threshold

### Command Line

```bash
# View all available species
cat ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt

# View species predicted for your location
python3 ~/BirdNET-Pi/scripts/species.py --threshold 0.05

# Edit exclude list
nano ~/BirdNET-Pi/exclude_species_list.txt

# Edit include list (USE WITH CAUTION)
nano ~/BirdNET-Pi/include_species_list.txt

# Edit whitelist
nano ~/BirdNET-Pi/whitelist_species_list.txt
```

## Common Use Cases

### 1. Exclude Noisy Urban Birds
**File**: `~/BirdNET-Pi/exclude_species_list.txt`
```
Corvus_corone
Pica_pica
Columba_livia
Columba_palumbus
Sturnus_vulgaris
Passer_domesticus
```

### 2. Monitor Only Raptors
**File**: `~/BirdNET-Pi/include_species_list.txt`
```
Accipiter_nisus
Buteo_buteo
Falco_tinnunculus
Milvus_milvus
Pernis_apivorus
```

### 3. Monitor Only Owls (Night Monitoring)
**File**: `~/BirdNET-Pi/include_species_list.txt`
```
Strix_aluco
Athene_noctua
Asio_otus
Tyto_alba
Bubo_bubo
```

### 4. Monitor Only Warblers
**File**: `~/BirdNET-Pi/include_species_list.txt`
```
Phylloscopus_collybita
Phylloscopus_trochilus
Sylvia_atricapilla
Sylvia_borin
Sylvia_communis
Acrocephalus_scirpaceus
Acrocephalus_palustris
```

### 5. Exclude Domestic/Exotic Species
**File**: `~/BirdNET-Pi/exclude_species_list.txt`
```
Gallus_gallus
Anas_platyrhynchos_domesticus
Psittacula_krameri
Branta_canadensis
Cygnus_olor
```

### 6. Force Detection of Rare Species
**File**: `~/BirdNET-Pi/whitelist_species_list.txt`
```
Bubo_bubo
Aquila_chrysaetos
Pandion_haliaetus
Alcedo_atthis
Lanius_collurio
```

## File Format Rules

### Correct Format
```
Genus_species
```

### Examples
✅ Correct:
```
Pica_pica
Turdus_merula
Erithacus_rubecula
```

❌ Incorrect:
```
Pica pica          # Missing underscore
pica_pica          # Lowercase genus
PICA_PICA          # All uppercase
Magpie             # Common name
Pica_pica_pica     # Too many parts
```

## Important Warnings

### ⚠️ Include List Warning
**IF YOU ADD ANY SPECIES TO THE INCLUDE LIST, ALL OTHER SPECIES WILL BE IGNORED!**

The include list is for dedicated monitoring projects only. For most users, the exclude list is safer.

### ⚠️ Whitelist Warning
The whitelist overrides geographic filtering. Use sparingly and only for species you know occur in your area but fall below the threshold.

### ⚠️ Format Warning
Always use the exact scientific name from the labels file:
```bash
cat ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt | grep -i "species_name"
```

## Configuration Parameters

Edit `/etc/birdnet/birdnet.conf`:

```ini
# Minimum confidence to record a detection (0.0-1.0)
CONFIDENCE=0.7

# Model sensitivity (0.5-1.5, higher = more sensitive)
SENSITIVITY=1.0

# Species occurrence frequency threshold (0.0-1.0)
SF_THRESH=0.05

# Meta data model version (1 or 2)
DATA_MODEL_VERSION=2

# Your location for geographic filtering
LATITUDE=52.3676
LONGITUDE=4.9041
```

## Testing Your Configuration

### 1. Preview Species List
```bash
# See what species will be detected for your location
python3 ~/BirdNET-Pi/scripts/species.py --threshold 0.05
```

### 2. Check Your Lists
```bash
# Count species in each list
echo "Include list: $(wc -l < ~/BirdNET-Pi/include_species_list.txt) species"
echo "Exclude list: $(wc -l < ~/BirdNET-Pi/exclude_species_list.txt) species"
echo "Whitelist: $(wc -l < ~/BirdNET-Pi/whitelist_species_list.txt) species"

# View lists
echo "=== INCLUDE LIST ===" && cat ~/BirdNET-Pi/include_species_list.txt
echo "=== EXCLUDE LIST ===" && cat ~/BirdNET-Pi/exclude_species_list.txt
echo "=== WHITELIST ===" && cat ~/BirdNET-Pi/whitelist_species_list.txt
```

### 3. Validate Species Names
```bash
# Check if a species exists in the model
SPECIES="Pica_pica"
if grep -q "^${SPECIES}$" ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt; then
    echo "✓ ${SPECIES} is valid"
else
    echo "✗ ${SPECIES} not found in model"
fi
```

### 4. Search for Species
```bash
# Find all species containing "turdus" (thrushes)
grep -i "turdus" ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt

# Find all species starting with "Parus" (tits)
grep "^Parus_" ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt
```

## Troubleshooting

### Species Not Being Filtered
1. **Check file path**: Lists must be in `~/BirdNET-Pi/`
2. **Check file name**: Must be exactly `{include,exclude,whitelist}_species_list.txt`
3. **Check format**: Each species on its own line, `Genus_species` format
4. **Restart services**: 
   ```bash
   # Via web interface: Tools → Services → Restart Core Services
   # Or command line:
   sudo systemctl restart birdnet_analysis.service
   ```

### Species Still Detected Despite Exclude List
1. **Check confidence threshold**: Detection might be from whitelist
2. **Check spelling**: Must match exactly (case-sensitive)
3. **Check logs**: 
   ```bash
   tail -f ~/BirdSongs/Processed/birdnet_analysis.log
   ```

### Include List Not Working
1. **Verify not empty**: Empty include list = all species detected
2. **Check species names**: One species per line
3. **No blank lines**: Remove empty lines from file
   ```bash
   sed -i '/^$/d' ~/BirdNET-Pi/include_species_list.txt
   ```

### Geographic Filtering Too Restrictive
1. **Lower threshold**: Edit SF_THRESH in `/etc/birdnet/birdnet.conf`
2. **Try different model**: Switch DATA_MODEL_VERSION between 1 and 2
3. **Use whitelist**: Add specific species to override threshold

## Performance Tips

### Filtering Does NOT Improve Performance
- The model always runs full inference (all 6522 species)
- Filtering happens after model inference
- Use filtering for data quality, not performance

### To Improve Performance
1. Adjust recording quality/length
2. Use appropriate hardware (Pi 4/5 recommended)
3. Enable TMPFS for temp files (if available)
4. Reduce RECORDING_LENGTH if possible

## Backup and Restore

### Backup Lists
```bash
# Create backup
cp ~/BirdNET-Pi/exclude_species_list.txt ~/BirdNET-Pi/exclude_species_list.txt.backup
cp ~/BirdNET-Pi/include_species_list.txt ~/BirdNET-Pi/include_species_list.txt.backup
cp ~/BirdNET-Pi/whitelist_species_list.txt ~/BirdNET-Pi/whitelist_species_list.txt.backup
```

### Restore Lists
```bash
# Restore from backup
cp ~/BirdNET-Pi/exclude_species_list.txt.backup ~/BirdNET-Pi/exclude_species_list.txt
cp ~/BirdNET-Pi/include_species_list.txt.backup ~/BirdNET-Pi/include_species_list.txt
cp ~/BirdNET-Pi/whitelist_species_list.txt.backup ~/BirdNET-Pi/whitelist_species_list.txt

# Restart service
sudo systemctl restart birdnet_analysis.service
```

## Advanced: Generate Lists Programmatically

### All European Thrushes
```bash
grep "^Turdus_" ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt > ~/BirdNET-Pi/include_species_list.txt
```

### All Owls (Strigiformes)
```bash
grep -E "^(Strix|Athene|Asio|Tyto|Bubo|Glaucidium|Aegolius|Surnia|Nyctea)_" \
    ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt \
    > ~/BirdNET-Pi/include_species_list.txt
```

### All Corvids
```bash
grep -E "^(Corvus|Pica|Garrulus|Nucifraga|Pyrrhocorax|Cyanopica)_" \
    ~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt \
    > ~/BirdNET-Pi/exclude_species_list.txt
```

## Resources

- **All Species**: `~/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt`
- **Configuration**: `/etc/birdnet/birdnet.conf`
- **Logs**: `~/BirdSongs/Processed/birdnet_analysis.log`
- **Database**: `~/BirdNET-Pi/scripts/birds.db`

## Help

For questions and issues:
1. Check the main README: `~/BirdNET-Pi/README.md`
2. Visit the discussions: https://github.com/mcguirepr89/BirdNET-Pi/discussions
3. Check the wiki: https://github.com/mcguirepr89/BirdNET-Pi/wiki
