import argparse
import datetime

from utils.helpers import get_settings, get_model_labels, model_supports_species_filter
from utils.models import MDataModel1, MDataModel2

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get list of species for a given location with BirdNET. Sorted by occurrence frequency.'
    )
    parser.add_argument('--threshold', type=float, default=0.05,
                        help='Occurrence frequency threshold. Defaults to 0.05.')
    parser.add_argument('--model', type=str, default=None,
                        help='Classifier model to preview species range against. Defaults to configured MODEL.')
    parser.add_argument('--data-model-version', type=int, choices=[1, 2], default=None,
                        help='Species range model version. Defaults to configured DATA_MODEL_VERSION.')
    parser.add_argument('--plain', action='store_true',
                        help='Output only species lines with no header/footer text.')
    args = parser.parse_args()

    conf = get_settings()
    lat = conf.getfloat('LATITUDE')
    lon = conf.getfloat('LONGITUDE')
    week = datetime.datetime.today().isocalendar()[1]
    model_name = args.model or conf['MODEL']
    data_model_version = args.data_model_version if args.data_model_version is not None else conf.getint('DATA_MODEL_VERSION')

    if not model_supports_species_filter(model_name):
        raise SystemExit(f'Model {model_name} does not support species range preview')

    if not args.plain:
        print(f'Getting species list for {lat}/{lon}, Week {week}...', flush=True)
    labels = get_model_labels(model_name)

    model = MDataModel1(args.threshold) if data_model_version == 1 else MDataModel2(args.threshold)
    model.set_meta_data(lat, lon, week)
    species_list = model.get_species_list_details(labels)

    for species in species_list:
        print(f'{species[1]} - {species[0]:.4f}')

    if not args.plain:
        print("""
The above species list describes all the species that the model will attempt to detect.
If you don't see a species you want detected on this list, decrease your threshold.

NOTE: no actual changes to your BirdNET-Pi species list were made by running this command.
To set your desired frequency threshold, do it through the BirdNET-Pi web interface (Tools -> Settings -> Model)
""")
