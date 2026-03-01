"""Species API endpoints."""
import os
import shutil
import sqlite3
import subprocess
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import get_settings, Settings
from ..dependencies import (
    get_db,
    verify_credentials,
    read_species_list,
    write_species_list,
    common_name_to_folder,
)
from ..models.schemas import SpeciesSummary, SpeciesList, SpeciesListResponse, SpeciesListUpdate

router = APIRouter()


def normalize_species_key(species_entry: str) -> str:
    """Normalize species list entries to scientific name only."""
    return species_entry.split('_', 1)[0].strip()


@router.get("/species", response_model=SpeciesList)
async def list_species(
    sort: str = Query("count", pattern="^(count|confidence|date|name)$"),
    date: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get list of all species with detection counts.

    Args:
        sort: Sort order - count, confidence, date, or name
        date: Optional date filter (YYYY-MM-DD)
    """
    where = "" if date is None else f'WHERE Date = "{date}"'

    sort_map = {
        "count": "COUNT(*) DESC",
        "confidence": "MAX(Confidence) DESC",
        "date": "MIN(Date) DESC, Time DESC",
        "name": "Com_Name ASC",
    }
    order_by = sort_map.get(sort, "COUNT(*) DESC")

    select_sql = f"""
        SELECT Date, Time, File_Name, Com_Name, Sci_Name,
               COUNT(*) as Count, MAX(Confidence) as MaxConfidence
        FROM detections
        {where}
        GROUP BY Sci_Name
        ORDER BY {order_by}
    """

    cursor = db.execute(select_sql)
    rows = cursor.fetchall()

    species = [SpeciesSummary.model_validate(dict(row)) for row in rows]

    return SpeciesList(species=species, total=len(species))


@router.get("/species/{sci_name}/detections")
async def get_species_detections(
    sci_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Get all detections for a specific species."""
    # Get total count
    count_sql = "SELECT COUNT(*) FROM detections WHERE Sci_Name = ?"
    total = db.execute(count_sql, (sci_name,)).fetchone()[0]

    if total == 0:
        raise HTTPException(status_code=404, detail=f"No detections found for {sci_name}")

    # Get detections
    select_sql = """
        SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
               Cutoff, Week, Sens, Overlap, File_Name
        FROM detections
        WHERE Sci_Name = ?
        ORDER BY Date DESC, Time DESC
        LIMIT ? OFFSET ?
    """

    cursor = db.execute(select_sql, (sci_name, limit, offset))
    rows = cursor.fetchall()

    return {
        "species": sci_name,
        "detections": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/species/{sci_name}/chart-data")
async def get_species_chart_data(
    sci_name: str,
    days: int = Query(7, ge=1, le=365),
    db: sqlite3.Connection = Depends(get_db),
):
    """Get detection counts per day for a species (for charts)."""
    select_sql = """
        SELECT Date, COUNT(*) as Count
        FROM detections
        WHERE Sci_Name = ?
        AND Date >= DATE('now', 'localtime', ?)
        GROUP BY Date
        ORDER BY Date ASC
    """

    cursor = db.execute(select_sql, (sci_name, f'-{days} days'))
    rows = cursor.fetchall()

    # Get common name
    com_name_row = db.execute(
        "SELECT Com_Name FROM detections WHERE Sci_Name = ? LIMIT 1",
        (sci_name,)
    ).fetchone()
    com_name = com_name_row[0] if com_name_row else sci_name

    return {
        "species": sci_name,
        "com_name": com_name,
        "days": days,
        "data": [{"date": row[0], "count": row[1]} for row in rows],
    }


@router.get("/species/{sci_name}/stats")
async def get_species_stats(
    sci_name: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get statistics for a specific species."""
    stats_sql = """
        SELECT
            COUNT(*) as total_detections,
            COUNT(DISTINCT Date) as days_detected,
            MIN(Date) as first_detection,
            MAX(Date) as last_detection,
            AVG(Confidence) as avg_confidence,
            MAX(Confidence) as max_confidence
        FROM detections
        WHERE Sci_Name = ?
    """

    row = db.execute(stats_sql, (sci_name,)).fetchone()

    if not row or row[0] == 0:
        raise HTTPException(status_code=404, detail=f"No detections found for {sci_name}")

    # Get common name
    com_name_row = db.execute(
        "SELECT Com_Name FROM detections WHERE Sci_Name = ? LIMIT 1",
        (sci_name,)
    ).fetchone()

    return {
        "sci_name": sci_name,
        "com_name": com_name_row[0] if com_name_row else sci_name,
        "total_detections": row[0],
        "days_detected": row[1],
        "first_detection": row[2],
        "last_detection": row[3],
        "avg_confidence": round(row[4], 4) if row[4] else 0,
        "max_confidence": row[5],
    }


@router.delete("/species/{sci_name}")
async def delete_species_data(
    sci_name: str,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Delete all data for a species (detections and files).

    Requires authentication.
    """
    # Get all detection files for this species
    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row

    try:
        # Get the common name and dates for this species
        cursor = db.execute(
            "SELECT DISTINCT Date, Com_Name FROM detections WHERE Sci_Name = ?",
            (sci_name,)
        )
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No detections found for {sci_name}")

        dates = [row[0] for row in rows]
        # Get the common name (should be consistent across all detections)
        common_name = rows[0][1]

        # Delete from database
        db.execute("DELETE FROM detections WHERE Sci_Name = ?", (sci_name,))
        db.commit()
    finally:
        db.close()

    # Convert common name to folder format (removes apostrophes, replaces spaces with underscores)
    species_folder = common_name_to_folder(common_name)

    # Delete species directories for each date
    deleted_dirs = []
    for date in dates:
        species_dir = os.path.join(settings.by_date_dir, date, species_folder)
        if os.path.exists(species_dir):
            try:
                shutil.rmtree(species_dir)
                deleted_dirs.append(species_dir)
            except PermissionError:
                subprocess.run(['sudo', 'rm', '-r', species_dir], check=True)
                deleted_dirs.append(species_dir)

    return {
        "message": f"Deleted all data for {sci_name}",
        "deleted_directories": deleted_dirs,
    }


# Species list management endpoints
@router.get("/species-lists/{list_type}", response_model=SpeciesListResponse)
async def get_species_list(
    list_type: str,
):
    """Get contents of a species list.

    Args:
        list_type: One of 'include', 'exclude', 'whitelist', 'confirmed'
    """
    try:
        species = read_species_list(list_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    normalized_species = sorted(set(normalize_species_key(item) for item in species if item.strip()))

    return SpeciesListResponse(list_type=list_type, species=normalized_species)


@router.post("/species-lists/{list_type}")
async def update_species_list(
    list_type: str,
    update: SpeciesListUpdate,
    user: str = Depends(verify_credentials),
):
    """Add or remove a species from a list.

    Requires authentication.

    Args:
        list_type: One of 'include', 'exclude', 'whitelist', 'confirmed'
        update: Species and action (add/remove)
    """
    try:
        current_list = read_species_list(list_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    normalized_species = normalize_species_key(update.species)
    current_keys = {normalize_species_key(item) for item in current_list if item.strip()}

    if update.action == "add":
        if normalized_species not in current_keys:
            current_list.append(normalized_species)
    elif update.action == "remove":
        current_list = [
            item for item in current_list
            if normalize_species_key(item) != normalized_species
        ]

    current_list = sorted(
        {normalize_species_key(item) for item in current_list if item.strip()}
    )
    write_species_list(list_type, current_list)

    return {
        "message": f"Species {update.action}ed {'to' if update.action == 'add' else 'from'} {list_type} list",
        "species": normalized_species,
        "list_type": list_type,
    }


@router.get("/species/{sci_name}/lists")
async def get_species_list_membership(
    sci_name: str,
):
    """Check which lists a species belongs to."""
    membership = {}
    for list_type in ['include', 'exclude', 'whitelist', 'confirmed']:
        species_list = read_species_list(list_type)
        membership[list_type] = any(
            normalize_species_key(item) == sci_name
            for item in species_list
        )

    return {
        "species": sci_name,
        "lists": membership,
    }
