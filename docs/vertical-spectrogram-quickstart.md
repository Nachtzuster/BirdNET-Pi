# Vertical Spectrogram - Quick Reference

## Direct Access URLs

### Standalone View
Access directly on your smartphone or tablet:
```
http://[your-device]/scripts/vertical_spectrogram.php
```

Examples:
- `http://birdnetpi.local/scripts/vertical_spectrogram.php`
- `http://192.168.1.100/scripts/vertical_spectrogram.php`

### Embedded View
Access through main interface:
```
http://[your-device]/views.php?view=Vertical+Spectrogram
```

## Quick Settings Guide

### Color Schemes
| Scheme | Best For |
|--------|----------|
| **Purple** | General use, default |
| **Black-White** | Battery saving, high contrast |
| **Lava** | Dramatic visualization |
| **Green-White** | Night viewing, reduced eye strain |

### Low-Cut Filter Settings
| Environment | Recommended Frequency |
|-------------|---------------------|
| Indoor/Quiet | 50-100 Hz |
| Outdoor/Garden | 150-250 Hz |
| Urban/Noisy | 300-500 Hz |

### Performance Settings
| Device | Redraw Interval |
|--------|----------------|
| Raspberry Pi 3/0W2 | 100-150 ms |
| Raspberry Pi 4 | 75-100 ms |
| Raspberry Pi 5 | 50-75 ms |
| Smartphone | 100-150 ms |

## Buttons & Controls

| Button | Function |
|--------|----------|
| ⛶ | Toggle fullscreen |
| − | Collapse controls |
| + | Expand controls |

## Keyboard Shortcuts

- **ESC** - Exit fullscreen
- **F11** - Browser fullscreen (desktop)

## Troubleshooting

**Problem:** Controls keep disappearing
- **Solution:** Touch screen or move mouse to show them

**Problem:** No sound
- **Solution:** Check audio permissions in browser

**Problem:** Colors look washed out
- **Solution:** Try different color scheme or adjust gain

**Problem:** Too much background noise
- **Solution:** Enable low-cut filter (200-300 Hz)

## Tips

1. **Bookmark the standalone URL** for quick mobile access
2. **Use fullscreen mode** for dedicated tablet displays
3. **Enable auto-rotate** for flexible viewing angles
4. **Adjust gain** if signals are too weak or clipping
5. **Use landscape mode** for wider frequency display

## Support

For detailed information, see: `docs/vertical-spectrogram-features.md`
