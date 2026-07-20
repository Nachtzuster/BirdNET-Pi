# External Integrations Notes

This document captures the current behavior and lessons learned for external image integrations, especially Wikimedia.

## Bird Image Flow

The bird image API lives in [backend/app/routers/integrations.py](/Users/cpieper/code/cpieper/BirdNET-Pibird/backend/app/routers/integrations.py).

Current Wikimedia flow:

1. `GET /api/image/{sci_name}` checks `scripts/wikipedia.db`.
2. If a cached row exists, the API returns a local BirdNET asset URL:
   `/api/image-asset/wikipedia/{sci_name}`.
3. `GET /api/image-asset/...` serves a local cached file if present.
4. If the local file is missing, the API tries to download it from the cached remote Wikimedia URL.
5. If the cached URL is missing or malformed, the API re-fetches the Wikipedia summary and repopulates the cache before retrying the local asset cache.

This is intentional. The browser should not receive `upload.wikimedia.org` URLs directly for Wikipedia images.

The frontend `SpeciesImage` component also keeps an in-memory request cache and uses `IntersectionObserver` with a generous root margin. This prevents repeated cards for the same species from triggering duplicate API calls and avoids loading images far below the visible page.

## Cache Layout

- Metadata cache DB: `scripts/wikipedia.db`
- Legacy successful image table: `images`
- Additional fetch metadata table: `image_fetch_meta`
- Local duplicated image files: `scripts/image-cache/wikipedia/`

The `images` table remains part of the cache schema for compatibility with existing metadata rows and cache readers.

Cached image asset responses set browser cache headers:

- Wikipedia assets: `public, max-age=604800, stale-while-revalidate=86400`
- Flickr assets: shorter-lived cache headers suitable for a provider-backed image

## Why Negative Caching Exists

Some species pages do not have usable images, and some requests fail transiently.

- Successful image lookups are cached.
- "No image" results are also cached for a TTL to avoid repeatedly hitting Wikimedia for the same miss.
- `429` rate-limit responses are not treated as permanent misses.

## Wikimedia-Specific Rules

Two separate Wikimedia interactions exist:

- Summary metadata from `en.wikipedia.org/api/rest_v1/page/summary/...`
- Image bytes from `upload.wikimedia.org/...`

These can fail independently. A summary lookup succeeding does not mean an asset download will succeed.

Current safeguards:

- Explicit `User-Agent` is sent for both summary and image requests.
- Outgoing summary requests are rate-limited in-process.
- `429 Retry-After` is honored.
- Thumbnail URLs are rewritten down to a smaller width before local caching.
- The code prefers `thumbnail.source` over `originalimage.source`.
- Local asset filenames are sanitized from the scientific name and keep a conservative image extension from the remote URL.

## Lessons Learned

- Keep image caching changes isolated from `birds.db` and detection query code.
- Caching only metadata is not enough; asset bytes must be cached locally too.
- If the browser ever sees a Wikimedia asset URL, the solution is incomplete.
- Fallback paths matter. A missing local file must trigger rehydration, not a blind `404`.
- Logs should distinguish summary lookup failures from asset download failures.

## Useful Debug Signals

If image loading breaks again, check `birdnet-web` logs for these stages:

- `/api/image/{sci_name}` returns `200` but `/api/image-asset/...` returns `404`
- `Failed to cache local image asset for ...`
- `Wikipedia returned 429`
- `Wikipedia rate limited ... backing off`

Those messages identify which step is failing without needing full tracebacks.
