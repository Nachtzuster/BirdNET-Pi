"""System control API endpoints."""
import os
import sqlite3
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from ..config import get_settings, Settings
from ..dependencies import verify_credentials, get_db
from ..models.schemas import ServiceStatus, SystemInfo
from ..version_metadata import read_version_metadata, normalized_service_version

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
    settings: Settings = Depends(get_settings),
):
    """Check if updates are available."""
    try:
        # Fetch latest
        subprocess.run(
            ['git', '-C', settings.base_path, 'fetch'],
            capture_output=True,
            timeout=30,
        )

        # Check commits behind
        result = subprocess.run(
            ['git', '-C', settings.base_path, 'rev-list', '--count', 'HEAD..origin/main'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        commits_behind = int(result.stdout.strip()) if result.returncode == 0 else 0

        # Get current commit
        current = subprocess.run(
            ['git', '-C', settings.base_path, 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        current_commit = current.stdout.strip() if current.returncode == 0 else "unknown"

        return {
            "commits_behind": commits_behind,
            "update_available": commits_behind > 0,
            "current_commit": current_commit,
        }
    except Exception as e:
        return {
            "commits_behind": 0,
            "update_available": False,
            "current_commit": "unknown",
            "error": str(e),
        }
