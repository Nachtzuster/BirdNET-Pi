"""Publish past detections to BirdWeather."""

import datetime
import logging
import os
import sqlite3
from typing import Optional
import warnings

import librosa
import pandas as pd
from tzlocal import get_localzone
from utils.helpers import DB_PATH, get_settings, setup_logging, Detection
from utils.birdweather import get_birdweather_species_id, query_birdweather_detections, \
    post_soundscape_to_birdweather, post_detection_to_birdweather

log = logging.getLogger(os.path.splitext(os.path.basename(os.path.realpath(__file__)))[0])


def get_last_run_time(script_name: str) -> Optional[datetime.datetime]:
    """Fetch the last run time for the given script from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT last_run FROM scripts_metadata WHERE script_name = ?", (script_name,)
    )
    result = cursor.fetchone()

    conn.close()

    if result:
        return datetime.datetime.fromisoformat(result[0])
    return None


def update_last_run_time(script_name: str):
    """Update the last run time for the given script to the current time in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_time = datetime.datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO scripts_metadata (script_name, last_run) VALUES (?, ?)
        ON CONFLICT(script_name) DO UPDATE SET last_run = excluded.last_run;
        """,
        (script_name, current_time),
    )

    conn.commit()
    conn.close()


def get_detections_since(start_datetime: datetime.datetime) -> pd.DataFrame:
    """Get detections from the database that occurred after the specified date."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        f"SELECT * from detections WHERE Date > DATE('{start_datetime.strftime('%Y-%m-%d')}')",
        conn,
    )
    conn.close()
    return df


def main():

    conf = get_settings()
    if conf["BIRDWEATHER_ID"] == "":
        return

    # Get detections since last run (defaults to 7 days if last run time is not found)
    last_run_time = get_last_run_time(script_name=os.path.basename(os.path.realpath(__file__)))
    if last_run_time is None:
        last_run_time = datetime.datetime.now() - datetime.timedelta(days=7)
    df = get_detections_since(last_run_time)

    # Loop through recent detections
    log.info(
        f"Checking if recent detections are present in BirdWeather since {last_run_time}"
    )
    for detection_entry in df.itertuples():

        detection_datetime = datetime.datetime.strptime(
            f"{detection_entry.Date} {detection_entry.Time}", "%Y-%m-%d %H:%M:%S"
        ).astimezone(get_localzone())

        try:
            # Lookup detections present in BirdWeather at the time of this detection
            species_id = get_birdweather_species_id(
                detection_entry.Sci_Name, detection_entry.Com_Name
            )
            birdweather_detections = query_birdweather_detections(
                conf["BIRDWEATHER_ID"],
                species_id,
                detection_datetime,
            )
        except Exception as e:
            log.error(
                f"Script {os.path.basename(os.path.realpath(__file__))} stopped due to error: {e}"
            )
            return

        # This detection is not present in BirdWeather
        if birdweather_detections == []:

            log.info(f"Detection not in BirdWeather: {detection_entry.File_Name}")

            # Post extracted audio to BirdWeather as soundscape
            extracted_audio_file = os.path.join(
                conf["EXTRACTED"],
                "By_Date",
                detection_datetime.strftime("%Y-%m-%d"),
                detection_entry.Com_Name.replace(" ", "_").replace("'", ""),
                detection_entry.File_Name,
            )
            soundscape_id = post_soundscape_to_birdweather(
                conf["BIRDWEATHER_ID"],
                detection_datetime,
                extracted_audio_file,
            )

            # Get length of extracted audio file, will be useful to post detection to BirdWeather
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=FutureWarning)
                soundscape_duration = librosa.get_duration(path=extracted_audio_file)

            # Create an instance of Detection and post it to BirdWeather
            # This Detection start and end times are equal to soundscape start and end times,
            # because we're using an "extracted" audio file as soundscape
            detection = Detection(
                detection_datetime,
                detection_datetime + datetime.timedelta(seconds=soundscape_duration),
                f"{detection_entry.Sci_Name}_{detection_entry.Com_Name}",
                detection_entry.Confidence,
            )
            post_detection_to_birdweather(
                detection,
                soundscape_id,
                detection_datetime,
                conf["BIRDWEATHER_ID"],
                conf['LATITUDE'],
                conf['LONGITUDE'],
                conf['MODEL'],
            )

    update_last_run_time(script_name=os.path.basename(os.path.realpath(__file__)))


if __name__ == "__main__":

    setup_logging()

    main()
