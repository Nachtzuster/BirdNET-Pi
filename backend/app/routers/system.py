"""System control API endpoints."""
import hashlib
import hmac
import os
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from threading import Lock
from typing import Any, Optional
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from ..config import get_settings, Settings
from ..dependencies import verify_credentials, get_db
from ..models.schemas import (
    ApplyUpdateRequest,
    ServiceStatus,
    SystemInfo,
    TimeConfigResponse,
    TimeConfigUpdate,
)
from ..version_metadata import (
    normalized_git_hash,
    normalized_service_version,
    read_version_metadata,
)

router = APIRouter()

# BirdNET-Pi services
SERVICES = [
    'birdnet_analysis',
    'birdnet_recording',
    'birdnet_stats',
    'chart_viewer',
    'spectrogram_viewer',
    'livestream',
    'icecast2',
    'birdnet_log',
    'web_terminal',
]

# Services that must be running for healthy detection operation.
CORE_SERVICES = [
    'birdnet_analysis',
    'birdnet_recording',
]

UPDATE_STATUS_CACHE_TTL_SECONDS = 15 * 60
UPDATE_REMOTE = 'origin'
LIVE_STREAM_TOKEN_TTL_SECONDS = 10 * 60
LIVE_STREAM_TOKEN_FALLBACK_SECRET = os.urandom(32)
_update_status_cache_expires_at = 0.0
_update_status_checked_at: Optional[str] = None
_update_status_lock = Lock()
SEMVER_TAG_RE = re.compile(
    r'^[vV]?(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$'
)


def format_uptime() -> Optional[str]:
    """Read and format uptime from /proc/uptime."""
    try:
        with open('/proc/uptime') as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{days}d {hours}h {minutes}m"
    except Exception:
        return None


def read_version(settings: Settings) -> str:
    """Read concise app version from versions.md metadata."""
    metadata = read_version_metadata(settings.base_path)
    return normalized_service_version(metadata)


def read_update_state_file(path: str) -> dict[str, str]:
    """Read a simple line-based status file."""
    values: dict[str, str] = {}
    if not os.path.exists(path):
        return values

    try:
        with open(path, 'r', encoding='utf-8') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith('#') or ': ' not in line:
                    continue
                key, value = line.split(': ', 1)
                values[key.strip()] = value.strip()
    except Exception:
        return {}

    return values


def update_state_dir(settings: Settings) -> str:
    """Path used by the updater script for status and logs."""
    return os.path.join(settings.base_path, '.update-state')


def update_status_file(settings: Settings) -> str:
    return os.path.join(update_state_dir(settings), 'status')


def update_log_file(settings: Settings) -> str:
    return os.path.join(update_state_dir(settings), 'apply-update.log')


def run_command(command: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a command and capture text output."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_git(settings: Settings, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run git in the repository."""
    return run_command(['git', '-C', settings.base_path, *args], timeout=timeout)


def git_output(settings: Settings, args: list[str], timeout: int = 10) -> Optional[str]:
    """Return stripped stdout for a git command, or None on failure."""
    try:
        result = run_git(settings, args, timeout=timeout)
    except Exception:
        return None

    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def normalize_tag_version(tag: Optional[str]) -> Optional[str]:
    """Normalize a git tag to its semantic version string."""
    if not tag:
        return None

    match = SEMVER_TAG_RE.match(tag)
    if match:
        return match.group('version')
    return None


def list_version_tags(settings: Settings) -> list[str]:
    """List tags sorted by semantic version descending."""
    output = git_output(settings, ['tag', '--list', '--sort=-version:refname'])
    if not output:
        return []
    return [tag for tag in output.splitlines() if SEMVER_TAG_RE.match(tag)]


def latest_stable_tag(settings: Settings) -> Optional[str]:
    """Return the newest stable tag."""
    for tag in list_version_tags(settings):
        normalized = normalize_tag_version(tag)
        if normalized and '-' not in normalized:
            return tag
    return None


def latest_prerelease_tag(settings: Settings) -> Optional[str]:
    """Return the newest prerelease-or-stable tag."""
    tags = list_version_tags(settings)
    return tags[0] if tags else None


def resolve_edge_branch(settings: Settings, current_branch: Optional[str], metadata_branch: str) -> str:
    """Choose the branch to track for edge updates."""
    if current_branch and current_branch != 'HEAD':
        return current_branch

    if metadata_branch and metadata_branch not in {'unknown', 'HEAD'} and not metadata_branch.startswith('tag:'):
        return metadata_branch

    upstream = git_output(
        settings,
        ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
    )
    if upstream and '/' in upstream:
        return upstream.split('/', 1)[1]

    return 'main'


def bool_from_string(value: str) -> bool:
    """Parse common boolean-ish strings."""
    return value.lower() in {'1', 'true', 'yes', 'on'}


def pid_is_running(pid: Optional[int]) -> bool:
    """Check whether a pid exists."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True


def read_apply_state(settings: Settings) -> Optional[dict[str, Any]]:
    """Read the current updater state file, if present."""
    raw = read_update_state_file(update_status_file(settings))
    if not raw:
        return None

    pid = None
    try:
        pid = int(raw.get('pid', ''))
    except (TypeError, ValueError):
        pid = None

    return {
        'status': raw.get('status', 'unknown'),
        'stage': raw.get('stage', 'unknown'),
        'channel': raw.get('channel', settings.update_channel),
        'target': raw.get('target') or None,
        'target_type': raw.get('target_type') or None,
        'message': raw.get('message', ''),
        'started_at': raw.get('started_at') or None,
        'updated_at': raw.get('updated_at') or None,
        'pid': pid,
        'previous_ref': raw.get('previous_ref') or None,
        'current_ref': raw.get('current_ref') or None,
        'backup_created': bool_from_string(raw.get('backup_created', 'false')),
        'backup_path': raw.get('backup_path') or None,
        'error': raw.get('error') or None,
        'running': raw.get('status') == 'running' and pid_is_running(pid),
    }


def get_service_status(service_name: str) -> ServiceStatus:
    """Get the status of a systemd service."""
    try:
        # Check if active
        active_result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
        )
        is_active = active_result.returncode == 0

        # Check if enabled
        enabled_result = subprocess.run(
            ['systemctl', 'is-enabled', service_name],
            capture_output=True,
            text=True,
        )
        is_enabled = enabled_result.returncode == 0

        # Get status text
        status = active_result.stdout.strip()

        return ServiceStatus(
            name=service_name,
            active=is_active,
            enabled=is_enabled,
            status=status,
        )
    except Exception as e:
        return ServiceStatus(
            name=service_name,
            active=False,
            enabled=False,
            status=f"error: {str(e)}",
        )


def refresh_remote_update_refs(settings: Settings) -> None:
    """Refresh the remote git refs used by update checks."""
    current_branch = git_output(settings, ['branch', '--show-current']) or ''
    metadata_branch = read_version_metadata(settings.base_path).get('git_branch', 'unknown')
    edge_branch = resolve_edge_branch(settings, current_branch, metadata_branch)

    fetch_all = run_git(settings, ['fetch', '--tags', '--prune', UPDATE_REMOTE], timeout=30)
    if fetch_all.returncode != 0:
        raise RuntimeError(fetch_all.stderr.strip() or 'git fetch failed')

    fetch_branch = run_git(
        settings,
        ['fetch', '--prune', UPDATE_REMOTE, f'{edge_branch}:refs/remotes/{UPDATE_REMOTE}/{edge_branch}'],
        timeout=30,
    )
    if fetch_branch.returncode != 0:
        raise RuntimeError(fetch_branch.stderr.strip() or f'git fetch for {edge_branch} failed')


def build_update_status(settings: Settings) -> dict[str, Any]:
    """Build software update status from local git refs and version metadata."""
    metadata = read_version_metadata(settings.base_path)
    current_commit = git_output(settings, ['rev-parse', '--short', 'HEAD']) or normalized_git_hash(metadata)
    current_branch = git_output(settings, ['branch', '--show-current']) or metadata.get('git_branch', 'unknown')
    current_tag = git_output(settings, ['describe', '--tags', '--exact-match'])

    installed_service_version = metadata.get('service_version', 'unknown')
    installed_release_version = normalize_tag_version(current_tag) or normalized_service_version(metadata)
    stable_tag = latest_stable_tag(settings)
    prerelease_tag = latest_prerelease_tag(settings)
    edge_branch = resolve_edge_branch(settings, current_branch, metadata.get('git_branch', 'unknown'))
    remote_commit = git_output(settings, ['rev-parse', '--short', f'{UPDATE_REMOTE}/{edge_branch}'])
    commits_behind_output = git_output(settings, ['rev-list', '--count', f'HEAD..{UPDATE_REMOTE}/{edge_branch}'])
    commits_behind = int(commits_behind_output) if commits_behind_output and commits_behind_output.isdigit() else 0

    stable_version = normalize_tag_version(stable_tag)
    prerelease_version = normalize_tag_version(prerelease_tag)
    stable_update_available = bool(stable_version and stable_version != installed_release_version)
    prerelease_update_available = bool(prerelease_version and prerelease_version != installed_release_version)
    edge_update_available = bool(remote_commit and current_commit != remote_commit)

    available: dict[str, Any] = {
        'stable': {
            'channel': 'stable',
            'tag': stable_tag,
            'installed_version': installed_service_version,
            'update_available': stable_update_available,
        },
        'prerelease': {
            'channel': 'prerelease',
            'tag': prerelease_tag,
            'installed_version': installed_service_version,
            'update_available': prerelease_update_available,
        },
        'edge': {
            'branch': edge_branch,
            'remote': UPDATE_REMOTE,
            'current_commit': current_commit,
            'remote_commit': remote_commit,
            'commits_behind': commits_behind,
            'update_available': edge_update_available,
        },
    }

    if settings.update_channel == 'stable':
        recommended_target = stable_tag
        recommended_type = 'tag'
        recommended_available = stable_update_available
        summary = (
            f'New stable release {stable_tag} available.'
            if stable_update_available and stable_tag
            else 'Installed version matches the latest stable release.'
        )
    elif settings.update_channel == 'prerelease':
        recommended_target = prerelease_tag
        recommended_type = 'tag'
        recommended_available = prerelease_update_available
        summary = (
            f'New prerelease {prerelease_tag} available.'
            if prerelease_update_available and prerelease_tag
            else 'Installed version matches the latest prerelease target.'
        )
    else:
        recommended_target = edge_branch
        recommended_type = 'branch'
        recommended_available = edge_update_available
        summary = (
            f'Branch {edge_branch} is {commits_behind} commit(s) ahead of this install.'
            if edge_update_available
            else f'Installed code matches {UPDATE_REMOTE}/{edge_branch}.'
        )

    return {
        'installed': {
            'service_version': installed_service_version,
            'git_hash': metadata.get('git_hash', 'unknown'),
            'git_branch': metadata.get('git_branch', 'unknown'),
            'current_commit': current_commit,
            'current_branch': current_branch,
            'current_tag': current_tag,
        },
        'update_channel': settings.update_channel,
        'available': available,
        'recommended': {
            'channel': settings.update_channel,
            'target': recommended_target,
            'target_type': recommended_type,
            'update_available': recommended_available,
            'summary': summary,
        },
        'current_commit': current_commit,
        'commits_behind': commits_behind,
        'update_available': recommended_available,
    }


def get_cached_update_status(settings: Settings, force_refresh: bool = False) -> dict:
    """Return update status while caching the expensive remote fetch step."""
    global _update_status_cache_expires_at
    global _update_status_checked_at

    cached = False

    now = time.time()
    if force_refresh or now >= _update_status_cache_expires_at:
        with _update_status_lock:
            now = time.time()
            if force_refresh or now >= _update_status_cache_expires_at:
                refresh_remote_update_refs(settings)
                _update_status_checked_at = datetime.now().isoformat(timespec="seconds")
                _update_status_cache_expires_at = now + UPDATE_STATUS_CACHE_TTL_SECONDS
            else:
                cached = True
    else:
        cached = True

    status = build_update_status(settings)
    status.update({
        'apply_state': read_apply_state(settings),
        'checked_at': _update_status_checked_at or datetime.now().isoformat(timespec="seconds"),
        'cache_ttl_seconds': UPDATE_STATUS_CACHE_TTL_SECONDS,
        'cached': cached,
    })
    return status


def invalidate_update_status_cache() -> None:
    """Force the next update-status request to refresh remote refs."""
    global _update_status_cache_expires_at
    global _update_status_checked_at
    _update_status_cache_expires_at = 0.0
    _update_status_checked_at = None


def sign_live_stream_token(settings: Settings, expires: int) -> str:
    """Sign a short-lived dashboard live-stream token."""
    payload = f"live-stream:{expires}".encode('utf-8')
    secret = settings.caddy_password.encode('utf-8') or LIVE_STREAM_TOKEN_FALLBACK_SECRET
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def validate_live_stream_token(settings: Settings, expires: int, signature: str) -> bool:
    """Validate the short-lived dashboard live-stream token."""
    if expires < int(time.time()) or not signature:
        return False

    expected = sign_live_stream_token(settings, expires)
    return hmac.compare_digest(expected, signature)


def read_timedatectl_property(name: str, fallback: str = '') -> str:
    """Read a single timedatectl property value."""
    try:
        result = subprocess.run(
            ['timedatectl', 'show', '--property', name, '--value'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return fallback


def parse_boolish(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    return default


def build_time_config_response() -> TimeConfigResponse:
    """Read the current system time configuration."""
    now = datetime.now()
    timezone = read_timedatectl_property('Timezone', 'UTC') or 'UTC'
    ntp_enabled = parse_boolish(read_timedatectl_property('NTP', 'yes'), True)

    return TimeConfigResponse(
        timezone=timezone,
        ntp_enabled=ntp_enabled,
        current_date=now.strftime('%Y-%m-%d'),
        current_time=now.strftime('%H:%M'),
        available_timezones=sorted(available_timezones()),
    )


def set_timezone(timezone: str) -> None:
    """Set the system timezone and keep /etc/timezone synchronized when present."""
    subprocess.run(['sudo', 'timedatectl', 'set-timezone', timezone], check=True, timeout=30)

    if os.path.exists('/etc/timezone'):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tmp:
            tmp.write(f'{timezone}\n')
            tmp_path = tmp.name
        try:
            subprocess.run(['sudo', 'cp', tmp_path, '/etc/timezone'], check=True, timeout=30)
        finally:
            os.unlink(tmp_path)


@router.get("/system/public-status")
async def get_public_status(
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Public status summary with no sensitive system details."""
    last_row = db.execute(
        "SELECT Date, Time FROM detections ORDER BY Date DESC, Time DESC LIMIT 1"
    ).fetchone()

    last_detection = None
    if last_row:
        last_detection = f"{last_row[0]} {last_row[1]}"

    core_service_statuses = [get_service_status(name) for name in CORE_SERVICES]
    inactive_core_services = [service.name for service in core_service_statuses if not service.active]
    status = "online" if len(inactive_core_services) == 0 else "degraded"

    return {
        "status": status,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "uptime": format_uptime(),
        "last_detection": last_detection,
        "version": read_version(settings),
        "service_summary": {
            "core_total": len(CORE_SERVICES),
            "core_active": len(CORE_SERVICES) - len(inactive_core_services),
            "inactive_core_services": inactive_core_services,
        },
    }


@router.post("/system/live-stream-url")
async def create_live_stream_url(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Create a short-lived dashboard live-stream URL."""
    expires = int(time.time()) + LIVE_STREAM_TOKEN_TTL_SECONDS
    signature = sign_live_stream_token(settings, expires)
    return {
        "url": f"/api/system/live-stream?expires={expires}&signature={signature}",
        "expires_at": datetime.fromtimestamp(expires).isoformat(timespec="seconds"),
        "ttl_seconds": LIVE_STREAM_TOKEN_TTL_SECONDS,
    }


@router.get("/system/live-stream")
async def stream_live_audio(
    expires: int = Query(..., ge=0),
    signature: str = Query(..., min_length=1),
    settings: Settings = Depends(get_settings),
):
    """Proxy the local Icecast stream behind a short-lived signed URL."""
    if not validate_live_stream_token(settings, expires, signature):
        raise HTTPException(status_code=401, detail="Invalid or expired live stream token")

    try:
        upstream = urllib.request.urlopen('http://127.0.0.1:8000/stream', timeout=10)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Live audio unavailable: {exc}")

    media_type = upstream.headers.get_content_type() or 'audio/mpeg'

    def iter_stream():
        try:
            while True:
                chunk = upstream.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    return StreamingResponse(iter_stream(), media_type=media_type)


@router.get("/system/services")
async def list_services(
    user: str = Depends(verify_credentials),
):
    """Get status of all BirdNET-Pi services.

    Requires authentication.
    """
    services = [get_service_status(name) for name in SERVICES]
    return {"services": services}


@router.get("/system/services/{service_name}")
async def get_service(
    service_name: str,
    user: str = Depends(verify_credentials),
):
    """Get status of a specific service.

    Requires authentication.
    """
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")

    return get_service_status(service_name)


@router.post("/system/services/{service_name}/{action}")
async def control_service(
    service_name: str,
    action: str,
    user: str = Depends(verify_credentials),
):
    """Control a systemd service.

    Requires authentication.

    Args:
        service_name: Name of the service
        action: One of start, stop, restart, enable, disable
    """
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")

    valid_actions = ['start', 'stop', 'restart', 'enable', 'disable']
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {action}. Must be one of {valid_actions}"
        )

    try:
        result = subprocess.run(
            ['sudo', 'systemctl', action, service_name],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return {
                "message": f"Service {service_name} {action} successful",
                "service": get_service_status(service_name),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {action} {service_name}: {result.stderr}",
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Operation timed out")


@router.post("/system/restart-services")
async def restart_all_services(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Restart all BirdNET-Pi services.

    Requires authentication.
    """
    script_path = os.path.join(settings.base_path, 'scripts', 'restart_services.sh')

    try:
        result = subprocess.run(
            ['sudo', script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "message": "Services restart initiated",
            "output": result.stdout,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/reboot")
async def reboot_system(
    user: str = Depends(verify_credentials),
):
    """Reboot the system.

    Requires authentication.
    """
    try:
        subprocess.Popen(['sudo', 'reboot'])
        return {"message": "System reboot initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/shutdown")
async def shutdown_system(
    user: str = Depends(verify_credentials),
):
    """Shutdown the system.

    Requires authentication.
    """
    try:
        subprocess.Popen(['sudo', 'shutdown', 'now'])
        return {"message": "System shutdown initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/backup")
async def download_backup(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Download a backup of BirdNET-Pi data.

    Requires authentication.
    """
    from datetime import datetime

    script_path = os.path.join(settings.base_path, 'scripts', 'backup_data.sh')

    # Create backup
    try:
        result = subprocess.run(
            ['sudo', '-u', os.environ.get('USER', 'pi'), script_path, '-a', 'backup', '-f', '-'],
            capture_output=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Backup failed: {result.stderr.decode()}")

        # Return the backup data as a streaming response
        filename = f"birdnet-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.tar.gz"

        return StreamingResponse(
            iter([result.stdout]),
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
            },
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Backup timed out")


@router.post("/system/restore")
async def restore_backup(
    file: UploadFile = File(...),
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Restore BirdNET-Pi data from a backup.

    Requires authentication.
    """
    import tempfile

    script_path = os.path.join(settings.base_path, 'scripts', 'backup_data.sh')

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Run restore
        result = subprocess.run(
            ['sudo', '-u', os.environ.get('USER', 'pi'), script_path, '-a', 'restore', '-f', tmp_path],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            return {"message": "Restore completed successfully", "output": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=f"Restore failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Restore timed out")
    finally:
        os.unlink(tmp_path)


@router.get("/system/info")
async def get_system_info(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Get system information.

    Requires authentication.
    """
    version = read_version(settings)

    # Get disk usage
    disk_usage = None
    try:
        result = subprocess.run(
            ['df', '-h', settings.recs_dir],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    disk_usage = {
                        "total": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "percent": parts[4],
                    }
    except Exception:
        pass

    uptime = format_uptime()

    # Get service statuses
    services = [get_service_status(name) for name in SERVICES]

    return SystemInfo(
        version=version,
        uptime=uptime,
        disk_usage=disk_usage,
        services=services,
    )


@router.get("/system/time-config", response_model=TimeConfigResponse)
async def get_time_config(
    user: str = Depends(verify_credentials),
):
    """Get system timezone, current date/time, and NTP state."""
    return build_time_config_response()


@router.put("/system/time-config", response_model=TimeConfigResponse)
async def update_time_config(
    request: TimeConfigUpdate,
    user: str = Depends(verify_credentials),
):
    """Update system timezone and automatic/manual time settings."""
    if (request.date is None) ^ (request.time is None):
        raise HTTPException(status_code=400, detail="Manual time updates require both date and time")

    if request.timezone is not None:
        if request.timezone not in available_timezones():
            raise HTTPException(status_code=400, detail=f"Unknown timezone: {request.timezone}")
        try:
            set_timezone(request.timezone)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to set timezone: {exc}")

    if request.ntp_enabled is not None:
        try:
            subprocess.run(
                ['sudo', 'timedatectl', 'set-ntp', 'true' if request.ntp_enabled else 'false'],
                check=True,
                timeout=30,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to update NTP setting: {exc}")

    if request.date and request.time:
        try:
            datetime.strptime(f'{request.date} {request.time}', '%Y-%m-%d %H:%M')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date/time value")

        try:
            subprocess.run(['sudo', 'timedatectl', 'set-ntp', 'false'], check=True, timeout=30)
            subprocess.run(['sudo', 'date', '-s', f'{request.date} {request.time}'], check=True, timeout=30)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to set manual date/time: {exc}")

    return build_time_config_response()


@router.get("/system/logs/{service_name}")
async def get_service_logs(
    service_name: str,
    lines: int = 100,
    user: str = Depends(verify_credentials),
):
    """Get recent logs for a service.

    Requires authentication.
    """
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")

    try:
        result = subprocess.run(
            ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {
            "service": service_name,
            "lines": lines,
            "logs": result.stdout,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Log retrieval timed out")


@router.post("/system/clear-data")
async def clear_all_data(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Clear all detection data.

    Requires authentication. WARNING: This is destructive!
    """
    script_path = os.path.join(settings.base_path, 'scripts', 'clear_all_data.sh')

    try:
        result = subprocess.run(
            ['sudo', script_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return {"message": "All data cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to clear data: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Operation timed out")


@router.get("/system/update-status")
async def get_update_status(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
    force_refresh: bool = False,
):
    """Check if updates are available."""
    try:
        return get_cached_update_status(settings, force_refresh=force_refresh)
    except Exception as e:
        try:
            partial_status = build_update_status(settings)
        except Exception:
            metadata = read_version_metadata(settings.base_path)
            partial_status = {
                'installed': {
                    'service_version': metadata.get('service_version', 'unknown'),
                    'git_hash': metadata.get('git_hash', 'unknown'),
                    'git_branch': metadata.get('git_branch', 'unknown'),
                    'current_commit': normalized_git_hash(metadata),
                    'current_branch': metadata.get('git_branch', 'unknown'),
                    'current_tag': None,
                },
                'update_channel': settings.update_channel,
                'available': {
                    'stable': {
                        'channel': 'stable',
                        'tag': None,
                        'installed_version': metadata.get('service_version', 'unknown'),
                        'update_available': False,
                    },
                    'prerelease': {
                        'channel': 'prerelease',
                        'tag': None,
                        'installed_version': metadata.get('service_version', 'unknown'),
                        'update_available': False,
                    },
                    'edge': {
                        'branch': 'main',
                        'remote': UPDATE_REMOTE,
                        'current_commit': normalized_git_hash(metadata),
                        'remote_commit': None,
                        'commits_behind': 0,
                        'update_available': False,
                    },
                },
                'recommended': {
                    'channel': settings.update_channel,
                    'target': None,
                    'target_type': 'none',
                    'update_available': False,
                    'summary': 'Software update status is temporarily unavailable.',
                },
                'current_commit': normalized_git_hash(metadata),
                'commits_behind': 0,
                'update_available': False,
            }
        partial_status.update({
            'apply_state': read_apply_state(settings),
            'checked_at': _update_status_checked_at or datetime.now().isoformat(timespec="seconds"),
            'cache_ttl_seconds': UPDATE_STATUS_CACHE_TTL_SECONDS,
            'cached': False,
            'error': str(e),
        })
        return partial_status


@router.get("/system/update-log")
async def get_update_log(
    lines: int = 200,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Return recent updater log output."""
    lines = max(10, min(lines, 500))
    log_path = update_log_file(settings)
    if not os.path.exists(log_path):
        return {'lines': lines, 'log': ''}

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as handle:
            content_lines = handle.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read updater log: {e}")

    return {
        'lines': lines,
        'log': ''.join(content_lines[-lines:]),
    }


@router.post("/system/apply-update")
async def apply_update(
    request: ApplyUpdateRequest,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Launch the background update script for the selected channel."""
    current_state = read_apply_state(settings)
    if current_state and current_state.get('running'):
        raise HTTPException(status_code=409, detail="An update is already running.")

    script_path = os.path.join(settings.base_path, 'scripts', 'apply_update.sh')
    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail="Update script is missing.")

    channel = request.channel or settings.update_channel
    command = ['bash', script_path, '--channel', channel]
    if request.target:
        command.extend(['--target', request.target])
    if request.branch:
        command.extend(['--branch', request.branch])
    if not request.create_backup:
        command.append('--skip-backup')

    try:
        subprocess.Popen(
            command,
            cwd=settings.base_path,
            start_new_session=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start updater: {e}")

    invalidate_update_status_cache()
    return {
        'message': 'Software update started',
        'channel': channel,
        'target': request.target,
        'create_backup': request.create_backup,
    }
