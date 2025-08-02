from scripts.utils.parse_settings import config_to_settings
import tempfile


def test():
    text = """LATITUDE=32.0
LONGITUDE=-73.0
BIRDWEATHER_ID=
CADDY_PWD="nonsuchpass"
ICE_PWD=birdnetpi
BIRDNETPI_URL=
RTSP_STREAM=
APPRISE_NOTIFICATION_TITLE="Bird!"
APPRISE_NOTIFICATION_BODY="A $comname ($sciname) was just detected with a confidence of $confidence"
APPRISE_NOTIFY_EACH_DETECTION=0
APPRISE_NOTIFY_NEW_SPECIES=1
FLICKR_API_KEY=
FLICKR_FILTER_EMAIL=
IMAGE_PROVIDER=WIKIPEDIA
RECS_DIR=/home/pi/BirdSongs
REC_CARD=default
PROCESSED=/home/pi/BirdSongs/Processed
EXTRACTED=/home/pi/BirdSongs/Extracted
OVERLAP=0.0
CONFIDENCE=0.7
SENSITIVITY=1.25
CHANNELS=2
FULL_DISK=purge
PRIVACY_THRESHOLD=0
RECORDING_LENGTH=15
EXTRACTION_LENGTH=
AUDIOFMT=mp3
DATABASE_LANG=en
LAST_RUN=
THIS_RUN=
IDFILE=/home/pi/BirdNET-Pi/IdentifiedSoFar.txt"""

    filename = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    with open(filename.name, 'w', encoding='utf8', newline='') as f:
        f.write(text)

    settings = config_to_settings(filename.name)
    assert (settings["APPRISE_NOTIFICATION_TITLE"] == "Bird!")
    assert (settings["FULL_DISK"] == "purge")
    assert (settings["OVERLAP"] == "0.0")  # Yes, it's a string at this point.
    assert (settings["IMAGE_PROVIDER"] == "WIKIPEDIA")
