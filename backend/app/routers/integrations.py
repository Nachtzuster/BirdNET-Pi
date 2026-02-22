"""External integration API endpoints (Flickr, Wikipedia, BirdWeather)."""
import json
import logging
import os
import sqlite3
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import get_settings, Settings
from ..models.schemas import BirdImage
from ..species_links import build_species_links

logger = logging.getLogger(__name__)

router = APIRouter()


# Image cache database
def get_image_cache_db(provider: str, settings: Settings) -> sqlite3.Connection:
    """Get connection to image cache database."""
    db_name = f"{provider}.db"
    db_path = os.path.join(settings.base_path, 'scripts', db_name)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            sci_name TEXT PRIMARY KEY,
            com_en_name TEXT,
            image_url TEXT,
            title TEXT,
            id TEXT,
            author_url TEXT,
            license_url TEXT,
            date_created TEXT
        )
    """)
    conn.commit()
    
    return conn


def get_cached_image(sci_name: str, provider: str, settings: Settings) -> Optional[dict]:
    """Get cached image from database."""
    try:
        conn = get_image_cache_db(provider, settings)
        cursor = conn.execute(
            "SELECT * FROM images WHERE sci_name = ?",
            (sci_name,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception:
        return None


def cache_image(sci_name: str, image_data: dict, provider: str, settings: Settings):
    """Cache image data in database."""
    try:
        conn = get_image_cache_db(provider, settings)
        conn.execute("""
            INSERT OR REPLACE INTO images 
            (sci_name, com_en_name, image_url, title, id, author_url, license_url, date_created)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            sci_name,
            image_data.get('com_name', ''),
            image_data.get('url', ''),
            image_data.get('title', ''),
            image_data.get('id', ''),
            image_data.get('author_url', ''),
            image_data.get('license_url', ''),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


@router.get("/image/{sci_name}", response_model=Optional[BirdImage])
async def get_bird_image(
    sci_name: str,
    force_refresh: bool = False,
    settings: Settings = Depends(get_settings),
):
    """Get an image for a bird species.
    
    Tries cached image first, then fetches from configured provider.
    Returns null if no image is available (instead of 404).
    
    Args:
        sci_name: Scientific name of the species
        force_refresh: If True, skip cache and fetch fresh image
    """
    provider = settings.image_provider.lower()
    logger.debug("Image request for '%s' using provider '%s'", sci_name, provider)
    
    # Check cache first
    if not force_refresh:
        cached = get_cached_image(sci_name, provider, settings)
        if cached and cached.get('image_url'):
            logger.debug("Cache hit for '%s'", sci_name)
            return BirdImage(
                url=cached['image_url'],
                title=cached.get('title'),
                author_url=cached.get('author_url'),
                license_url=cached.get('license_url'),
                source=provider,
            )
    
    # Fetch from provider
    if provider == 'flickr':
        image = await fetch_flickr_image(sci_name, settings)
    elif provider == 'wikipedia':
        image = await fetch_wikipedia_image(sci_name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown image provider: {provider}")
    
    if image:
        logger.debug("Fetched image for '%s' from %s: %s", sci_name, provider, image.url)
        # Cache the result
        cache_image(sci_name, {
            'url': image.url,
            'title': image.title,
            'author_url': image.author_url,
            'license_url': image.license_url,
        }, provider, settings)
        return image
    
    logger.warning("No image found for '%s' from provider '%s'", sci_name, provider)
    # Return null instead of 404 - let frontend handle gracefully
    return None


async def fetch_flickr_image(sci_name: str, settings: Settings) -> Optional[BirdImage]:
    """Fetch bird image from Flickr API."""
    api_key = settings.flickr_api_key
    
    if not api_key:
        logger.debug("No Flickr API key configured, skipping Flickr for '%s'", sci_name)
        return None
    
    async with httpx.AsyncClient() as client:
        # Search for photos
        search_url = "https://www.flickr.com/services/rest/"
        params = {
            'method': 'flickr.photos.search',
            'api_key': api_key,
            'text': sci_name,
            'sort': 'relevance',
            'media': 'photos',
            'content_type': 1,  # Photos only
            'per_page': 1,
            'format': 'json',
            'nojsoncallback': 1,
            'license': '1,2,3,4,5,6,9,10',  # Creative Commons licenses
        }
        
        try:
            response = await client.get(search_url, params=params, timeout=10)
            data = response.json()
            
            if data.get('stat') != 'ok' or not data.get('photos', {}).get('photo'):
                return None
            
            photo = data['photos']['photo'][0]
            photo_id = photo['id']
            
            # Get photo info for URL and license
            info_params = {
                'method': 'flickr.photos.getInfo',
                'api_key': api_key,
                'photo_id': photo_id,
                'format': 'json',
                'nojsoncallback': 1,
            }
            
            info_response = await client.get(search_url, params=info_params, timeout=10)
            info_data = info_response.json()
            
            if info_data.get('stat') != 'ok':
                return None
            
            photo_info = info_data['photo']
            
            # Build image URL
            server = photo['server']
            secret = photo['secret']
            image_url = f"https://live.staticflickr.com/{server}/{photo_id}_{secret}_b.jpg"
            
            # Get owner info
            owner = photo_info.get('owner', {})
            author_url = f"https://www.flickr.com/photos/{owner.get('nsid', '')}"
            
            return BirdImage(
                url=image_url,
                title=photo_info.get('title', {}).get('_content', ''),
                author=owner.get('username', ''),
                author_url=author_url,
                license_url=photo_info.get('license', ''),
                source='flickr',
            )
        except Exception as e:
            logger.error("Flickr fetch failed for '%s': %s", sci_name, e)
            return None


async def fetch_wikipedia_image(sci_name: str) -> Optional[BirdImage]:
    """Fetch bird image from Wikipedia API."""
    headers = {
        "User-Agent": "BirdNET-Pi/1.0 (https://github.com/tphakala/BirdNET-Pi; bird detection project)",
    }
    async with httpx.AsyncClient(headers=headers) as client:
        # Use Wikipedia REST API to get page summary
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{sci_name.replace(' ', '_')}"
        
        try:
            response = await client.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning("Wikipedia returned %d for '%s'", response.status_code, sci_name)
                return None
            
            data = response.json()
            
            # Get thumbnail or original image
            thumbnail = data.get('thumbnail', {})
            original = data.get('originalimage', {})
            
            image_url = original.get('source') or thumbnail.get('source')
            
            if not image_url:
                logger.debug("Wikipedia page for '%s' has no image", sci_name)
                return None
            
            return BirdImage(
                url=image_url,
                title=data.get('title', sci_name),
                source='wikipedia',
            )
        except Exception as e:
            logger.error("Wikipedia fetch failed for '%s': %s", sci_name, e)
            return None


@router.post("/image/{sci_name}/blacklist")
async def blacklist_image(
    sci_name: str,
    settings: Settings = Depends(get_settings),
):
    """Blacklist the current cached image for a species.
    
    This will remove the cached image and try to fetch a different one.
    """
    provider = settings.image_provider.lower()
    
    # Remove from cache
    try:
        conn = get_image_cache_db(provider, settings)
        conn.execute("DELETE FROM images WHERE sci_name = ?", (sci_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"message": f"Image for {sci_name} blacklisted and removed from cache"}


@router.get("/birdweather/status")
async def get_birdweather_status(
    settings: Settings = Depends(get_settings),
):
    """Get BirdWeather integration status."""
    station_id = settings.birdweather_id
    
    return {
        "enabled": bool(station_id),
        "station_id": station_id if station_id else None,
        "station_url": f"https://app.birdweather.com/stations/{station_id}" if station_id else None,
    }


@router.get("/species-links/{sci_name}")
async def get_species_links(
    sci_name: str,
    com_name: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
):
    """Get external species reference links (eBird and All About Birds)."""
    return build_species_links(
        sci_name=sci_name,
        com_name=com_name,
        language=settings.database_lang,
    )


@router.get("/labels")
async def get_all_labels(
    settings: Settings = Depends(get_settings),
):
    """Get all species labels in current language."""
    from utils.helpers import get_language, get_model_labels
    
    try:
        language = get_language()
        model_labels = get_model_labels()
        
        # Build mapping of scientific name to common name
        labels = {}
        for sci_name in model_labels:
            labels[sci_name] = language.get(sci_name, sci_name)
        
        return {
            "language": settings.database_lang,
            "count": len(labels),
            "labels": labels,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels/{sci_name}")
async def get_species_label(
    sci_name: str,
    settings: Settings = Depends(get_settings),
):
    """Get the localized common name for a species."""
    from utils.helpers import get_language
    
    try:
        language = get_language()
        com_name = language.get(sci_name, sci_name)
        
        return {
            "sci_name": sci_name,
            "com_name": com_name,
            "language": settings.database_lang,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ebird/export/{date}")
async def export_ebird_data(
    date: str,
    min_confidence: float = 0.75,
    settings: Settings = Depends(get_settings),
):
    """Export detections for a date in eBird format.
    
    Args:
        date: Date to export (YYYY-MM-DD)
        min_confidence: Minimum confidence threshold (default 0.75)
    """
    import sqlite3
    from datetime import datetime
    
    db_path = settings.db_path
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    
    # Get detections for the date
    cursor = conn.execute("""
        SELECT Sci_Name, Com_Name, Time, Confidence
        FROM detections
        WHERE Date = ? AND Confidence >= ?
        ORDER BY Sci_Name, Time
    """, (date, min_confidence))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Group by species and hour (eBird wants max 1 per hour per species)
    species_hours = {}
    for row in rows:
        key = (row['Sci_Name'], row['Time'][:2])  # Group by species and hour
        if key not in species_hours:
            species_hours[key] = row
    
    # Build eBird CSV format
    lines = ["Common Name,Scientific Name,Count,Location,Date,Time,Notes"]
    
    for key, row in species_hours.items():
        line = f'"{row["Com_Name"]}","{row["Sci_Name"]}",1,"{settings.site_name}",{date},{row["Time"][:5]},"BirdNET detection (confidence: {row["Confidence"]:.2f})"'
        lines.append(line)
    
    csv_content = '\n'.join(lines)
    
    return {
        "date": date,
        "species_count": len(species_hours),
        "csv": csv_content,
    }
