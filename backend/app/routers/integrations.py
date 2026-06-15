"""External integration API endpoints (Flickr, Wikipedia, BirdWeather)."""
import asyncio
import logging
import os
import re
import sqlite3
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import get_settings, Settings
from ..dependencies import verify_credentials
from ..models.schemas import BirdImage
from ..species_links import build_species_links

logger = logging.getLogger(__name__)

router = APIRouter()

NEGATIVE_CACHE_TTL_SECONDS = 12 * 60 * 60
WIKIMEDIA_MIN_REQUEST_INTERVAL_SECONDS = 0.5
WIKIMEDIA_DEFAULT_RETRY_AFTER_SECONDS = 60
WIKIMEDIA_LOCAL_CACHE_MAX_WIDTH = 640
IMAGE_ASSET_CACHE_SECONDS = {
    'wikipedia': 7 * 24 * 60 * 60,
    'flickr': 60 * 60,
}

_wikimedia_request_lock: Optional[asyncio.Lock] = None
_wikimedia_lock_loop_id: Optional[int] = None
_wikimedia_next_request_at = 0.0
_wikimedia_cooldown_until = 0.0


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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS image_fetch_meta (
            sci_name TEXT PRIMARY KEY,
            has_image INTEGER NOT NULL,
            local_path TEXT,
            last_checked_epoch INTEGER NOT NULL
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


def get_cached_fetch_meta(sci_name: str, provider: str, settings: Settings) -> Optional[dict]:
    """Get fetch metadata from database."""
    try:
        conn = get_image_cache_db(provider, settings)
        cursor = conn.execute(
            "SELECT has_image, local_path, last_checked_epoch FROM image_fetch_meta WHERE sci_name = ?",
            (sci_name,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def cache_fetch_meta(
    sci_name: str,
    has_image: bool,
    provider: str,
    settings: Settings,
    local_path: Optional[str] = None,
):
    """Cache fetch result metadata without changing the legacy images table schema."""
    try:
        conn = get_image_cache_db(provider, settings)
        conn.execute("""
            INSERT OR REPLACE INTO image_fetch_meta
            (sci_name, has_image, local_path, last_checked_epoch)
            VALUES (?, ?, ?, ?)
        """, (
            sci_name,
            1 if has_image else 0,
            local_path,
            int(time.time()),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def is_negative_cache_fresh(cached_meta: Optional[dict], ttl_seconds: int = NEGATIVE_CACHE_TTL_SECONDS) -> bool:
    """Return True when a no-image result was cached recently."""
    if not cached_meta or cached_meta.get('has_image'):
        return False
    last_checked_epoch = cached_meta.get('last_checked_epoch')
    if not last_checked_epoch:
        return False
    return (time.time() - int(last_checked_epoch)) < ttl_seconds


def sanitize_cache_key(sci_name: str) -> str:
    """Create a filesystem-safe cache key."""
    normalized = sci_name.strip().replace(' ', '_')
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', normalized)


def get_image_asset_dir(provider: str, settings: Settings) -> str:
    """Return local asset cache directory."""
    asset_dir = os.path.join(settings.base_path, 'scripts', 'image-cache', provider)
    os.makedirs(asset_dir, exist_ok=True)
    return asset_dir


def get_extension_from_url(url: str) -> str:
    """Extract a conservative extension from image URL."""
    path = url.split('?', 1)[0]
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
        return ext
    return '.jpg'


def get_wikimedia_headers() -> dict[str, str]:
    """Headers for Wikimedia API and asset requests."""
    return {
        "User-Agent": "BirdNET-Pi/1.0 (https://github.com/tphakala/BirdNET-Pi; bird detection project)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }


def rewrite_wikimedia_thumbnail_url(url: str, max_width: int = WIKIMEDIA_LOCAL_CACHE_MAX_WIDTH) -> str:
    """Clamp Wikimedia thumbnail URLs to a smaller width to reduce upstream load."""
    if "upload.wikimedia.org" not in url or "/thumb/" not in url:
        return url
    return re.sub(r'/\d+px-', f'/{max_width}px-', url, count=1)


async def cache_remote_image_asset(
    sci_name: str,
    provider: str,
    remote_url: str,
    settings: Settings,
) -> Optional[str]:
    """Download and cache a remote image locally so the browser no longer fetches Wikimedia directly."""
    try:
        remote_url = rewrite_wikimedia_thumbnail_url(remote_url)
        file_name = f"{sanitize_cache_key(sci_name)}{get_extension_from_url(remote_url)}"
        absolute_path = os.path.join(get_image_asset_dir(provider, settings), file_name)
        relative_path = os.path.relpath(absolute_path, settings.base_path)

        if not os.path.exists(absolute_path):
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers=get_wikimedia_headers(),
            ) as client:
                response = await client.get(remote_url, timeout=20)
                response.raise_for_status()
                with open(absolute_path, 'wb') as image_file:
                    image_file.write(response.content)

        return relative_path
    except Exception as e:
        logger.warning("Failed to cache local image asset for '%s': %s", sci_name, e)
        return None


async def ensure_local_image_asset(
    sci_name: str,
    provider: str,
    settings: Settings,
) -> Optional[str]:
    """Ensure a local cached asset exists for a cached remote image."""
    cached_meta = get_cached_fetch_meta(sci_name, provider, settings)
    local_path = cached_meta.get('local_path') if cached_meta else None
    if local_path and os.path.exists(os.path.join(settings.base_path, local_path)):
        return local_path

    cached_image = get_cached_image(sci_name, provider, settings)
    remote_url = None
    if cached_image and cached_image.get('image_url'):
        candidate_url = cached_image['image_url']
        if isinstance(candidate_url, str) and candidate_url.startswith('http'):
            remote_url = candidate_url

    # If the cached row is missing or malformed, try a fresh Wikimedia summary lookup.
    if not remote_url and provider == 'wikipedia':
        image, cacheable_miss = await fetch_wikipedia_image(sci_name)
        if image:
            cache_image(sci_name, {
                'url': image.url,
                'title': image.title,
                'author_url': image.author_url,
                'license_url': image.license_url,
            }, provider, settings)
            remote_url = image.url
        elif cacheable_miss:
            cache_fetch_meta(sci_name, has_image=False, provider=provider, settings=settings)
            return None

    if not remote_url:
        return None

    logger.debug("Caching local image asset for '%s' from %s", sci_name, remote_url)
    local_path = await cache_remote_image_asset(sci_name, provider, remote_url, settings)
    if local_path:
        cache_fetch_meta(
            sci_name,
            has_image=True,
            provider=provider,
            settings=settings,
            local_path=local_path,
        )
    return local_path


def build_local_asset_url(provider: str, sci_name: str) -> str:
    """Build API URL for a cached local image asset."""
    return f"/api/image-asset/{provider}/{sci_name}"


def get_image_asset_cache_headers(provider: str) -> dict[str, str]:
    """Return browser cache headers for locally cached image assets."""
    max_age = IMAGE_ASSET_CACHE_SECONDS.get(provider.lower(), 60 * 60)
    return {
        "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=86400",
    }


def parse_retry_after_seconds(retry_after_header: Optional[str]) -> int:
    """Parse Retry-After header as seconds."""
    if not retry_after_header:
        return WIKIMEDIA_DEFAULT_RETRY_AFTER_SECONDS
    try:
        return max(1, int(retry_after_header))
    except ValueError:
        return WIKIMEDIA_DEFAULT_RETRY_AFTER_SECONDS


def get_wikimedia_request_lock() -> asyncio.Lock:
    """Return a loop-local lock for Wikimedia request pacing."""
    global _wikimedia_request_lock
    global _wikimedia_lock_loop_id

    running_loop = asyncio.get_running_loop()
    running_loop_id = id(running_loop)
    if _wikimedia_request_lock is None or _wikimedia_lock_loop_id != running_loop_id:
        _wikimedia_request_lock = asyncio.Lock()
        _wikimedia_lock_loop_id = running_loop_id
    return _wikimedia_request_lock


async def await_wikimedia_request_slot():
    """Rate-limit outgoing Wikimedia requests inside the API process."""
    global _wikimedia_next_request_at

    lock = get_wikimedia_request_lock()
    async with lock:
        now = time.monotonic()
        wait_seconds = max(0.0, _wikimedia_next_request_at - now, _wikimedia_cooldown_until - now)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        _wikimedia_next_request_at = time.monotonic() + WIKIMEDIA_MIN_REQUEST_INTERVAL_SECONDS


async def apply_wikimedia_backoff(cooldown_seconds: int):
    """Honor Wikimedia retry windows after 429 responses."""
    global _wikimedia_cooldown_until

    if cooldown_seconds <= 0:
        return

    lock = get_wikimedia_request_lock()
    async with lock:
        _wikimedia_cooldown_until = max(
            _wikimedia_cooldown_until,
            time.monotonic() + cooldown_seconds,
        )


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

    if provider in {'', 'none'}:
        logger.debug("Image provider disabled for '%s'", sci_name)
        return None

    # Check cache first
    if not force_refresh:
        cached = get_cached_image(sci_name, provider, settings)
        if cached and cached.get('image_url'):
            logger.debug("Cache hit for '%s'", sci_name)
            return BirdImage(
                url=build_local_asset_url(provider, sci_name) if provider == 'wikipedia' else cached['image_url'],
                title=cached.get('title'),
                author_url=cached.get('author_url'),
                license_url=cached.get('license_url'),
                source=provider,
            )
        cached_meta = get_cached_fetch_meta(sci_name, provider, settings)
        if provider == 'wikipedia' and is_negative_cache_fresh(cached_meta):
            logger.debug("Negative image cache hit for '%s'", sci_name)
            return None

    # Fetch from provider
    cacheable_miss = True
    if provider == 'flickr':
        image = await fetch_flickr_image(sci_name, settings)
    elif provider == 'wikipedia':
        image, cacheable_miss = await fetch_wikipedia_image(sci_name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown image provider: {provider}")

    if image:
        logger.debug("Fetched image for '%s' from %s: %s", sci_name, provider, image.url)
        local_path = await cache_remote_image_asset(sci_name, provider, image.url, settings)
        # Cache the result
        cache_image(sci_name, {
            'url': image.url,
            'title': image.title,
            'author_url': image.author_url,
            'license_url': image.license_url,
        }, provider, settings)
        cache_fetch_meta(sci_name, has_image=True, provider=provider, settings=settings, local_path=local_path)
        if provider == 'wikipedia':
            image.url = build_local_asset_url(provider, sci_name)
        elif local_path:
            image.url = build_local_asset_url(provider, sci_name)
        return image

    logger.warning("No image found for '%s' from provider '%s'", sci_name, provider)
    if provider == 'wikipedia' and cacheable_miss:
        cache_fetch_meta(sci_name, has_image=False, provider=provider, settings=settings)
    # Return null instead of 404 - let frontend handle gracefully
    return None


async def fetch_flickr_image(sci_name: str, settings: Settings) -> Optional[BirdImage]:
    """Fetch bird image from Flickr API."""
    api_key = settings.flickr_api_key
    filter_email = settings.flickr_filter_email.strip()

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
            if filter_email:
                user_lookup = await client.get(search_url, params={
                    'method': 'flickr.people.findByEmail',
                    'api_key': api_key,
                    'find_email': filter_email,
                    'format': 'json',
                    'nojsoncallback': 1,
                }, timeout=10)
                user_lookup_data = user_lookup.json()
                user_id = user_lookup_data.get('user', {}).get('nsid')
                if user_lookup_data.get('stat') == 'ok' and user_id:
                    params['user_id'] = user_id

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


async def fetch_wikipedia_image(sci_name: str) -> tuple[Optional[BirdImage], bool]:
    """Fetch bird image from Wikipedia API.

    Returns (image, cacheable_miss).
    """
    headers = get_wikimedia_headers()
    async with httpx.AsyncClient(headers=headers) as client:
        # Use Wikipedia REST API to get page summary
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{sci_name.replace(' ', '_')}"

        try:
            await await_wikimedia_request_slot()
            response = await client.get(url, timeout=10)

            if response.status_code == 429:
                retry_after_seconds = parse_retry_after_seconds(response.headers.get('Retry-After'))
                await apply_wikimedia_backoff(retry_after_seconds)
                logger.warning(
                    "Wikipedia rate limited '%s' (429), backing off for %ds",
                    sci_name,
                    retry_after_seconds,
                )
                return None, False

            if response.status_code != 200:
                logger.warning("Wikipedia returned %d for '%s'", response.status_code, sci_name)
                return None, True

            data = response.json()

            # Prefer the summary thumbnail over the original to avoid oversized asset fetches.
            thumbnail = data.get('thumbnail', {})
            original = data.get('originalimage', {})

            image_url = thumbnail.get('source') or original.get('source')

            if not image_url:
                logger.debug("Wikipedia page for '%s' has no image", sci_name)
                return None, True

            return BirdImage(
                url=image_url,
                title=data.get('title', sci_name),
                source='wikipedia',
            ), True
        except Exception as e:
            logger.error("Wikipedia fetch failed for '%s': %s", sci_name, e)
            return None, False


@router.get("/image-asset/{provider}/{sci_name:path}")
async def get_cached_image_asset(
    provider: str,
    sci_name: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a locally cached bird image asset."""
    local_path = await ensure_local_image_asset(sci_name, provider, settings)
    if not local_path:
        raise HTTPException(status_code=404, detail="Cached image asset not found")

    file_path = os.path.join(settings.base_path, local_path)
    return FileResponse(file_path, headers=get_image_asset_cache_headers(provider))


@router.post("/image/{sci_name}/blacklist")
async def blacklist_image(
    sci_name: str,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Blacklist the current cached image for a species.

    This will remove the cached image and try to fetch a different one.
    """
    provider = settings.image_provider.lower()
    if provider in {'', 'none'}:
        return {"message": "No image provider is configured"}

    # Remove from cache
    try:
        conn = get_image_cache_db(provider, settings)
        conn.execute("DELETE FROM images WHERE sci_name = ?", (sci_name,))
        conn.execute("DELETE FROM image_fetch_meta WHERE sci_name = ?", (sci_name,))
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
        line = (
            f'"{row["Com_Name"]}","{row["Sci_Name"]}",1,"{settings.site_name}",{date},'
            f'{row["Time"][:5]},"BirdNET detection (confidence: {row["Confidence"]:.2f})"'
        )
        lines.append(line)

    csv_content = '\n'.join(lines)

    return {
        "date": date,
        "species_count": len(species_hours),
        "csv": csv_content,
    }
