"""BirdNET-Pi FastAPI Application.

Main entry point for the web API.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import detections, species, config, system, media, integrations
from .version_metadata import read_version_metadata, normalized_service_version, normalized_git_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting BirdNET-Pi API for {settings.site_name}")
    print(f"Database: {settings.db_path}")
    yield
    # Shutdown
    print("Shutting down BirdNET-Pi API")


app = FastAPI(
    title="BirdNET-Pi API",
    description="API for BirdNET-Pi bird detection system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(detections.router, prefix="/api", tags=["detections"])
app.include_router(species.router, prefix="/api", tags=["species"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(media.router, prefix="/api", tags=["media"])
app.include_router(integrations.router, prefix="/api", tags=["integrations"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "site_name": settings.site_name,
    }


@app.get("/api/info")
async def app_info():
    """Application information."""
    settings = get_settings()
    metadata = read_version_metadata(settings.base_path)
    
    return {
        "name": "BirdNET-Pi",
        "version": normalized_service_version(metadata),
        "git_hash": normalized_git_hash(metadata),
        "git_branch": metadata.get("git_branch", "unknown"),
        "api_version": metadata.get("api_version", "1.0.0"),
        "build_date_utc": metadata.get("build_date_utc", "unknown"),
        "site_name": settings.site_name,
        "latitude": settings.latitude,
        "longitude": settings.longitude,
        "model": settings.model,
    }


# Frontend static files configuration
frontend_build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend', 'build')

if os.path.exists(frontend_build_path):
    # Mount static assets (JS, CSS, images, etc.) under /_app
    app_assets_path = os.path.join(frontend_build_path, '_app')
    if os.path.exists(app_assets_path):
        app.mount("/_app", StaticFiles(directory=app_assets_path), name="app_assets")
    
    # Serve favicon
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = os.path.join(frontend_build_path, 'favicon.ico')
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        # Fallback to favicon.png
        favicon_png = os.path.join(frontend_build_path, 'favicon.png')
        if os.path.exists(favicon_png):
            return FileResponse(favicon_png, media_type="image/png")
        return FileResponse(favicon_path)  # Will 404 if neither exists
    
    # SPA fallback: serve index.html for any non-API route
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SvelteKit SPA for any non-API route.
        
        This handles client-side routing by serving index.html for all
        paths that don't match static files or API routes.
        """
        # Check if the path maps to an actual static file
        file_path = Path(frontend_build_path) / full_path
        
        # If it's a file that exists, serve it
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Check for .html extension (pre-rendered pages)
        html_path = file_path.with_suffix('.html')
        if html_path.is_file():
            return FileResponse(html_path)
        
        # Check for index.html in directory
        index_path = file_path / 'index.html'
        if index_path.is_file():
            return FileResponse(index_path)
        
        # SPA fallback: serve the main index.html
        index_html = Path(frontend_build_path) / 'index.html'
        if index_html.is_file():
            return FileResponse(index_html)
        
        # Last resort fallback (shouldn't happen)
        return FileResponse(os.path.join(frontend_build_path, 'index.html'))
