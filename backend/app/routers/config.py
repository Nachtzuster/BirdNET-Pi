"""Configuration API endpoints."""
import os
import re

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings, Settings
from ..dependencies import verify_credentials
from ..models.schemas import ConfigUpdate, ConfigResponse, TestNotificationRequest, NotificationResponse

router = APIRouter()


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
    config_path = '/etc/birdnet/birdnet.conf'

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
        import subprocess
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

    return {
        "message": "Configuration updated",
        "updated_fields": list(updates.keys()),
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
    model_dir = settings.model_path

    models = []
    for filename in os.listdir(model_dir):
        if filename.endswith('.tflite'):
            model_name = filename.replace('.tflite', '')
            models.append({
                "name": model_name,
                "active": model_name == settings.model,
            })

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
    threshold: float = 0.03,
    settings: Settings = Depends(get_settings),
):
    """Preview species list for a given threshold.

    Uses the species.py script to generate the list.
    """
    import subprocess

    script_path = os.path.join(settings.base_path, 'scripts', 'species.py')
    python_path = os.path.join(settings.base_path, 'birdnet', 'bin', 'python3')

    try:
        result = subprocess.run(
            [python_path, script_path, '--threshold', str(threshold)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            # Parse output - each line is a species
            species = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return {
                "threshold": threshold,
                "count": len(species),
                "species": species,
            }
        else:
            raise HTTPException(status_code=500, detail=f"Script error: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Species list generation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
