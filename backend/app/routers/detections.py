"""Detection API endpoints."""
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ..config import get_settings, Settings
from ..dependencies import get_db, verify_credentials, extract_species_from_filename
from ..models.schemas import Detection, DetectionList, DetectionSummary

router = APIRouter()


def percentage_change(current: int, previous: int) -> float | None:
    """Return percentage change, or None when prior baseline is zero."""
    if previous == 0:
        return None if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def completed_week_range(anchor: date | None = None) -> tuple[date, date]:
    """Return the most recently completed Sunday-Saturday reporting window."""
    base = anchor or datetime.now().date()
    days_since_sunday = (base.weekday() + 1) % 7
    last_sunday = base - timedelta(days=days_since_sunday)
    start = last_sunday - timedelta(days=7)
    end = last_sunday - timedelta(days=1)
    return start, end


def build_weekly_report_payload(
    db: sqlite3.Connection,
    end_date: Optional[str] = None,
) -> dict:
    """Build the weekly report payload used by the API and notifications."""
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date must be YYYY-MM-DD format")
        start = end - timedelta(days=6)
    else:
        start, end = completed_week_range()

    prev_start = start - timedelta(days=7)
    prev_end = end - timedelta(days=7)

    current_species_rows = db.execute(
        """
        SELECT Sci_Name, Com_Name, COUNT(*) as count
        FROM detections
        WHERE Date BETWEEN ? AND ?
        GROUP BY Sci_Name
        ORDER BY count DESC, Com_Name ASC
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    prior_species_rows = db.execute(
        """
        SELECT Sci_Name, COUNT(*) as count
        FROM detections
        WHERE Date BETWEEN ? AND ?
        GROUP BY Sci_Name
        """,
        (prev_start.isoformat(), prev_end.isoformat()),
    ).fetchall()
    prior_species_counts = {row["Sci_Name"]: row["count"] for row in prior_species_rows}

    first_seen_rows = db.execute(
        """
        SELECT d.Sci_Name, d.Com_Name, COUNT(*) as count
        FROM detections d
        WHERE d.Date BETWEEN ? AND ?
          AND NOT EXISTS (
              SELECT 1
              FROM detections prev
              WHERE prev.Sci_Name = d.Sci_Name
                AND prev.Date < ?
          )
        GROUP BY d.Sci_Name
        ORDER BY count DESC, d.Com_Name ASC
        """,
        (start.isoformat(), end.isoformat(), start.isoformat()),
    ).fetchall()

    total_detections = db.execute(
        "SELECT COUNT(*) FROM detections WHERE Date BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat()),
    ).fetchone()[0]
    previous_total_detections = db.execute(
        "SELECT COUNT(*) FROM detections WHERE Date BETWEEN ? AND ?",
        (prev_start.isoformat(), prev_end.isoformat()),
    ).fetchone()[0]

    total_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat()),
    ).fetchone()[0]
    previous_total_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date BETWEEN ? AND ?",
        (prev_start.isoformat(), prev_end.isoformat()),
    ).fetchone()[0]

    top_species = []
    for row in current_species_rows[:10]:
        prior_count = prior_species_counts.get(row["Sci_Name"], 0)
        top_species.append({
            "sci_name": row["Sci_Name"],
            "com_name": row["Com_Name"],
            "count": row["count"],
            "previous_count": prior_count,
            "change_pct": percentage_change(row["count"], prior_count),
            "is_new_this_week": prior_count == 0,
        })

    first_seen_species = [
        {
            "sci_name": row["Sci_Name"],
            "com_name": row["Com_Name"],
            "count": row["count"],
        }
        for row in first_seen_rows
    ]

    return {
        "label": f"Week {end.isocalendar().week} Report",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "week_number": end.isocalendar().week,
        "year": end.isocalendar().year,
        "total_detections": total_detections,
        "previous_total_detections": previous_total_detections,
        "total_detections_change_pct": percentage_change(total_detections, previous_total_detections),
        "species_count": total_species,
        "previous_species_count": previous_total_species,
        "species_count_change_pct": percentage_change(total_species, previous_total_species),
        "top_species": top_species,
        "first_seen_species": first_seen_species,
    }


def format_report_change_html(value: float | None) -> str:
    """Render a weekly report percentage change as inline HTML."""
    if value is None:
        return "<span style='color:green;font-size:small'>New activity</span>"
    if value > 0:
        return f"<span style='color:green;font-size:small'>+{value:g}%</span>"
    if value < 0:
        return f"<span style='color:red;font-size:small'>-{abs(value):g}%</span>"
    return "<span style='color:gray;font-size:small'>0%</span>"


def render_weekly_report_notification(report: dict, site_name: str) -> str:
    """Render the weekly report in the legacy notification text format."""
    previous_week = report["week_number"] - 1
    if previous_week < 1:
        previous_week = 52

    lines = [
        f"# {site_name}: Week {report['week_number']} Report",
        f"Total Detections: <b>{report['total_detections']}</b> ({format_report_change_html(report['total_detections_change_pct'])})<br>",
        f"Unique Species Detected: <b>{report['species_count']}</b> ({format_report_change_html(report['species_count_change_pct'])})<br><br>",
        "= <b>Top 10 Species</b> =<br>",
    ]

    if report["top_species"]:
        for species in report["top_species"]:
            lines.append(
                f"{species['com_name']} - {species['count']} "
                f"({format_report_change_html(species['change_pct'])})<br>"
            )
    else:
        lines.append("No detections were recorded during this week.<br>")

    lines.append("<br>= <b>Species Detected for the First Time</b> =<br>")
    if report["first_seen_species"]:
        for species in report["first_seen_species"]:
            lines.append(f"{species['com_name']} - {species['count']}<br>")
    else:
        lines.append("No new species were seen this week.")

    lines.append(
        f"<hr><span style='font-size:small'>* data from {report['start_date']} — {report['end_date']}.</span><br>"
    )
    lines.append(
        f"<span style='font-size:small'>* percentages are calculated relative to week {previous_week}.</span>"
    )
    return "\n".join(lines)


@router.get("/detections", response_model=DetectionList)
async def get_detections(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    date: Optional[str] = None,
    species: Optional[str] = None,
    search: Optional[str] = None,
    new_on_date: bool = False,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get paginated list of detections.

    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        date: Filter by date (YYYY-MM-DD)
        species: Filter by scientific name
        search: Search term for common or scientific name
        new_on_date: Only include species whose first-ever detection was on the selected date
    """
    if new_on_date and not date:
        raise HTTPException(status_code=400, detail="new_on_date filter requires a date")

    # Build WHERE clause
    conditions = []
    params = []

    if date:
        conditions.append("Date = ?")
        params.append(date)
    if species:
        conditions.append("Sci_Name = ?")
        params.append(species)
    if search:
        conditions.append("(Com_Name LIKE ? OR Sci_Name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if new_on_date:
        conditions.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM detections prev
                WHERE prev.Sci_Name = detections.Sci_Name
                  AND prev.Date < ?
            )
            """
        )
        params.append(date)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM detections{where_clause}"
    total = db.execute(count_sql, params).fetchone()[0]

    # Get detections
    select_sql = f"""
        SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
               Cutoff, Week, Sens, Overlap, File_Name
        FROM detections
        {where_clause}
        ORDER BY Date DESC, Time DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cursor = db.execute(select_sql, params)
    rows = cursor.fetchall()

    detections = [Detection.model_validate(dict(row)) for row in rows]

    return DetectionList(
        detections=detections,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/detections/today")
async def get_todays_detections(
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get today's detections.

    Args:
        limit: Maximum number of results
        search: Search term for species name
    """
    today = datetime.now().strftime("%Y-%m-%d")

    conditions = ["Date = ?"]
    params = [today]

    if search:
        conditions.append("(Com_Name LIKE ? OR Sci_Name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = " WHERE " + " AND ".join(conditions)

    select_sql = f"""
        SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
               Cutoff, Week, Sens, Overlap, File_Name
        FROM detections
        {where_clause}
        ORDER BY Time DESC
        LIMIT ?
    """
    params.append(limit)

    cursor = db.execute(select_sql, params)
    rows = cursor.fetchall()

    return {
        "detections": [dict(row) for row in rows],
        "date": today,
    }


@router.get("/detections/latest")
async def get_latest_detection(
    db: sqlite3.Connection = Depends(get_db),
):
    """Get the most recent detection."""
    select_sql = """
        SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
               Cutoff, Week, Sens, Overlap, File_Name
        FROM detections
        ORDER BY Date DESC, Time DESC
        LIMIT 1
    """
    cursor = db.execute(select_sql)
    row = cursor.fetchone()

    if not row:
        return None

    return dict(row)


@router.get("/detections/stats", response_model=DetectionSummary)
async def get_detection_stats(
    db: sqlite3.Connection = Depends(get_db),
):
    """Get detection statistics."""
    # Total count
    total = db.execute("SELECT COUNT(*) FROM detections").fetchone()[0]

    # Today's count
    todays = db.execute(
        "SELECT COUNT(*) FROM detections WHERE Date = DATE('now', 'localtime')"
    ).fetchone()[0]

    # Last hour count
    hour = db.execute(
        """SELECT COUNT(*) FROM detections
           WHERE Date = DATE('now', 'localtime')
           AND Time >= TIME('now', 'localtime', '-1 hour')"""
    ).fetchone()[0]

    # Today's species count
    todays_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date = DATE('now', 'localtime')"
    ).fetchone()[0]

    # New species first detected today
    new_species_today = db.execute(
        """
        SELECT COUNT(DISTINCT d.Sci_Name)
        FROM detections d
        WHERE d.Date = DATE('now', 'localtime')
          AND NOT EXISTS (
              SELECT 1
              FROM detections prev
              WHERE prev.Sci_Name = d.Sci_Name
                AND prev.Date < DATE('now', 'localtime')
          )
        """
    ).fetchone()[0]

    # Total species count
    total_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections"
    ).fetchone()[0]

    return DetectionSummary(
        total_count=total,
        todays_count=todays,
        hour_count=hour,
        new_species_today=new_species_today,
        todays_species_tally=todays_species,
        species_tally=total_species,
    )


@router.get("/detections/new-species-today", response_model=list[Detection])
async def get_new_species_today(
    db: sqlite3.Connection = Depends(get_db),
):
    """Get today's detections for species first-ever seen today (latest per species)."""
    rows = db.execute(
        """
        SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
               Cutoff, Week, Sens, Overlap, File_Name
        FROM detections d
        WHERE d.Date = DATE('now', 'localtime')
          AND NOT EXISTS (
              SELECT 1
              FROM detections prev
              WHERE prev.Sci_Name = d.Sci_Name
                AND prev.Date < DATE('now', 'localtime')
          )
        ORDER BY d.Time DESC
        """
    ).fetchall()

    latest_by_species: list[dict] = []
    seen_species: set[str] = set()
    for row in rows:
        sci_name = row["Sci_Name"]
        if sci_name in seen_species:
            continue
        seen_species.add(sci_name)
        latest_by_species.append(dict(row))

    return latest_by_species


@router.get("/detections/weekly-report")
async def get_weekly_report(
    end_date: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get summary data for the most recently completed reporting week."""
    return build_weekly_report_payload(db, end_date)


@router.get("/detections/weekly-report/notification", response_class=PlainTextResponse)
async def get_weekly_report_notification(
    end_date: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Render the weekly report using the legacy notification text contract."""
    report = build_weekly_report_payload(db, end_date)
    return render_weekly_report_notification(report, settings.site_name or "BirdNET-Pi")


@router.get("/detections/daily-report")
async def get_daily_report(
    date: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get summary data for a single reporting day."""
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD format")
    else:
        latest_row = db.execute(
            "SELECT Date FROM detections ORDER BY Date DESC LIMIT 1"
        ).fetchone()
        if not latest_row:
            raise HTTPException(status_code=404, detail="No detections available")
        report_date = datetime.strptime(latest_row[0], "%Y-%m-%d").date()

    previous_date = report_date - timedelta(days=1)

    current_species_rows = db.execute(
        """
        SELECT Sci_Name, Com_Name, COUNT(*) as count
        FROM detections
        WHERE Date = ?
        GROUP BY Sci_Name
        ORDER BY count DESC, Com_Name ASC
        """,
        (report_date.isoformat(),),
    ).fetchall()

    prior_species_rows = db.execute(
        """
        SELECT Sci_Name, COUNT(*) as count
        FROM detections
        WHERE Date = ?
        GROUP BY Sci_Name
        """,
        (previous_date.isoformat(),),
    ).fetchall()
    prior_species_counts = {row["Sci_Name"]: row["count"] for row in prior_species_rows}

    first_seen_rows = db.execute(
        """
        SELECT d.Sci_Name, d.Com_Name, COUNT(*) as count
        FROM detections d
        WHERE d.Date = ?
          AND NOT EXISTS (
              SELECT 1
              FROM detections prev
              WHERE prev.Sci_Name = d.Sci_Name
                AND prev.Date < ?
          )
        GROUP BY d.Sci_Name
        ORDER BY count DESC, d.Com_Name ASC
        """,
        (report_date.isoformat(), report_date.isoformat()),
    ).fetchall()
    first_seen_species_names = {row["Sci_Name"] for row in first_seen_rows}

    total_detections = db.execute(
        "SELECT COUNT(*) FROM detections WHERE Date = ?",
        (report_date.isoformat(),),
    ).fetchone()[0]
    previous_total_detections = db.execute(
        "SELECT COUNT(*) FROM detections WHERE Date = ?",
        (previous_date.isoformat(),),
    ).fetchone()[0]

    total_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date = ?",
        (report_date.isoformat(),),
    ).fetchone()[0]
    previous_total_species = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date = ?",
        (previous_date.isoformat(),),
    ).fetchone()[0]

    peak_hour_row = db.execute(
        """
        SELECT CAST(SUBSTR(Time, 1, 2) AS INTEGER) as hour, COUNT(*) as count
        FROM detections
        WHERE Date = ?
        GROUP BY hour
        ORDER BY count DESC, hour ASC
        LIMIT 1
        """,
        (report_date.isoformat(),),
    ).fetchone()

    top_species = []
    for row in current_species_rows[:10]:
        prior_count = prior_species_counts.get(row["Sci_Name"], 0)
        top_species.append({
            "sci_name": row["Sci_Name"],
            "com_name": row["Com_Name"],
            "count": row["count"],
            "previous_count": prior_count,
            "change_pct": percentage_change(row["count"], prior_count),
            "is_new_this_day": row["Sci_Name"] in first_seen_species_names,
        })

    first_seen_species = [
        {
            "sci_name": row["Sci_Name"],
            "com_name": row["Com_Name"],
            "count": row["count"],
        }
        for row in first_seen_rows
    ]

    return {
        "label": "Daily Report",
        "date": report_date.isoformat(),
        "previous_date": previous_date.isoformat(),
        "total_detections": total_detections,
        "previous_total_detections": previous_total_detections,
        "total_detections_change_pct": percentage_change(total_detections, previous_total_detections),
        "species_count": total_species,
        "previous_species_count": previous_total_species,
        "species_count_change_pct": percentage_change(total_species, previous_total_species),
        "peak_hour": peak_hour_row["hour"] if peak_hour_row else None,
        "top_species": top_species,
        "first_seen_species": first_seen_species,
    }


@router.get("/detections/dates")
async def get_detection_dates(
    db: sqlite3.Connection = Depends(get_db),
):
    """Get all dates that have detections."""
    cursor = db.execute(
        "SELECT DISTINCT Date FROM detections ORDER BY Date DESC"
    )
    rows = cursor.fetchall()
    return {"dates": [row[0] for row in rows]}


@router.get("/detections/chart-data/{date}")
async def get_chart_data(
    date: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get hourly detection counts and species breakdown for a date.

    Returns data suitable for rendering interactive charts.

    Args:
        date: Date to get chart data for (YYYY-MM-DD)
    """
    # Hourly detection counts
    hourly_sql = """
        SELECT CAST(SUBSTR(Time, 1, 2) AS INTEGER) as hour, COUNT(*) as count
        FROM detections
        WHERE Date = ?
        GROUP BY hour
        ORDER BY hour
    """
    hourly_rows = db.execute(hourly_sql, (date,)).fetchall()

    # Build full 24-hour array (fill gaps with 0)
    hourly_counts = {row[0]: row[1] for row in hourly_rows}
    hourly = [{"hour": h, "count": hourly_counts.get(h, 0)} for h in range(24)]

    # Top species for the day
    species_sql = """
        SELECT Com_Name, Sci_Name, COUNT(*) as count, MAX(Confidence) as max_confidence
        FROM detections
        WHERE Date = ?
        GROUP BY Sci_Name
        ORDER BY count DESC
        LIMIT 10
    """
    species_rows = db.execute(species_sql, (date,)).fetchall()
    top_species = [
        {
            "com_name": row[0],
            "sci_name": row[1],
            "count": row[2],
            "max_confidence": round(row[3], 2),
        }
        for row in species_rows
    ]

    # Per-species hourly breakdown (for all species detected that day)
    species_hourly_sql = """
        SELECT Sci_Name, Com_Name,
               CAST(SUBSTR(Time, 1, 2) AS INTEGER) as hour,
               COUNT(*) as count
        FROM detections
        WHERE Date = ?
        GROUP BY Sci_Name, hour
        ORDER BY Sci_Name, hour
    """
    species_hourly_rows = db.execute(species_hourly_sql, (date,)).fetchall()

    # Organize into { sci_name: { com_name, hourly: [24 counts] } }
    species_hourly_map: dict = {}
    for row in species_hourly_rows:
        sci_name = row[0]
        if sci_name not in species_hourly_map:
            species_hourly_map[sci_name] = {
                "sci_name": sci_name,
                "com_name": row[1],
                "hourly": [0] * 24,
            }
        species_hourly_map[sci_name]["hourly"][row[2]] = row[3]

    species_hourly = list(species_hourly_map.values())

    # Summary stats
    total = sum(h["count"] for h in hourly)
    species_count = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date = ?", (date,)
    ).fetchone()[0]

    return {
        "date": date,
        "total_detections": total,
        "species_count": species_count,
        "hourly": hourly,
        "top_species": top_species,
        "species_hourly": species_hourly,
    }


@router.get("/detections/chart-data-range")
async def get_chart_data_range(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
    group_by: str = Query("day", description="Grouping: hour, day, week, month"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Get aggregated detection data over a date range.

    Supports multiple groupings for different time-range views:
    - hour: 24-hour breakdown (best for single-day or today view)
    - day: one bucket per calendar day
    - week: one bucket per ISO week
    - month: one bucket per calendar month

    Returns:
        buckets: list of {period, count} dicts
        total_detections: total count in range
        species_count: distinct species in range
        top_species: top 10 species with counts and max confidence
        species_buckets: per-species breakdown matching the bucket grouping
    """
    if group_by not in ("hour", "day", "week", "month"):
        raise HTTPException(status_code=400, detail="group_by must be one of: hour, day, week, month")

    # Validate dates
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be YYYY-MM-DD format")

    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start must be <= end")

    # Build the GROUP BY expression based on grouping mode
    if group_by == "hour":
        period_expr = "CAST(SUBSTR(Time, 1, 2) AS INTEGER)"
        period_alias = "period"
    elif group_by == "day":
        period_expr = "Date"
        period_alias = "period"
    elif group_by == "week":
        # ISO week: YYYY-Www (SQLite strftime %W is zero-padded week number)
        period_expr = "SUBSTR(Date, 1, 4) || '-W' || strftime('%W', Date)"
        period_alias = "period"
    elif group_by == "month":
        period_expr = "SUBSTR(Date, 1, 7)"
        period_alias = "period"

    # Aggregated buckets
    bucket_sql = f"""
        SELECT {period_expr} as {period_alias}, COUNT(*) as count
        FROM detections
        WHERE Date BETWEEN ? AND ?
        GROUP BY {period_alias}
        ORDER BY {period_alias}
    """
    bucket_rows = db.execute(bucket_sql, (start, end)).fetchall()

    # For hour grouping, fill in all 24 hours
    if group_by == "hour":
        hour_map = {row[0]: row[1] for row in bucket_rows}
        buckets = [{"period": h, "count": hour_map.get(h, 0)} for h in range(24)]
    else:
        buckets = [{"period": str(row[0]), "count": row[1]} for row in bucket_rows]

    # Summary stats
    total = sum(b["count"] for b in buckets)
    species_count = db.execute(
        "SELECT COUNT(DISTINCT Sci_Name) FROM detections WHERE Date BETWEEN ? AND ?",
        (start, end),
    ).fetchone()[0]

    # Top species
    species_sql = """
        SELECT Com_Name, Sci_Name, COUNT(*) as count, MAX(Confidence) as max_confidence
        FROM detections
        WHERE Date BETWEEN ? AND ?
        GROUP BY Sci_Name
        ORDER BY count DESC
        LIMIT 10
    """
    species_rows = db.execute(species_sql, (start, end)).fetchall()
    top_species = [
        {
            "com_name": row[0],
            "sci_name": row[1],
            "count": row[2],
            "max_confidence": round(row[3], 2),
        }
        for row in species_rows
    ]

    # Per-species bucket breakdown (for stacked charts)
    species_bucket_sql = f"""
        SELECT Sci_Name, Com_Name, {period_expr} as {period_alias}, COUNT(*) as count
        FROM detections
        WHERE Date BETWEEN ? AND ?
        GROUP BY Sci_Name, {period_alias}
        ORDER BY Sci_Name, {period_alias}
    """
    species_bucket_rows = db.execute(species_bucket_sql, (start, end)).fetchall()

    species_bucket_map: dict = {}
    for row in species_bucket_rows:
        sci_name = row[0]
        if sci_name not in species_bucket_map:
            species_bucket_map[sci_name] = {
                "sci_name": sci_name,
                "com_name": row[1],
                "buckets": {},
            }
        period_key = row[2] if group_by != "hour" else row[2]
        species_bucket_map[sci_name]["buckets"][str(period_key) if group_by != "hour" else period_key] = row[3]

    # Convert to arrays matching the bucket structure
    all_periods = [b["period"] for b in buckets]
    species_buckets = []
    for entry in species_bucket_map.values():
        counts = [entry["buckets"].get(p, 0) for p in all_periods]
        species_buckets.append({
            "sci_name": entry["sci_name"],
            "com_name": entry["com_name"],
            "counts": counts,
        })

    return {
        "start": start,
        "end": end,
        "group_by": group_by,
        "total_detections": total,
        "species_count": species_count,
        "buckets": buckets,
        "top_species": top_species,
        "species_buckets": species_buckets,
    }


@router.get("/detections/by-file/{filename:path}")
async def get_detection_by_file(
    filename: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get detection by filename."""
    cursor = db.execute(
        """SELECT Date, Time, Sci_Name, Com_Name, Confidence, Lat, Lon,
                  Cutoff, Week, Sens, Overlap, File_Name
           FROM detections
           WHERE File_Name = ?
           ORDER BY Date DESC, Time DESC""",
        (filename,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Detection not found")

    return dict(row)


@router.delete("/detections/{filename:path}")
async def delete_detection(
    filename: str,
    user: str = Depends(verify_credentials),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Delete a detection and its associated files.

    Requires authentication.
    """
    import os
    import subprocess

    # Get the detection to find the file path
    cursor = db.execute(
        "SELECT Date FROM detections WHERE File_Name = ?",
        (filename,)
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Detection not found")

    detection_date = row[0]

    # Extract species folder from filename (files are stored by common name, not scientific name)
    species_folder = extract_species_from_filename(filename)

    # Build file paths
    base_path = os.path.join(settings.by_date_dir, detection_date, species_folder)
    audio_path = os.path.join(base_path, filename)
    spectrogram_path = audio_path + '.png'

    # Delete from database (using a new writable connection)
    write_db = sqlite3.connect(settings.db_path)
    try:
        write_db.execute("DELETE FROM detections WHERE File_Name = ?", (filename,))
        write_db.commit()
    finally:
        write_db.close()

    # Delete files
    deleted_files = []
    for path in [audio_path, spectrogram_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted_files.append(path)
            except PermissionError:
                # Try with sudo
                subprocess.run(['sudo', 'rm', path], check=True)
                deleted_files.append(path)

    return {
        "message": "Detection deleted",
        "filename": filename,
        "deleted_files": deleted_files,
    }
