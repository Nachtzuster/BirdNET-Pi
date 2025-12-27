# Audit: Species Filtering Capabilities in BirdNET Model

**Date**: December 18, 2025  
**Model**: BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite  
**Audit Type**: Technical feasibility analysis for species filtering

## Executive Summary

**Yes, it is possible to filter specific species from the BirdNET model.** The system currently offers three different filtering mechanisms that operate post-inference. The filtering does not occur within the .tflite model itself, but rather in the processing logic that handles the model output.

## Current Filtering Mechanisms

### 1. Include Species List (Whitelist)
**File**: `~/BirdNET-Pi/include_species_list.txt`  
**Function**: Whitelist - Only species on this list will be recognized  
**Use Case**: For users who want to detect ONLY specific species  
**Warning**: If this list contains ANY species, ALL other species will be excluded

**Implementation Location**: 
- `scripts/utils/analysis.py`, lines 141, 166-167
- Web interface: `homepage/views.php`, line 185

### 2. Exclude Species List (Blacklist)
**File**: `~/BirdNET-Pi/exclude_species_list.txt`  
**Function**: Blacklist - Species on this list will NOT be recognized  
**Use Case**: For users who want to exclude specific species  

**Implementation Location**:
- `scripts/utils/analysis.py`, lines 142, 168-169
- Web interface: `homepage/views.php`, line 193

### 3. Whitelist Species List (Threshold Override)
**File**: `~/BirdNET-Pi/whitelist_species_list.txt`  
**Function**: Overrides the Species Occurrence Frequency threshold  
**Use Case**: Species will be detected even if they fall below the geographic occurrence threshold  
**Note**: Not the recommended approach - try Species Occurrence models v1 and v2.4 first

**Implementation Location**:
- `scripts/utils/analysis.py`, lines 143, 170-171
- Web interface: `homepage/views.php`, line 201

## Technical Architecture

### Model Components

The BirdNET model consists of multiple components:

1. **Classification Model**: `BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite`
   - Primary model for audio classification
   - Generates 6522 predictions (one per species)
   - Operates independently of filtering

2. **Meta Data Models**: 
   - `BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite` (version 1)
   - `BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite` (version 2)
   - Used for geographic and temporal filtering
   - Based on latitude, longitude, and week number

3. **Labels File**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt`
   - Contains 6522 species names in scientific notation
   - Examples: `Pica pica`, `Accipiter nisus`, etc.

### Processing Pipeline

```
Audio Input
    ↓
[BirdNET Model Inference] ← No filtering here (6522 species)
    ↓
[All predictions sorted by confidence]
    ↓
[Top 10 per audio chunk retained]
    ↓
[Privacy Filter] ← Removes human sounds
    ↓
[Confidence Threshold Filter] ← Minimum confidence score
    ↓
[Include List Filter] ← If list not empty: only these species
    ↓
[Exclude List Filter] ← Remove these species
    ↓
[Species Occurrence Filter] ← Geographic/temporal filtering
    ↓
[Whitelist Override] ← Allow despite low occurrence
    ↓
Final Detections
```

### Code Implementation

Filtering is performed in `scripts/utils/analysis.py`, function `run_analysis()`:

```python
# Load the three species lists
include_list = loadCustomSpeciesList("~/BirdNET-Pi/include_species_list.txt")
exclude_list = loadCustomSpeciesList("~/BirdNET-Pi/exclude_species_list.txt")
whitelist_list = loadCustomSpeciesList("~/BirdNET-Pi/whitelist_species_list.txt")

# For each detection with sufficient confidence:
if sci_name not in include_list and len(include_list) != 0:
    # Excluded: not in include list
elif sci_name in exclude_list and len(exclude_list) != 0:
    # Excluded: in exclude list
elif sci_name not in predicted_species_list and sci_name not in whitelist_list:
    # Excluded: below geographic threshold
else:
    # Accepted
```

### Function: loadCustomSpeciesList()

Located in `scripts/utils/analysis.py`, lines 17-23:

```python
def loadCustomSpeciesList(path):
    species_list = []
    if os.path.isfile(path):
        with open(path, 'r') as csfile:
            species_list = [line.strip().split('_')[0] for line in csfile.readlines()]
    return species_list
```

**Important Note**: The function extracts the genus from `Genus_species` format, returning only `Genus`.

## Web Interface

Users can manage species through the web interface:

**Navigation**: Tools → Settings → Species Lists
- **Included Species**: Manage include list
- **Excluded Species**: Manage exclude list  
- **Whitelisted Species**: Manage whitelist

**Features**:
- Search functionality for quick access to species
- Drag-and-drop interface for adding/removing
- Real-time validation

**Implementation**: 
- `scripts/species_list.php` - UI rendering
- `homepage/views.php` - Server-side processing

## Limitations and Considerations

### 1. The .tflite Model Cannot be Modified
- The TensorFlow Lite model is a compiled binary file
- Species cannot be permanently removed from the model
- The model always generates predictions for all 6522 species
- Filtering only happens post-inference in Python code

### 2. Performance Implications
- **No performance benefit**: The model always runs full inference
- **Filtering is fast**: String matching in Python is negligible
- **Memory usage**: Unchanged - full model stays in memory

### 3. Geographic Filtering (Meta Data Model)
- Uses Species Occurrence Frequency threshold
- Based on eBird data and occurrence patterns
- Configurable via `SF_THRESH` parameter
- Two versions available (v1 and v2.4) with different algorithms

### 4. File Format
The species list files use a specific format:
```
Genus_species
```
Examples:
```
Pica_pica
Turdus_merula
Erithacus_rubecula
```

**Important**: Use scientific names as found in `labels.txt`

## Best Practices

### For Simple Filtering (< 50 species)
1. Use the **Exclude List** to block unwanted species
2. Manage via web interface (Tools → Settings → Excluded Species)
3. Species are still analyzed but not saved

### For Specific Projects (Only certain species)
1. Use the **Include List** for exact control
2. **WARNING**: All unlisted species will be ignored
3. Test with a small list first before going live

### For Geographic Filtering
1. Configure latitude/longitude correctly in Settings
2. Adjust `SF_THRESH` (Species Frequency Threshold)
   - Higher value = fewer species (more restrictive)
   - Lower value = more species (less restrictive)
3. Test both Meta Data model versions (v1 vs v2.4)
4. Use `scripts/species.py` to preview predicted species

### For Exceptions
1. Use **Whitelist** for species that would normally be filtered
2. Combine with geographic filtering for optimal results

## Configuration Parameters

All parameters are managed in `/etc/birdnet/birdnet.conf`:

```ini
LATITUDE=52.3676        # For geographic filtering
LONGITUDE=4.9041        # For geographic filtering
CONFIDENCE=0.7          # Minimum confidence score (0.0-1.0)
SENSITIVITY=1.0         # Model sensitivity (0.5-1.5)
SF_THRESH=0.05          # Species Occurrence threshold
DATA_MODEL_VERSION=2    # Meta data model version (1 or 2)
PRIVACY_THRESHOLD=0     # Privacy filter for human sounds
```

## Testing Command

To see which species the system predicts for your location:

```bash
python3 scripts/species.py --threshold 0.05
```

This displays all species above the threshold for your location and current week.

## Backup and Restore

Species lists are included in backup/restore operations:
- `scripts/backup_data.sh` includes all three lists
- Lists are preserved during system updates
- Symlinks in `~/BirdNET-Pi/scripts/` point to main lists

## Practical Examples

### Example 1: Exclude Common Nuisance Species

Create or edit `~/BirdNET-Pi/exclude_species_list.txt`:
```
Corvus_corone
Pica_pica
Columba_livia
```

This will exclude crows, magpies, and rock doves from all detections.

### Example 2: Monitor Only Owls

Create or edit `~/BirdNET-Pi/include_species_list.txt`:
```
Strix_aluco
Athene_noctua
Asio_otus
Tyto_alba
```

This will ONLY detect Tawny Owl, Little Owl, Long-eared Owl, and Barn Owl.

### Example 3: Rare Species Monitoring

Use geographic filtering with a whitelist override:
1. Set `SF_THRESH=0.1` (higher threshold, fewer species)
2. Add rare species to `whitelist_species_list.txt`:
```
Bubo_bubo
Aquila_chrysaetos
```

This ensures Eagle Owl and Golden Eagle are detected even if rare in your area.

## Diagnostic Tools

### Check Current Species Lists

```bash
# View current exclude list
cat ~/BirdNET-Pi/exclude_species_list.txt

# View current include list
cat ~/BirdNET-Pi/include_species_list.txt

# View current whitelist
cat ~/BirdNET-Pi/whitelist_species_list.txt

# Count entries
wc -l ~/BirdNET-Pi/*_species_list.txt
```

### Preview Species for Your Location

```bash
# Default threshold (0.05)
python3 /home/$USER/BirdNET-Pi/scripts/species.py

# Custom threshold
python3 /home/$USER/BirdNET-Pi/scripts/species.py --threshold 0.03
```

### Validate Species Names

All valid species names are in:
```bash
cat /home/$USER/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt
```

Search for a specific species:
```bash
grep -i "turdus" /home/$USER/BirdNET-Pi/model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt
```

## Conclusion

**Answer to the question**: Yes, it is definitely possible to filter species from the BirdNET model, with the following considerations:

✅ **WHAT IS POSSIBLE**:
- Block species via exclude list
- Detect only specific species via include list
- Geographic filtering via Meta Data models
- Threshold overrides via whitelist
- Manage all filtering via web interface

❌ **WHAT IS NOT POSSIBLE**:
- Modify the .tflite model itself
- Performance improvement through filtering (model runs fully)
- Add new species not in the model
- Permanently reduce model size

**RECOMMENDATION**: For most users, the combination of geographic filtering (Meta Data model) and a targeted exclude list is the best approach. This provides good results without being too restrictive.

## Code Flow Diagram

```
run_analysis() in scripts/utils/analysis.py
    │
    ├── Load species lists (lines 141-143)
    │   ├── include_list
    │   ├── exclude_list
    │   └── whitelist_list
    │
    ├── Read audio with readAudioData()
    │
    ├── Analyze with analyzeAudioData()
    │   ├── load_global_model()
    │   ├── model.set_meta_data(lat, lon, week)
    │   ├── model.get_species_list() → predicted_species_list
    │   └── filter_humans()
    │
    └── For each detection (lines 160-182)
        ├── Check confidence >= CONFIDENCE threshold
        │
        ├── Include list check (lines 166-167)
        │   └── If include_list not empty AND species NOT in list → REJECT
        │
        ├── Exclude list check (lines 168-169)
        │   └── If exclude_list not empty AND species IN list → REJECT
        │
        ├── Geographic filter check (lines 170-171)
        │   └── If species NOT in predicted_species_list 
        │       AND species NOT in whitelist → REJECT
        │
        └── ACCEPT → Create Detection object
```

## References

### Code Locations
- **Analysis pipeline**: `scripts/utils/analysis.py`
- **Model management**: `scripts/utils/models.py`
- **Species list UI**: `scripts/species_list.php`
- **Web interface**: `homepage/views.php`
- **Helper functions**: `scripts/utils/helpers.py`

### Model Files
- **Labels**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt` (6522 species)
- **Classification model**: `model/BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite`
- **Meta data v1**: `model/BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite`
- **Meta data v2**: `model/BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite`

### Configuration
- **Species lists**: `~/BirdNET-Pi/{include,exclude,whitelist}_species_list.txt`
- **System config**: `/etc/birdnet/birdnet.conf`

---

*This audit document describes the current state of the system without making any modifications, as requested.*
