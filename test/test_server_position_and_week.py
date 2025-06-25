import unittest
from unittest.mock import patch, MagicMock
import datetime
from server import PositionAndWeek

# Run these tests from the `scripts` folder: $ python3 -m unittest discover ../test

class TestPositionAndWeek(unittest.TestCase):
    def test_calling_first_time(self):
        paw = PositionAndWeek()
        self.assertTrue(paw.isPositionOrWeekChanged(1, 2))

    def test_calling_two_times_same_position(self):
        paw = PositionAndWeek()
        self.assertTrue(paw.isPositionOrWeekChanged(1, 2))
        self.assertFalse(paw.isPositionOrWeekChanged(1, 2))

    def test_calling_two_times_updated_position(self):
        paw = PositionAndWeek()
        self.assertTrue(paw.isPositionOrWeekChanged(1, 2))
        self.assertTrue(paw.isPositionOrWeekChanged(0, 2))

    @patch('server.datetime')
    def test_week_change(self, mock_datetime_module):
        mock_datetime = MagicMock()

        initial_date = datetime.datetime(2025, 6, 1)
        changed_date = datetime.datetime(2025, 3, 1)

        # First call return initial_date, second call return changed_date
        mock_datetime.now.side_effect = [
            MagicMock(isocalendar=lambda: initial_date.isocalendar()),
            MagicMock(isocalendar=lambda: changed_date.isocalendar())
        ]
        mock_datetime_module.datetime = mock_datetime

        paw = PositionAndWeek()
        dummy = paw.isPositionOrWeekChanged(1, 2) # First call is always true
        changed = paw.isPositionOrWeekChanged(1, 2)

        self.assertTrue(changed)


    @patch('server.datetime')
    def test_different_year_same_week(self, mock_datetime_module):
        mock_datetime = MagicMock()

        initial_date = datetime.datetime(2020, 1, 1)
        changed_date = datetime.datetime(2025, 1, 1)

        # First call return initial_date, second call return changed_date
        mock_datetime.now.side_effect = [
            MagicMock(isocalendar=lambda: initial_date.isocalendar()),
            MagicMock(isocalendar=lambda: changed_date.isocalendar())
        ]
        mock_datetime_module.datetime = mock_datetime

        paw = PositionAndWeek()
        dummy = paw.isPositionOrWeekChanged(1, 2) # First call is always true
        changed = paw.isPositionOrWeekChanged(1, 2)

        self.assertFalse(changed)
        
if __name__ == '__main__':
    unittest.main()