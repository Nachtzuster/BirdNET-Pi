"""FastAPI dependencies for BirdNET-Pi API.

Provides database connections, authentication, and other shared dependencies.
"""
import os
import re
import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import get_settings, Settings

# HTTP Basic Authentication
security = HTTPBasic()


def get_db_connection(readonly: bool = True) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection.

    Args:
        readonly: If True, open database in read-only mode

    Yields:
        SQLite connection with Row factory
    """
    settings = get_settings()
    db_path = settings.db_path

    # check_same_thread=False is required for uvicorn workers
    if readonly:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(db_path, check_same_thread=False)

    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get a read-only database connection."""
    yield from get_db_connection(readonly=True)


def get_db_write() -> Generator[sqlite3.Connection, None, None]:
    """Get a writable database connection."""
    yield from get_db_connection(readonly=False)


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> str:
    """Verify HTTP Basic Auth credentials.

    Args:
        credentials: HTTP Basic credentials
        settings: Application settings

    Returns:
        Username if authenticated

    Raises:
        HTTPException: If credentials are invalid or password not configured
    """
    correct_username = "birdnet"
    correct_password = settings.caddy_password

    # If no password is configured, deny access with helpful message
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Please set CADDY_PWD in /etc/birdnet/birdnet.conf",
        )

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def optional_auth(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> str | None:
    """Optional authentication - doesn't raise if invalid.

    Returns:
        Username if authenticated, None otherwise
    """
    try:
        return verify_credentials(credentials, settings)
    except HTTPException:
        return None


# Species list file paths
def get_species_list_path(list_type: str) -> str:
    """Get the path to a species list file.

    Args:
        list_type: One of 'include', 'exclude', 'whitelist', 'confirmed'

    Returns:
        Full path to the species list file

    Raises:
        ValueError: If list_type is invalid
    """
    settings = get_settings()
    list_files = {
        'include': 'include_species_list.txt',
        'exclude': 'exclude_species_list.txt',
        'whitelist': 'whitelist_species_list.txt',
        'confirmed': 'confirmed_species_list.txt',
    }

    if list_type not in list_files:
        raise ValueError(f"Invalid list type: {list_type}. Must be one of {list(list_files.keys())}")

    return os.path.join(settings.base_path, 'scripts', list_files[list_type])


def read_species_list(list_type: str) -> list[str]:
    """Read a species list file.

    Args:
        list_type: One of 'include', 'exclude', 'whitelist', 'confirmed'

    Returns:
        List of species names (scientific names)
    """
    path = get_species_list_path(list_type)
    try:
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def write_species_list(list_type: str, species: list[str]) -> None:
    """Write a species list file.

    Args:
        list_type: One of 'include', 'exclude', 'whitelist', 'confirmed'
        species: List of species names to write
    """
    path = get_species_list_path(list_type)
    with open(path, 'w') as f:
        f.write('\n'.join(species))
        if species:
            f.write('\n')


# Species name utilities for file system operations
def extract_species_from_filename(filename: str) -> str:
    """Extract the species folder name from a BirdNET filename.

    Filenames follow the pattern: CommonName-confidence-date-birdnet-time.ext
    Example: White-throated_Sparrow-70-2026-02-03-birdnet-17:53:14.mp3
             -> White-throated_Sparrow

    Args:
        filename: The audio filename

    Returns:
        The species folder name (common name with underscores)
    """
    # Match pattern: species name followed by -NUMBER-YYYY
    match = re.match(r'^(.+?)-\d+-\d{4}-', filename)
    if match:
        return match.group(1)
    # Fallback: split on first hyphen followed by digit
    parts = re.split(r'-(?=\d)', filename, maxsplit=1)
    return parts[0] if parts else filename


def common_name_to_folder(common_name: str) -> str:
    """Convert a common name to the folder name format.

    Removes apostrophes and replaces spaces with underscores.
    Example: "Cooper's Hawk" -> "Coopers_Hawk"
             "Mourning Dove" -> "Mourning_Dove"

    Args:
        common_name: The common name from the database

    Returns:
        The folder-safe name
    """
    return common_name.replace("'", "").replace(" ", "_")
