import sqlite3
import time as timeim
from datetime import datetime

from .helpers import DB_PATH

_DB = None


def get_db():
    global _DB
    if _DB is None:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        _DB = con
    return _DB


def get_records(select_sql):
    con = get_db()
    try:
        cur = con.execute(select_sql)
        records = cur.fetchall()
    except sqlite3.Error as e:
        print(e)
        timeim.sleep(2)
        records = []
    return records


def get_record(select_sql):
    records = get_records(select_sql)
    return dict(records[0]) if records else None


def get_latest():
    select_sql = "SELECT * FROM detections ORDER BY Date DESC, Time DESC LIMIT 1"
    return get_record(select_sql)


def get_todays_count_for(sci_name):
    today = datetime.now().strftime("%Y-%m-%d")
    select_sql = f"SELECT COUNT(*) FROM detections WHERE Date = DATE('{today}') AND Sci_Name = '{sci_name}'"
    records = get_records(select_sql)
    return records[0][0] if records else 0


def get_this_weeks_count_for(sci_name):
    today = datetime.now().strftime("%Y-%m-%d")
    select_sql = f"SELECT COUNT(*) FROM detections WHERE Date >= DATE('{today}', '-7 day') AND Sci_Name = '{sci_name}'"
    records = get_records(select_sql)
    return records[0][0] if records else 0


def get_summary():
    total_count = get_record("SELECT COUNT(*) as total_count FROM detections")
    todays_count = get_record("SELECT COUNT(*) as todays_count FROM detections WHERE Date == DATE('now', 'localtime')")
    hour_count = get_record("SELECT COUNT(*) as hour_count FROM detections "
                            "WHERE Date == Date('now', 'localtime') AND TIME >= TIME('now', 'localtime', '-1 hour')")
    todays_species_tally = get_record("SELECT COUNT(DISTINCT(Sci_Name)) as todays_species_tally FROM detections WHERE Date == Date('now','localtime')")
    species_tally = get_record("SELECT COUNT(DISTINCT(Sci_Name)) as species_tally FROM detections")

    summary = {**total_count, **todays_count, **hour_count, **todays_species_tally, **species_tally}
    return summary


def get_species_by(sort_by=None, date=None):
    where = "" if date is None else f'WHERE Date == "{date}"'
    if sort_by == "occurrences":
        select_sql = (f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence "
                      f"FROM detections {where} GROUP BY Sci_Name ORDER BY COUNT(*) DESC;")
    elif sort_by == "confidence":
        select_sql = (f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence "
                      f"FROM detections {where} GROUP BY Sci_Name ORDER BY MAX(Confidence) DESC;")
    elif sort_by == "date":
        select_sql = (f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence "
                      f"FROM detections {where} GROUP BY Sci_Name ORDER BY MIN(Date) DESC, Time DESC;")
    else:
        select_sql = (f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence "
                      f"FROM detections {where} GROUP BY Sci_Name ORDER BY Com_Name ASC;")
    records = get_records(select_sql)
    return records
