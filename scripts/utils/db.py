import sqlite3
import time as timeim
from datetime import datetime

from .helpers import DB_PATH

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


def get_species_by(sort_by=None, date=None):
    where = "" if date is None else  f'WHERE Date == "{date}"'
    if sort_by == "occurrences":
        select_sql = f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence FROM detections {where} GROUP BY Sci_Name ORDER BY COUNT(*) DESC"
    elif sort_by == "confidence":
        select_sql = f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence FROM detections {where} GROUP BY Sci_Name ORDER BY MAX(Confidence) DESC"
    elif sort_by == "date":
        select_sql = f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence FROM detections {where} GROUP BY Sci_Name ORDER BY MIN(Date) DESC, Time DESC"
    else:
        select_sql = f"SELECT Date, Time, File_Name, Com_Name, Sci_Name, COUNT(*) as Count, MAX(Confidence) as MaxConfidence FROM detections {where} GROUP BY Sci_Name ORDER BY Com_Name ASC"
    records = get_records(select_sql)
    return records


def get_records(select_sql):
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.execute(select_sql)
        records = cur.fetchall()
        con.close()
    except sqlite3.Error:
        print("Database busy")
        timeim.sleep(2)
        records = []
    return records
