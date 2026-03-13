"""Configuration API endpoints."""
import os
import re
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import get_settings, Settings
from ..dependencies import verify_credentials
from ..models.schemas import ConfigUpdate, ConfigResponse, TestNotificationRequest, NotificationResponse
from utils.helpers import list_installed_selectable_models, model_supports_species_filter

router = APIRouter()


def configured_birdnet_user(settings: Settings) -> str:
    return settings.config.get('BIRDNET_USER') or os.environ.get('USER', 'pi')


def run_managed_script(args: list[str], timeout: int, failure_detail: str) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail=f"{failure_detail}: operation timed out")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{failure_detail}: {exc}")

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise HTTPException(status_code=500, detail=f"{failure_detail}: {detail}")

    return result


def sync_language_labels(settings: Settings) -> None:
    script_path = os.path.join(settings.base_path, 'scripts', 'install_language_label.sh')
    run_managed_script(
        ['sudo', '-u', configured_birdnet_user(settings), script_path],
        timeout=30,
        failure_detail="Failed to update model labels",
    )


def restart_services(settings: Settings) -> None:
    script_path = os.path.join(settings.base_path, 'scripts', 'restart_services.sh')
    run_managed_script(
        ['sudo', script_path],
        timeout=60,
        failure_detail="Failed to restart services",
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Get current configuration.

    Requires authentication. Returns a safe subset of settings.
    """
    return ConfigResponse(
        site_name=settings.site_name,
        latitude=settings.latitude,
        longitude=settings.longitude,
        database_lang=settings.database_lang,
        color_scheme=settings.color_scheme,
        update_channel=settings.update_channel,
        model=settings.model,
        sf_thresh=settings.sf_thresh,
        data_model_version=settings.data_model_version,
        confidence=settings.confidence,
        sensitivity=settings.sensitivity,
        overlap=settings.overlap,
        birdweather_id=settings.birdweather_id,
        image_provider=settings.image_provider,
        has_flickr_key=bool(settings.flickr_api_key),
    )


@router.put("/config")
async def update_config(
    config_update: ConfigUpdate,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Update configuration.

    Requires authentication. Only updates fields that are provided.
    """
    config_path = settings.config_path
    previous_model = settings.model
    previous_language = settings.database_lang
    installed_models = list_installed_selectable_models()

    if config_update.model is not None and config_update.model not in installed_models:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unsupported model: {config_update.model}",
                "available_models": installed_models,
            },
        )

    # Read current config file
    try:
        with open(config_path, 'r') as f:
            contents = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Configuration file not found")
    except PermissionError:
        raise HTTPException(status_code=500, detail="Cannot read configuration file")

    # Map of field names to config keys
    field_map = {
        'site_name': 'SITE_NAME',
        'latitude': 'LATITUDE',
        'longitude': 'LONGITUDE',
        'database_lang': 'DATABASE_LANG',
        'color_scheme': 'COLOR_SCHEME',
        'update_channel': 'UPDATE_CHANNEL',
        'model': 'MODEL',
        'sf_thresh': 'SF_THRESH',
        'data_model_version': 'DATA_MODEL_VERSION',
        'confidence': 'CONFIDENCE',
        'sensitivity': 'SENSITIVITY',
        'overlap': 'OVERLAP',
        'birdweather_id': 'BIRDWEATHER_ID',
        'flickr_api_key': 'FLICKR_API_KEY',
        'image_provider': 'IMAGE_PROVIDER',
    }

    # Update config values
    updates = config_update.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in field_map and value is not None:
            key = field_map[field]
            # Handle string values that need quotes
            if isinstance(value, str):
                new_value = f'{key}="{value}"'
            else:
                new_value = f'{key}={value}'

            # Replace or add the setting
            pattern = rf'^{key}=.*$'
            if re.search(pattern, contents, re.MULTILINE):
                contents = re.sub(pattern, new_value, contents, flags=re.MULTILINE)
            else:
                contents += f'\n{new_value}'

    # Write updated config
    try:
        with open(config_path, 'w') as f:
            f.write(contents)
    except PermissionError:
        # Try with sudo
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            subprocess.run(['sudo', 'cp', tmp_path, config_path], check=True)
        finally:
            os.unlink(tmp_path)

    # Reload settings
    settings.reload()
    applied_actions = []

    if settings.model != previous_model or settings.database_lang != previous_language:
        sync_language_labels(settings)
        applied_actions.append('labels_updated')

    restart_services(settings)
    applied_actions.append('services_restarted')

    return {
        "message": "Configuration updated and services restarted",
        "updated_fields": list(updates.keys()),
        "applied_actions": applied_actions,
    }


@router.post("/config/test-notification", response_model=NotificationResponse)
async def test_notification(
    request: TestNotificationRequest,
    user: str = Depends(verify_credentials),
    settings: Settings = Depends(get_settings),
):
    """Send a test notification.

    Requires authentication.
    """
    import subprocess

    # Use the existing send_test_notification.py script
    script_path = os.path.join(settings.base_path, 'scripts', 'send_test_notification.py')
    python_path = os.path.join(settings.base_path, 'birdnet', 'bin', 'python3')

    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail="Notification script not found")

    # Build command
    cmd = [python_path, script_path]

    if request.title:
        cmd.extend(['--title', request.title])
    if request.body:
        cmd.extend(['--body', request.body])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return NotificationResponse(
                success=True,
                message="Test notification sent successfully",
            )
        else:
            return NotificationResponse(
                success=False,
                message=f"Notification failed: {result.stderr or result.stdout}",
            )
    except subprocess.TimeoutExpired:
        return NotificationResponse(
            success=False,
            message="Notification timed out",
        )
    except Exception as e:
        return NotificationResponse(
            success=False,
            message=f"Error sending notification: {str(e)}",
        )


@router.get("/config/models")
async def list_available_models(
    settings: Settings = Depends(get_settings),
):
    """List available BirdNET models."""
    models = [
        {
            "name": model_name,
            "active": model_name == settings.model,
            "supports_species_filter": model_supports_species_filter(model_name),
        }
        for model_name in list_installed_selectable_models()
    ]

    return {"models": models, "current": settings.model}


@router.get("/config/languages")
async def list_available_languages(
    settings: Settings = Depends(get_settings),
):
    """List available display languages."""
    l18n_dir = os.path.join(settings.model_path, 'l18n')

    languages = []
    for filename in os.listdir(l18n_dir):
        if filename.startswith('labels_') and filename.endswith('.json'):
            lang_code = filename.replace('labels_', '').replace('.json', '')
            languages.append({
                "code": lang_code,
                "active": lang_code == settings.database_lang,
            })

    languages.sort(key=lambda x: x['code'])

    return {"languages": languages, "current": settings.database_lang}


@router.get("/config/preview-species")
async def preview_species_list(
    threshold: float = Query(0.03, ge=0.0005, le=0.99),
    model: str | None = None,
    data_model_version: int | None = Query(None, ge=1, le=2),
    settings: Settings = Depends(get_settings),
):
    """Preview species list for a given threshold.

    Uses the species.py script to generate the list.
    """
    script_path = os.path.join(settings.base_path, 'scripts', 'species.py')
    python_path = os.path.join(settings.base_path, 'birdnet', 'bin', 'python3')
    model_name = model or settings.model
    model_version = data_model_version or settings.data_model_version

    if not model_supports_species_filter(model_name):
        raise HTTPException(status_code=400, detail=f"Model {model_name} does not support species range preview")

    cmd = [
        python_path,
        script_path,
        '--threshold',
        str(threshold),
        '--model',
        model_name,
        '--data-model-version',
        str(model_version),
        '--plain',
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            # Parse output - each line is a species
            species = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return {
                "threshold": threshold,
                "model": model_name,
                "data_model_version": model_version,
                "count": len(species),
                "species": species,
            }
        else:
            raise HTTPException(status_code=500, detail=f"Script error: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Species list generation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
