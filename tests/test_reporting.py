import unittest
from unittest.mock import patch

from scripts.utils import reporting


class TestSpectrogramFonts(unittest.TestCase):

    @patch('scripts.utils.reporting.get_font')
    def test_load_spectrogram_font_falls_back_when_font_missing(self, mock_get_font):
        mock_get_font.return_value = {'path': '/missing/RobotoFlex-Regular.ttf'}

        font = reporting._load_spectrogram_font(13)

        self.assertTrue(callable(getattr(font, 'getbbox', None)))


if __name__ == '__main__':
    unittest.main()
