"""This module gets location from gpsd daemon and updates configuration if needed."""
import logging
import sys

from apscheduler.schedulers.background import BlockingScheduler
import gpsdclient
from utils.helpers import get_settings, _load_settings, write_settings

log = logging.getLogger(__name__)

def main():
    """Starting the location updates at given interval."""
    conf = get_settings()

    if(conf.getint('LOCATION_AUTOUPDATE') == 1):
        log.info("Starting location autoupdate service")
        scheduler = BlockingScheduler()
        scheduler.add_job(location_update,'interval',seconds=conf.getint('LOCATION_AUTOUPDATE_INTERVAL'))
        scheduler.start()
    else:
        log.info("Location autoupdate service is not enabled in birdnet.conf. Not starting.")

def location_update():
    """Gets location from gpsd and updates configuration if needed."""
    _load_settings('/etc/birdnet/birdnet.conf',True)
    conf = get_settings()
    currentlatitude = conf.getfloat('LATITUDE')
    currentlongitude = conf.getfloat('LONGITUDE')

    threshold=conf.getfloat('LOCATION_AUTOUPDATE_THRESHOLD')
    with gpsdclient.GPSDClient(host="127.0.0.1") as client:
        for result in client.dict_stream(convert_datetime=True, filter=["TPV"]):
            lat = result.get("lat", "n/a")
            lon = result.get("lon", "n/a")
            if(lat != "n/a" and lon != "n/a"):
                break
    
    newlatitude=round(lat,4)
    newlongitude=round(lon,4)

    latdiff = abs(currentlatitude - newlatitude)
    londiff = abs(currentlongitude - newlongitude)

    if((latdiff > threshold) or (londiff > threshold)):
        log.info("New location detected: %s, %s",newlatitude,newlongitude)
        lat2replace = "LATITUDE="+str(currentlatitude)
        lon2replace = "LONGITUDE="+str(currentlongitude)
        lat2replacewith = "LATITUDE="+str(newlatitude)
        lon2replacewith = "LONGITUDE="+str(newlongitude)

        try:
            with open('/etc/birdnet/birdnet.conf', 'r') as configfile:
                configuration = configfile.read()
                configuration = configuration.replace(lat2replace,lat2replacewith)
                configuration = configuration.replace(lon2replace,lon2replacewith)
                configfile.close()
        except Exception as e:
            log.error("Error occured while trying to read configuration: ", e)

        try:
            with open('/etc/birdnet/birdnet.conf', 'w') as configfile:
                configfile.write(configuration)
                configfile.flush()
                configfile.close()
        except Exception as e:
            log.error("Error occured while trying to write configuration: ", e)
        
        _load_settings('/etc/birdnet/birdnet.conf',True)
        write_settings()


def setup_logging():
    """Do logging in a nice and polite way."""
    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    global log
    log = logging.getLogger('location_autoupdater')


if __name__ == '__main__':
    setup_logging()
    main()
