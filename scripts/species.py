import argparse
import datetime
import os

from utils.helpers import get_settings, MODEL_PATH
from utils.models import MDataModel1, MDataModel2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get list of species for a given location with BirdNET. Sorted by occurrence frequency.'
    )
    parser.add_argument('--threshold', type=float, default=0.05,
                        help='Occurrence frequency threshold. Defaults to 0.05.')
    args = parser.parse_args()

    conf = get_settings()
    lat = conf.getfloat('LATITUDE')
    lon = conf.getfloat('LONGITUDE')
    week = datetime.datetime.today().isocalendar()[1]

    print(f'Getting species list for {lat}/{lon}, Week {week}...', flush=True)
    labels_path = os.path.join(MODEL_PATH, 'labels.txt')
    with open(labels_path, 'r') as lfile:
        labels = [line.strip() for line in lfile]

    model = MDataModel1(args.threshold) if conf.getint('DATA_MODEL_VERSION') == 1 else MDataModel2(args.threshold)
    model.set_meta_data(lat, lon, week)
    species_list = model.get_species_list_details(labels)

    for species in species_list:
        print(f'{species[1]} - {species[0]:.4f}')

    print("""
The above species list describes all the species that the model will attempt to detect.
If you don't see a species you want detected on this list, decrease your threshold.

NOTE: no actual changes to your BirdNET-Pi species list were made by running this command.
To set your desired frequency threshold, do it through the BirdNET-Pi web interface (Tools -> Settings -> Model)
""")
