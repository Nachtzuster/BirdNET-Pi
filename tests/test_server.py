import os
import unittest
from unittest.mock import patch

from scripts.server import run_analysis
from scripts.utils.classes import ParseFileName
from tests.helpers import TESTDATA, Settings


class TestRunAnalysis(unittest.TestCase):

    @patch('scripts.utils.helpers._load_settings')
    @patch('scripts.server.loadCustomSpeciesList')
    def test_run_analysis(self, mock_loadCustomSpeciesList, mock_load_settings):
        # Mock the settings and species list
        mock_load_settings.return_value = Settings.with_defaults()
        mock_loadCustomSpeciesList.return_value = []

        # Test file
        test_file = ParseFileName(os.path.join(TESTDATA, '2024-02-24-birdnet-16:19:37.wav'))

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


if __name__ == '__main__':
    unittest.main()
