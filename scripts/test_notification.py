import argparse
import base64

from utils.helpers import Detection, ParseFileName
from utils.reporting import apprise


if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Not to be used outside of the BirdNET-Pi application. Used to send a test message through the Apprise notification system.'
    )

    parser.add_argument('--confidence', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--filename', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--body', required=False)

    args = parser.parse_args()
    # print(args);

    # create fake detection
    detections = []
    detection = Detection("1.0", "3.0", args.name, args.confidence)
    detection.file_name_extr = args.filename
    detections.append(detection)

    # create fake file
    file = ParseFileName(args.date)

    # send test notification
    title = base64.b64decode(args.title).decode("utf-8")
    body = base64.b64decode(args.body).decode("utf-8")
    apprise(file, detections, title=title, body=body)
