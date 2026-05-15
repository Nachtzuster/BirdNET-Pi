"""Media serving API endpoints."""
import os
import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..config import get_settings, Settings
from ..dependencies import verify_credentials

router = APIRouter()


def extract_species_from_filename(filename: str) -> str:
    """Extract the species folder name from a BirdNET filename.

    Filenames follow the pattern: CommonName-confidence-date-birdnet-time.mp3
    Example: White-throated_Sparrow-70-2026-02-03-birdnet-17:53:14.mp3
             -> White-throated_Sparrow
    """
    # Match pattern: species name followed by -NUMBER-YYYY
    match = re.match(r'^(.+?)-\d+-\d{4}-', filename)
    if match:
        return match.group(1)
    # Fallback
    parts = re.split(r'-(?=\d)', filename, maxsplit=1)
    return parts[0] if parts else filename


def validate_path(base: str, *parts: str) -> Path:
    """Validate that a path stays within the base directory.

    Prevents path traversal attacks.
    """
    base_path = Path(base).resolve()
    full_path = (base_path / Path(*parts)).resolve()

    if not str(full_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="Access denied")

    return full_path


@router.get("/media/audio/{date}/{species}/{filename}")
async def get_audio(
    date: str,
    species: str,
    filename: str,
    settings: Settings = Depends(get_settings),
):
    """Serve an audio file.

    Args:
        date: Detection date (YYYY-MM-DD)
        species: Scientific name (with spaces replaced by underscores in URL)
        filename: Audio filename
    """
    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    # Validate and build path
    species_folder = extract_species_from_filename(filename)
    file_path = validate_path(settings.by_date_dir, date, species_folder, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Determine media type based on extension
    ext = file_path.suffix.lower()
    media_types = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
    }
    media_type = media_types.get(ext, 'audio/wav')

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
    )


@router.get("/media/spectrogram/{date}/{species}/{filename}")
async def get_spectrogram(
    date: str,
    species: str,
    filename: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a spectrogram image.

    Args:
        date: Detection date (YYYY-MM-DD)
        species: Scientific name
        filename: Base filename (will append .png if needed)
    """
    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    # Ensure .png extension
    if not filename.endswith('.png'):
        filename = filename + '.png'

    species_folder = extract_species_from_filename(filename)
    file_path = validate_path(settings.by_date_dir, date, species_folder, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Spectrogram not found")

    return FileResponse(file_path, media_type="image/png")


@router.get("/media/chart/{date}")
async def get_daily_chart(
    date: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a daily chart image.

    Args:
        date: Chart date (YYYY-MM-DD)
    """
    filename = f"Combo-{date}.png"
    file_path = validate_path(settings.charts_dir, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found")

    return FileResponse(file_path, media_type="image/png")


@router.get("/media/shifted/{date}/{species}/{filename}")
async def get_shifted_audio(
    date: str,
    species: str,
    filename: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a frequency-shifted audio file.

    Args:
        date: Detection date (YYYY-MM-DD)
        species: Scientific name
        filename: Audio filename
    """
    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    shifted_dir = os.path.join(settings.by_date_dir, 'shifted')
    species_folder = extract_species_from_filename(filename)
    file_path = validate_path(shifted_dir, date, species_folder, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Shifted audio file not found")

    ext = file_path.suffix.lower()
    media_type = 'audio/wav' if ext == '.wav' else 'audio/mpeg'

    return FileResponse(file_path, media_type=media_type)


@router.post("/media/shift/{date}/{species}/{filename}")
async def create_shifted_audio(
    date: str,
    species: str,
    filename: str,
    pitch: int = -1000,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Create a frequency-shifted version of an audio file.

    Args:
        date: Detection date (YYYY-MM-DD)
        species: Scientific name
        filename: Audio filename
        pitch: Pitch shift in cents (default -1000 = one octave down)
    """
    import subprocess

    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    # Source file
    species_folder = extract_species_from_filename(filename)
    source_path = validate_path(settings.by_date_dir, date, species_folder, filename)

    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source audio file not found")

    # Create shifted directory structure
    shifted_dir = os.path.join(settings.by_date_dir, 'shifted', date, species_folder)
    os.makedirs(shifted_dir, exist_ok=True)

    output_path = os.path.join(shifted_dir, filename)

    # Try sox first, then ffmpeg
    try:
        result = subprocess.run(
            ['sox', str(source_path), output_path, 'pitch', str(pitch)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Try ffmpeg
            # Convert pitch cents to ratio: -1000 cents = half frequency
            ratio = 2 ** (pitch / 1200)
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', str(source_path),
                 '-af', f'rubberband=pitch={ratio}', output_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

        if result.returncode == 0:
            return {
                "message": "Shifted audio created",
                "path": f"/api/media/shifted/{date}/{species}/{filename}",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create shifted audio: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Operation timed out")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Neither sox nor ffmpeg found. Install one of them."
        )


@router.delete("/media/shift/{date}/{species}/{filename}")
async def delete_shifted_audio(
    date: str,
    species: str,
    filename: str,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Delete a frequency-shifted audio file."""
    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    shifted_dir = os.path.join(settings.by_date_dir, 'shifted')
    species_folder = extract_species_from_filename(filename)
    file_path = validate_path(shifted_dir, date, species_folder, filename)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Shifted audio file not found")

    os.remove(file_path)

    return {"message": "Shifted audio deleted"}


@router.get("/media/dates")
async def list_dates_with_recordings(
    settings: Settings = Depends(get_settings),
):
    """List all dates that have recordings."""
    by_date_dir = settings.by_date_dir

    if not os.path.exists(by_date_dir):
        return {"dates": []}

    dates = []
    for entry in os.listdir(by_date_dir):
        entry_path = os.path.join(by_date_dir, entry)
        # Check if it's a directory and looks like a date
        if os.path.isdir(entry_path) and len(entry) == 10 and entry.count('-') == 2:
            dates.append(entry)

    dates.sort(reverse=True)
    return {"dates": dates}


@router.get("/media/dates/{date}/species")
async def list_species_for_date(
    date: str,
    settings: Settings = Depends(get_settings),
):
    """List all species with recordings for a specific date."""
    date_dir = os.path.join(settings.by_date_dir, date)

    if not os.path.exists(date_dir):
        raise HTTPException(status_code=404, detail="No recordings for this date")

    species = []
    for entry in os.listdir(date_dir):
        entry_path = os.path.join(date_dir, entry)
        if os.path.isdir(entry_path) and not entry.startswith('.'):
            # Count files
            files = [f for f in os.listdir(entry_path) if not f.endswith('.png')]
            species.append({
                "name": entry,
                "count": len(files),
            })

    species.sort(key=lambda x: x['count'], reverse=True)
    return {"date": date, "species": species}


@router.get("/media/dates/{date}/{species}/meta")
async def get_species_meta_for_date(
    date: str,
    species: str,
    settings: Settings = Depends(get_settings),
):
    """Resolve species metadata (scientific/common names) for a date folder species."""
    species = species.replace(' ', '_')
    like_pattern = f"{species}-%"

    conn = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT Sci_Name, Com_Name
            FROM detections
            WHERE Date = ? AND File_Name LIKE ?
            ORDER BY Time DESC
            LIMIT 1
            """,
            (date, like_pattern),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Species metadata not found")

    return {
        "date": date,
        "species": species,
        "sci_name": row["Sci_Name"],
        "com_name": row["Com_Name"],
    }


@router.get("/media/dates/{date}/{species}/files")
async def list_files_for_species(
    date: str,
    species: str,
    settings: Settings = Depends(get_settings),
):
    """List all files for a specific species on a date."""
    # Normalize species name: spaces to underscores (filesystem uses underscores)
    species = species.replace(' ', '_')

    species_dir = os.path.join(settings.by_date_dir, date, species)

    if not os.path.exists(species_dir):
        raise HTTPException(status_code=404, detail="No recordings found")

    files = []
    for filename in os.listdir(species_dir):
        if not filename.endswith('.png'):
            filepath = os.path.join(species_dir, filename)
            files.append({
                "name": filename,
                "has_spectrogram": os.path.exists(filepath + '.png'),
                "size": os.path.getsize(filepath),
            })

    files.sort(key=lambda x: x['name'], reverse=True)
    return {"date": date, "species": species, "files": files}
