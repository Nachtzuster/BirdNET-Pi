# Documentation Index

## Species Filtering Documentation

This directory contains comprehensive documentation about species filtering capabilities in BirdNET-Pi.

### 📋 Quick Start
**Read this first**: [SPECIES_FILTERING_SUMMARY.md](SPECIES_FILTERING_SUMMARY.md)

A concise executive summary answering: "Can I filter species from the BirdNET model?" with key findings and recommendations.

### 📖 Full Documentation

#### 🇳🇱 Dutch Version (Nederlands)
**File**: [SPECIES_FILTERING_AUDIT.md](SPECIES_FILTERING_AUDIT.md)

Volledige technische analyse in het Nederlands met:
- Alle filtermechanismen
- Implementatie details
- Configuratie parameters
- Code referenties

#### 🇬🇧 English Version
**File**: [SPECIES_FILTERING_AUDIT_EN.md](SPECIES_FILTERING_AUDIT_EN.md)

Complete technical analysis in English with:
- All filtering mechanisms
- Implementation details
- Configuration parameters
- Code references
- Practical examples
- Diagnostic tools

### ⚡ Quick Reference
**File**: [SPECIES_FILTERING_QUICK_REFERENCE.md](SPECIES_FILTERING_QUICK_REFERENCE.md)

Hands-on guide with:
- Common use case examples (owls only, exclude corvids, etc.)
- Command-line snippets
- File format specifications
- Troubleshooting guide
- Testing procedures

## Document Overview

| Document | Size | Language | Purpose |
|----------|------|----------|---------|
| SPECIES_FILTERING_SUMMARY.md | 7 KB | EN | Executive summary |
| SPECIES_FILTERING_AUDIT.md | 9 KB | NL | Full technical audit (Dutch) |
| SPECIES_FILTERING_AUDIT_EN.md | 12 KB | EN | Full technical audit (English) |
| SPECIES_FILTERING_QUICK_REFERENCE.md | 8 KB | EN | Practical quick reference |

## Key Findings Summary

### ✅ YES - Species Filtering is Possible

The BirdNET-Pi system provides **three mechanisms** to filter species:

1. **Include List** (`include_species_list.txt`) - Whitelist: only detect these species
2. **Exclude List** (`exclude_species_list.txt`) - Blacklist: never detect these species
3. **Whitelist** (`whitelist_species_list.txt`) - Override geographic threshold for specific species

### How It Works

```
Audio → Model (6522 species) → Filters → Final Detections
```

Filtering happens **after** model inference in the Python analysis pipeline, not in the `.tflite` model itself.

### Quick Access

- **Web Interface**: Tools → Settings → Species Lists
- **Command Line**: Edit `~/BirdNET-Pi/{include,exclude,whitelist}_species_list.txt`
- **Preview**: `python3 scripts/species.py --threshold 0.05`

## For Users

### First Time Users
1. Start with [SPECIES_FILTERING_SUMMARY.md](SPECIES_FILTERING_SUMMARY.md)
2. Then read [SPECIES_FILTERING_QUICK_REFERENCE.md](SPECIES_FILTERING_QUICK_REFERENCE.md)
3. Try examples from the quick reference

### Technical Users
1. Read full audit: [SPECIES_FILTERING_AUDIT_EN.md](SPECIES_FILTERING_AUDIT_EN.md)
2. Review code references
3. Understand processing pipeline

### Dutch Speakers
1. Begin met [SPECIES_FILTERING_SUMMARY.md](SPECIES_FILTERING_SUMMARY.md)
2. Lees de volledige audit: [SPECIES_FILTERING_AUDIT.md](SPECIES_FILTERING_AUDIT.md)
3. Gebruik [SPECIES_FILTERING_QUICK_REFERENCE.md](SPECIES_FILTERING_QUICK_REFERENCE.md) voor praktische voorbeelden

## Other Documentation

### Translations
See [translations.md](translations.md) for information about language support and species name translations.

### Screenshots
- [overview.png](overview.png) - BirdNET-Pi overview
- [spectrogram.png](spectrogram.png) - Spectrogram view

## Related Files in Repository

### Code
- `scripts/utils/analysis.py` - Main filtering implementation
- `scripts/utils/models.py` - Model loading and meta data
- `scripts/species.py` - Species preview tool

### Web Interface
- `homepage/views.php` - Main view controller
- `scripts/species_list.php` - Species list management UI

### Configuration
- `/etc/birdnet/birdnet.conf` - System configuration
- `~/BirdNET-Pi/{include,exclude,whitelist}_species_list.txt` - Species filter lists

## Contributing

Found an issue or have a suggestion for this documentation? Please open an issue or discussion in the repository.

## License

This documentation follows the same license as BirdNET-Pi. See the main [LICENSE](../LICENSE) file for details.

---

**Documentation Version**: 1.0  
**Last Updated**: December 18, 2025  
**Audit Status**: Complete - No code modifications made
