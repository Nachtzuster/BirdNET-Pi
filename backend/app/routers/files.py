"""Admin-only file management API endpoints."""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import Settings, get_settings
from ..dependencies import verify_credentials
from ..models.schemas import (
    FileDeleteResponse,
    FileEntry,
    FileListingResponse,
    FileRoot,
    FileRootsResponse,
)

router = APIRouter()


@dataclass(frozen=True)
class RootDefinition:
    """Logical file-manager root."""
    id: str
    label: str
    description: str
    path: Path


def list_root_definitions(settings: Settings) -> list[RootDefinition]:
    """Return the allowlisted logical roots for the file manager."""
    return [
        RootDefinition(
            id="recordings",
            label="Recordings",
            description="Organized detection clips under By_Date.",
            path=Path(settings.by_date_dir),
        ),
        RootDefinition(
            id="shifted",
            label="Shifted Audio",
            description="Pitch-shifted clips generated from Library.",
            path=Path(settings.by_date_dir) / "shifted",
        ),
        RootDefinition(
            id="charts",
            label="Charts",
            description="Generated daily chart images.",
            path=Path(settings.charts_dir),
        ),
        RootDefinition(
            id="raw",
            label="Raw Stream",
            description="Live capture segments from StreamData.",
            path=Path(settings.recs_dir) / "StreamData",
        ),
    ]


def get_root_definition(root_id: str, settings: Settings) -> RootDefinition:
    """Look up a logical root by id."""
    for root in list_root_definitions(settings):
        if root.id == root_id:
            return root
    raise HTTPException(status_code=404, detail="Unknown file root")


def normalize_relative_path(relative_path: str) -> list[str]:
    """Normalize a user-supplied relative path and reject traversal."""
    if not relative_path or relative_path == ".":
        return []

    parts: list[str] = []
    for part in PurePosixPath(relative_path.replace("\\", "/")).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise HTTPException(status_code=403, detail="Access denied")
        parts.append(part)
    return parts


def resolve_scoped_path(root: RootDefinition, relative_path: str = "") -> Path:
    """Resolve a relative path under a logical root and keep it in-bounds."""
    base_path = root.path.resolve()
    full_path = (base_path / Path(*normalize_relative_path(relative_path))).resolve()

    try:
        full_path.relative_to(base_path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied") from exc

    return full_path


def relative_path_within_root(root: RootDefinition, path: Path) -> str:
    """Return the normalized path relative to the logical root."""
    relative = path.resolve().relative_to(root.path.resolve())
    return relative.as_posix() if str(relative) != "." else ""


def build_entry(root: RootDefinition, entry: Path) -> FileEntry | None:
    """Build a file entry if it resolves safely under the configured root."""
    try:
        resolved = entry.resolve()
        resolved.relative_to(root.path.resolve())
    except (FileNotFoundError, ValueError):
        return None

    if entry.name.startswith("."):
        return None

    stat = entry.stat()
    entry_type = "directory" if entry.is_dir() else "file"
    size = None if entry_type == "directory" else stat.st_size

    return FileEntry(
        name=entry.name,
        path=relative_path_within_root(root, entry),
        entry_type=entry_type,
        size=size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    )


@router.get("/files/roots", response_model=FileRootsResponse)
async def list_file_roots(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """List the allowlisted logical roots for the file manager."""
    del user

    roots = [
        FileRoot(
            id=root.id,
            label=root.label,
            description=root.description,
            available=root.path.exists(),
        )
        for root in list_root_definitions(settings)
    ]
    return FileRootsResponse(roots=roots)


@router.get("/files/list", response_model=FileListingResponse)
async def list_files(
    root: str = Query(...),
    path: str = Query(""),
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """List files within a logical root."""
    del user

    root_definition = get_root_definition(root, settings)
    current_dir = resolve_scoped_path(root_definition, path)

    if not current_dir.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not current_dir.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries: list[FileEntry] = []
    for child in sorted(current_dir.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        item = build_entry(root_definition, child)
        if item is not None:
            entries.append(item)

    current_path = relative_path_within_root(root_definition, current_dir)
    parent_path = None
    if current_path:
        parent_path = Path(current_path).parent.as_posix()
        if parent_path == ".":
            parent_path = ""

    return FileListingResponse(
        root=root_definition.id,
        root_label=root_definition.label,
        current_path=current_path,
        parent_path=parent_path,
        entries=entries,
    )


@router.get("/files/download")
async def download_file(
    root: str = Query(...),
    path: str = Query(...),
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Download a file from a logical root."""
    del user

    root_definition = get_root_definition(root, settings)
    file_path = resolve_scoped_path(root_definition, path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return FileResponse(file_path, filename=file_path.name)


@router.delete("/files", response_model=FileDeleteResponse)
async def delete_file(
    root: str = Query(...),
    path: str = Query(...),
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Delete a file or an empty directory from a logical root."""
    del user

    root_definition = get_root_definition(root, settings)
    target_path = resolve_scoped_path(root_definition, path)

    if target_path == root_definition.path.resolve():
        raise HTTPException(status_code=400, detail="Cannot delete a root directory")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target_path.is_dir():
        try:
            target_path.rmdir()
        except OSError as exc:
            raise HTTPException(status_code=400, detail="Directory is not empty") from exc
    else:
        os.remove(target_path)

    return FileDeleteResponse(
        message="Deleted successfully",
        path="/".join(normalize_relative_path(path)),
    )
