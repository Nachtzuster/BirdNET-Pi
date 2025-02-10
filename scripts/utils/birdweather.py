"""Module to handle communication with the BirdWeather API."""

import requests
import logging
import datetime

import gzip
from typing import Any, Dict, List, Optional
from .helpers import Detection

log = logging.getLogger(__name__)


def get_birdweather_species_id(sci_name: str, com_name: str) -> int:
    """Lookup a BirdWeather species ID based on the species scientific and common names."""
    species_url = "https://app.birdweather.com/api/v1/species/lookup"
    try:
        resp = requests.post(
            url=species_url,
            json={"species": [f"{sci_name}_{com_name}"]},
            timeout=20,
        )
        data = resp.json()
        if not data["success"] or len(data["species"]) != 1:
            raise
        species = next(iter(data["species"].values()))
        return species["id"]
    except Exception as e:
        log.error(f"Couldn't find BirdWeather species ID for {sci_name}_{com_name}: {e}")
        raise


def query_birdweather_detections(
    birdweather_id: str,
    species_id: int,
    detection_datetime: datetime.datetime,
) -> List[Dict[str, Any]]:
    """Query detections from the BirdWeather API for specific station, species and time."""
    detections_url = (
        f"https://app.birdweather.com/api/v1/stations/{birdweather_id}/detections"
    )
    try:
        resp = requests.get(
            url=detections_url,
            data={
                "speciesId": species_id,
                "from": detection_datetime.isoformat(),
                "to": detection_datetime.isoformat(),
            },
            timeout=20,
        )
        data = resp.json()
        if not data["success"]:
            raise
        return data["detections"]
    except Exception as e:
        log.error(f"Could not lookup detections from BirdWeather: {e}")
        raise


def post_soundscape_to_birdweather(
    birdweather_id: str, detection_datetime: datetime.datetime, soundscape_file: str
) -> Optional[int]:
    """Upload a soundscape file to BirdWeather."""
    soundscape_url = (
        f"https://app.birdweather.com/api/v1/stations/{birdweather_id}/"
        f"soundscapes?timestamp={detection_datetime.isoformat()}"
    )
    with open(soundscape_file, "rb") as f:
        mp3_data = f.read()
    gzip_mp3_data = gzip.compress(mp3_data)
    try:
        resp = requests.post(
            url=soundscape_url,
            data=gzip_mp3_data,
            timeout=20,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Encoding": "gzip",
            },
        )
        data = resp.json()
        if not data.get("success"):
            log.error(data.get("message"))
            raise
        return data["soundscape"]["id"]
    except Exception as e:
        log.error(f"Cannot POST soundscape: {e}")
        return


def post_detection_to_birdweather(
    detection: Detection,
    soundscape_id: str,
    soundscape_datetime: datetime.datetime,
    birdweather_id: str,
    latitude: float,
    longitude: float,
    model: str
):
    """Upload a detection to BirdWeather."""

    detection_url = f'https://app.birdweather.com/api/v1/stations/{birdweather_id}/detections'

    data = {
        'timestamp': detection.iso8601,
        'lat': latitude,
        'lon': longitude,
        'soundscapeId': soundscape_id,
        'soundscapeStartTime': (detection.start_datetime - soundscape_datetime).seconds,
        'soundscapeEndTime': (detection.stop_datetime - soundscape_datetime).seconds,
        'commonName': detection.common_name,
        'scientificName': detection.scientific_name,
        'algorithm': '2p4' if model == 'BirdNET_GLOBAL_6K_V2.4_Model_FP16' else 'alpha',
        'confidence': detection.confidence
    }

    log.debug(data)
    try:
        response = requests.post(detection_url, json=data, timeout=20)
        log.info("Detection POST Response Status - %d", response.status_code)
    except Exception as e:
        log.error("Cannot POST detection: %s", e)
