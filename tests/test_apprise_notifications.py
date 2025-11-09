import os
import sqlite3
from datetime import datetime
import unittest
from unittest.mock import patch

from scripts.utils import notifications
from scripts.utils.notifications import sendAppriseNotifications


class TestAppriseNotifications(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_file = "test.db"
        cls.apprise_body_file = "test_apprise_body"
        cls.apprise_config_file = "test_apprise_config"

    def create_test_db(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            sql_create_detections_table = """ CREATE TABLE IF NOT EXISTS detections (
                                            id integer PRIMARY KEY,
                                            Sci_Name text NOT NULL,
                                            Com_Name text NOT NULL,
                                            Date date NOT NULL,
                                            Time time NULL
                                        ); """
            cur = conn.cursor()
            cur.execute(sql_create_detections_table)
            sql = ''' INSERT INTO detections(Sci_Name, Com_Name, Date)
                  VALUES(?,?,?) '''

            today = datetime.now().strftime("%Y-%m-%d")  # SQLite stores date as YYYY-MM-DD
            cur.execute(sql, ["Myiarchus crinitus", "Great Crested Flycatcher", today])
            conn.commit()

        except Exception as e:
            print(e)
        finally:
            if conn:
                conn.close()

    def create_apprise_config(self):
        with open(self.apprise_body_file, 'w') as f:
            f.write('A $comname ($sciname) was just detected with a confidence of $confidencepct ($reason)')
        with open(self.apprise_config_file, 'w') as f:
            f.write('a dummy config')
        notifications.APPRISE_BODY = self.apprise_body_file
        notifications.APPRISE_CONFIG = self.apprise_config_file

    def tearDown(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        if os.path.exists(self.apprise_body_file):
            os.remove(self.apprise_body_file)
        if os.path.exists(self.apprise_config_file):
            os.remove(self.apprise_config_file)

    @patch('scripts.utils.notifications.notify')
    def test_notifications(self, mock_notify):
        self.create_test_db()
        self.create_apprise_config()
        settings_dict = {
            "APPRISE_NOTIFICATION_TITLE": "New backyard bird!",
            "APPRISE_NOTIFY_EACH_DETECTION": "0",
            "APPRISE_NOTIFY_NEW_SPECIES": "0",
            "APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY": "0",
            "APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES": "0"
        }
        sendAppriseNotifications("Myiarchus crinitus_Great Crested Flycatcher",
                                 "0.91",
                                 "91",
                                 "filename",
                                 "1666-06-06",
                                 "06:06:06",
                                 "06",
                                 "-1",
                                 "-1",
                                 "0.7",
                                 "1.25",
                                 "0.0",
                                 settings_dict,
                                 self.db_file)

        # No active apprise notifications configured. Confirm no notifications.
        self.assertEqual(mock_notify.call_count, 0)

        # Add daily notification.
        mock_notify.reset_mock()
        settings_dict["APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY"] = "1"
        sendAppriseNotifications("Myiarchus crinitus_Great Crested Flycatcher",
                                 "0.91",
                                 "91",
                                 "filename",
                                 "1666-06-06",
                                 "06:06:06",
                                 "06",
                                 "-1",
                                 "-1",
                                 "0.7",
                                 "1.25",
                                 "0.0",
                                 settings_dict,
                                 self.db_file)

        self.assertEqual(mock_notify.call_count, 1)
        self.assertEqual(
            mock_notify.call_args_list[0][0][0],
            "A Great Crested Flycatcher (Myiarchus crinitus) was just detected with a confidence of 91 (first time today)"
        )

        # Add new species notification.
        mock_notify.reset_mock()
        settings_dict["APPRISE_NOTIFY_NEW_SPECIES"] = "1"
        sendAppriseNotifications("Myiarchus crinitus_Great Crested Flycatcher",
                                 "0.91",
                                 "91",
                                 "filename",
                                 "1666-06-06",
                                 "06:06:06",
                                 "06",
                                 "-1",
                                 "-1",
                                 "0.7",
                                 "1.25",
                                 "0.0",
                                 settings_dict,
                                 self.db_file)

        self.assertEqual(mock_notify.call_count, 2)
        self.assertEqual(
            mock_notify.call_args_list[0][0][0],
            "A Great Crested Flycatcher (Myiarchus crinitus) was just detected with a confidence of 91 (first time today)"
        )
        self.assertEqual(
            mock_notify.call_args_list[1][0][0],
            "A Great Crested Flycatcher (Myiarchus crinitus) was just detected with a confidence of 91 (only seen 1 times in last 7d)"
        )

        # Add each species notification.
        mock_notify.reset_mock()
        settings_dict["APPRISE_NOTIFY_EACH_DETECTION"] = "1"
        sendAppriseNotifications("Myiarchus crinitus_Great Crested Flycatcher",
                                 "0.91",
                                 "91",
                                 "filename",
                                 "1666-06-06",
                                 "06:06:06",
                                 "06",
                                 "-1",
                                 "-1",
                                 "0.7",
                                 "1.25",
                                 "0.0",
                                 settings_dict,
                                 self.db_file)

        self.assertEqual(mock_notify.call_count, 3)


if __name__ == '__main__':
    unittest.main()
