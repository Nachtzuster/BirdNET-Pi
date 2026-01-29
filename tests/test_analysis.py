import os
import unittest
from unittest.mock import patch

from scripts.utils.analysis import filter_humans
from scripts.utils.analysis import run_analysis
from scripts.utils.classes import ParseFileName
from tests.helpers import TESTDATA, Settings


class TestRunAnalysis(unittest.TestCase):

    def setUp(self):
        source = os.path.join(TESTDATA, 'Pica pica_30s.wav')
        self.test_file = os.path.join(TESTDATA, '2024-02-24-birdnet-16:19:37.wav')
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)
        os.symlink(source, self.test_file)
        # Reset global model to force reload
        import scripts.utils.analysis
        scripts.utils.analysis.MODEL = None

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)
        # Reset global model to avoid bleeding into other tests
        import scripts.utils.analysis
        scripts.utils.analysis.MODEL = None

    @patch('scripts.utils.helpers._load_settings')
    @patch('scripts.utils.analysis.loadCustomSpeciesList')
    def test_run_analysis_birdnet(self, mock_loadCustomSpeciesList, mock_load_settings):
        # Mock the settings and species list
        mock_load_settings.return_value = Settings.with_defaults()
        mock_loadCustomSpeciesList.return_value = []

        # Test file
        test_file = ParseFileName(self.test_file)

        # Expected results
        expected_results = [
            {"confidence": 0.912, 'sci_name': 'Pica pica'},
            {"confidence": 0.9316, 'sci_name': 'Pica pica'},
            {"confidence": 0.8857, 'sci_name': 'Pica pica'}
        ]

        # Run the analysis
        detections = run_analysis(test_file)

        # Assertions
        self.assertEqual(len(detections), len(expected_results))
        for det, expected in zip(detections, expected_results):
            self.assertAlmostEqual(det.confidence, expected['confidence'], delta=1e-4)
            self.assertEqual(det.scientific_name, expected['sci_name'])

    @patch('scripts.utils.helpers._load_settings')
    @patch('scripts.utils.analysis.loadCustomSpeciesList')
    def test_run_analysis_perch(self, mock_loadCustomSpeciesList, mock_load_settings):
        settings = Settings.with_defaults()
        settings.update({
            'MODEL': 'Perch_v2',
            'PERCH_BIRDNET_FILTER': '1',
        })
        mock_load_settings.return_value = settings


        # Test file
        test_file = ParseFileName(self.test_file)

        # Expected results
        expected_results = [
            {"confidence": 0.9641, 'sci_name': 'Pica pica', 'common_name': 'Eurasian Magpie'},
            {"confidence": 0.9609, 'sci_name': 'Pica pica', 'common_name': 'Eurasian Magpie'},
            {"confidence": 0.9468, 'sci_name': 'Pica pica', 'common_name': 'Eurasian Magpie'}
        ]

        # Run the analysis
        detections = run_analysis(test_file)

        # Assertions
        self.assertEqual(len(detections), len(expected_results))
        for det, expected in zip(detections, expected_results):
            self.assertAlmostEqual(det.confidence, expected['confidence'], delta=1e-4)
            self.assertEqual(det.scientific_name, expected['sci_name'])
            self.assertEqual(det.common_name, expected['common_name'])


class TestFilterHumans(unittest.TestCase):

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_no_human(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections without humans
        detections = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_C', 0.9), ('Pacarina schumanni', 0.8)],
            [('Bird_F', 0.7), ('Bird_F', 0.6)]
        ]

        # Expected output
        expected = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_C', 0.9), ('Pacarina schumanni', 0.8)],
            [('Bird_F', 0.7), ('Bird_F', 0.6)]
        ]

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_empty(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections without humans
        detections = []

        # Expected output
        expected = []

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_with_human(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections with humans
        detections = [
            [('Human_Human', 0.95), ('Bird_A', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_C', 0.9), ('Bird_D', 0.8)],
            [('Bird_B', 0.7), ('Human vocal_Human vocal', 0.9)]
        ]

        # Expected output
        expected = [
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)]
        ]

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_with_human_neighbour(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections with human neighbours
        detections = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_D', 0.9), ('Bird_E', 0.8)],
            [('Human_Human', 0.95), ('Bird_C', 0.7)],
            [('Bird_F', 0.6), ('Bird_G', 0.5)]
        ]

        # Expected output
        expected = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)]
        ]

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_with_deep_human(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections with human neighbours
        detections = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_D', 0.9), ('Bird_E', 0.8)],
            [('Bird_C', 0.7)] * 10 + [('Human_Human', 0.95)],
            [('Bird_F', 0.6), ('Bird_G', 0.5)]
        ]

        # Expected output
        expected = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_D', 0.9), ('Bird_E', 0.8)],
            [('Bird_C', 0.7)] * 10,
            [('Bird_F', 0.6), ('Bird_G', 0.5)]
        ]

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_with_human_deep(self, mock_load_settings):
        settings = Settings.with_defaults()
        settings['PRIVACY_THRESHOLD'] = 1
        mock_load_settings.return_value = settings

        # Input detections with human neighbours
        detections = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_D', 0.9), ('Bird_E', 0.8)],
            [('Bird_C', 0.7)] * 10 + [('Human_Human', 0.95)],
            [('Bird_F', 0.6), ('Bird_G', 0.5)]
        ]

        # Expected output
        expected = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)],
            [('Human_Human', 0.0)]
        ]

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)

    @patch('scripts.utils.helpers._load_settings')
    def test_filter_humans_for_perch(self, mock_load_settings):
        mock_load_settings.return_value = Settings.with_defaults()

        # Input detections with "humans" from FSD50K
        # Child_speech_and_kid_speaking
        # Conversation
        # Female_singing
        # Female_speech_and_woman_speaking
        # Human_voice
        # Male_singing
        # Male_speech_and_man_speaking
        # Speech
        # Speech_synthesizer
        # Yell

        # Human_group_actions ??
        detections = [
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_A', 0.8), ('Child_speech_and_kid_speaking', 0.75)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Conversation', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Female_singing', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Female_speech_and_woman_speaking', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Human_group_actions', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Human_voice', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Male_singing', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Male_speech_and_man_speaking', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Speech', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Speech_synthesizer', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
            [('Bird_B', 0.9), ('Yell', 0.8)],
            [('Bird_A', 0.9), ('Bird_B', 0.8)],
        ]

        # Expected output
        expected = [
                       [('Human_Human', 0.0)]
                   ] * 23

        # Run filter_humans
        result = filter_humans(detections)

        # Assertions
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
