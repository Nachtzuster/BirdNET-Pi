"""Pydantic models for BirdNET-Pi API."""
from datetime import date as DateType, time as TimeType
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# Detection schemas
class Detection(BaseModel):
    """A single bird detection."""
    date: DateType = Field(..., alias="Date")
    time: TimeType = Field(..., alias="Time")
    sci_name: str = Field(..., alias="Sci_Name")
    com_name: str = Field(..., alias="Com_Name")
    confidence: float = Field(..., alias="Confidence")
    latitude: Optional[float] = Field(None, alias="Lat")
    longitude: Optional[float] = Field(None, alias="Lon")
    cutoff: Optional[float] = Field(None, alias="Cutoff")
    week: Optional[int] = Field(None, alias="Week")
    sensitivity: Optional[float] = Field(None, alias="Sens")
    overlap: Optional[float] = Field(None, alias="Overlap")
    file_name: str = Field(..., alias="File_Name")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,  # Serialize using aliases (Date, Time, etc.)
    )


class DetectionSummary(BaseModel):
    """Summary statistics for detections."""
    total_count: int
    todays_count: int
    hour_count: int
    new_species_today: int
    todays_species_tally: int
    species_tally: int


class SpeciesSummary(BaseModel):
    """Summary of a species with detection count."""
    date: DateType = Field(..., alias="Date")
    time: TimeType = Field(..., alias="Time")
    file_name: str = Field(..., alias="File_Name")
    com_name: str = Field(..., alias="Com_Name")
    sci_name: str = Field(..., alias="Sci_Name")
    count: int = Field(..., alias="Count")
    max_confidence: float = Field(..., alias="MaxConfidence")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,  # Serialize using aliases (Date, Time, etc.)
    )


class DetectionList(BaseModel):
    """Paginated list of detections."""
    detections: list[Detection]
    total: int
    limit: int
    offset: int


class SpeciesList(BaseModel):
    """List of species with summaries."""
    species: list[SpeciesSummary]
    total: int


# Configuration schemas
class ConfigBase(BaseModel):
    """Base configuration model with common settings."""
    site_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    database_lang: Optional[str] = None
    color_scheme: Optional[str] = None
    update_channel: Optional[str] = Field(None, pattern="^(stable|prerelease|edge)$")
    info_site: Optional[str] = Field(None, pattern="^(ALLABOUTBIRDS|EBIRD)$")


class ConfigUpdate(ConfigBase):
    """Configuration update request."""
    model: Optional[str] = None
    sf_thresh: Optional[float] = Field(None, ge=0.0005, le=0.99)
    data_model_version: Optional[int] = Field(None, ge=1, le=2)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    sensitivity: Optional[float] = Field(None, ge=0.5, le=1.5)
    overlap: Optional[float] = Field(None, ge=0.0, le=2.9)
    birdweather_id: Optional[str] = None
    flickr_api_key: Optional[str] = None
    image_provider: Optional[str] = None
    caddy_password: Optional[str] = Field(None, min_length=1)
    birdnetpi_url: Optional[str] = None
    rtsp_stream: Optional[str] = None
    rtsp_stream_to_livestream: Optional[int] = Field(None, ge=0)
    activate_freqshift_in_livestream: Optional[bool] = None
    apprise_config: Optional[str] = None
    apprise_notification_title: Optional[str] = None
    apprise_notification_body: Optional[str] = None
    apprise_notify_each_detection: Optional[bool] = None
    apprise_notify_new_species: Optional[bool] = None
    apprise_notify_new_species_each_day: Optional[bool] = None
    apprise_weekly_report: Optional[bool] = None
    apprise_minimum_seconds_between_notifications_per_species: Optional[int] = Field(None, ge=0)
    apprise_only_notify_species_names: Optional[str] = None
    apprise_only_notify_species_names_2: Optional[str] = None
    privacy_threshold: Optional[int] = Field(None, ge=0, le=3)
    full_disk: Optional[str] = Field(None, pattern="^(purge|keep)$")
    purge_threshold: Optional[int] = Field(None, ge=20, le=99)
    max_files_species: Optional[int] = Field(None, ge=0)
    rec_card: Optional[str] = None
    channels: Optional[int] = Field(None, ge=1, le=32)
    recording_length: Optional[int] = Field(None, ge=3, le=60)
    extraction_length: Optional[int] = Field(None, ge=3, le=60)
    audiofmt: Optional[str] = None
    silence_update_indicator: Optional[bool] = None
    automatic_update: Optional[bool] = None
    raw_spectrogram: Optional[bool] = None
    rare_species_threshold: Optional[int] = Field(None, ge=1)
    custom_image: Optional[str] = None
    custom_image_title: Optional[str] = None
    freqshift_tool: Optional[str] = Field(None, pattern="^(sox|ffmpeg)$")
    freqshift_hi: Optional[int] = Field(None, ge=0, le=20000)
    freqshift_lo: Optional[int] = Field(None, ge=0, le=20000)
    freqshift_reconnect_delay: Optional[int] = Field(None, ge=1000, le=10000)
    freqshift_pitch: Optional[int] = Field(None, ge=-4000, le=4000)
    log_level_birdnet_recording_service: Optional[str] = Field(None, pattern="^(error|warning|info|debug)$")
    log_level_live_audio_stream_service: Optional[str] = Field(None, pattern="^(error|warning|info|debug)$")
    log_level_spectrogram_viewer_service: Optional[str] = Field(None, pattern="^(error|warning|info|debug)$")


class ConfigResponse(BaseModel):
    """Configuration response (safe subset of settings)."""
    site_name: str
    latitude: float
    longitude: float
    database_lang: str
    color_scheme: str
    update_channel: str
    model: str
    sf_thresh: float
    data_model_version: int
    confidence: float
    sensitivity: float
    overlap: float
    birdweather_id: str
    info_site: str
    image_provider: str
    has_flickr_key: bool
    password_configured: bool
    birdnetpi_url: str
    rtsp_stream: str
    rtsp_stream_to_livestream: int
    activate_freqshift_in_livestream: bool
    apprise_config: str
    apprise_notification_title: str
    apprise_notification_body: str
    apprise_notify_each_detection: bool
    apprise_notify_new_species: bool
    apprise_notify_new_species_each_day: bool
    apprise_weekly_report: bool
    apprise_minimum_seconds_between_notifications_per_species: int
    apprise_only_notify_species_names: str
    apprise_only_notify_species_names_2: str
    privacy_threshold: int
    full_disk: str
    purge_threshold: int
    max_files_species: int
    rec_card: str
    channels: int
    recording_length: int
    extraction_length: int | None
    audiofmt: str
    silence_update_indicator: bool
    automatic_update: bool
    raw_spectrogram: bool
    rare_species_threshold: int
    custom_image: str
    custom_image_title: str
    freqshift_tool: str
    freqshift_hi: int
    freqshift_lo: int
    freqshift_reconnect_delay: int
    freqshift_pitch: int
    log_level_birdnet_recording_service: str
    log_level_live_audio_stream_service: str
    log_level_spectrogram_viewer_service: str


# System schemas
class ServiceStatus(BaseModel):
    """Status of a system service."""
    name: str
    active: bool
    enabled: bool
    status: str


class SystemInfo(BaseModel):
    """System information."""
    version: str
    uptime: Optional[str] = None
    disk_usage: Optional[dict] = None
    services: list[ServiceStatus]


class TimeConfigResponse(BaseModel):
    """System time and timezone settings."""
    timezone: str
    ntp_enabled: bool
    current_date: str
    current_time: str
    available_timezones: list[str]


class TimeConfigUpdate(BaseModel):
    """Updates to system time and timezone settings."""
    timezone: Optional[str] = None
    ntp_enabled: Optional[bool] = None
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class UpdateInstalledState(BaseModel):
    """Installed application and git metadata."""
    service_version: str
    git_hash: str
    git_branch: str
    current_commit: str
    current_branch: str
    current_tag: Optional[str] = None


class UpdateReleaseState(BaseModel):
    """Availability of a tagged release target."""
    channel: str
    tag: Optional[str] = None
    installed_version: str
    update_available: bool


class UpdateEdgeState(BaseModel):
    """Availability of the tracked edge branch head."""
    branch: str
    remote: str
    current_commit: str
    remote_commit: Optional[str] = None
    commits_behind: int
    update_available: bool


class UpdateRecommendation(BaseModel):
    """Recommended update target for the configured channel."""
    channel: str
    target: Optional[str] = None
    target_type: str
    update_available: bool
    summary: str


class UpdateApplyState(BaseModel):
    """State reported by the background updater script."""
    status: str
    stage: str
    channel: str
    target: Optional[str] = None
    target_type: Optional[str] = None
    message: str
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    pid: Optional[int] = None
    previous_ref: Optional[str] = None
    current_ref: Optional[str] = None
    backup_created: bool = False
    backup_path: Optional[str] = None
    error: Optional[str] = None
    running: bool = False


class UpdateStatusResponse(BaseModel):
    """Composite software update status."""
    installed: UpdateInstalledState
    update_channel: str
    available: dict[str, UpdateReleaseState | UpdateEdgeState]
    recommended: UpdateRecommendation
    apply_state: Optional[UpdateApplyState] = None
    current_commit: str
    commits_behind: int
    update_available: bool
    checked_at: str
    cache_ttl_seconds: int
    cached: bool
    error: Optional[str] = None


class ApplyUpdateRequest(BaseModel):
    """Request to apply an update."""
    channel: Optional[str] = Field(None, pattern="^(stable|prerelease|edge)$")
    target: Optional[str] = None
    branch: Optional[str] = None
    create_backup: bool = True


# Species list schemas
class SpeciesListUpdate(BaseModel):
    """Update to a species list."""
    species: str
    action: str = Field(..., pattern="^(add|remove)$")


class SpeciesListResponse(BaseModel):
    """Response with species list contents."""
    list_type: str
    species: list[str]


# Media schemas
class BirdImage(BaseModel):
    """Bird image information."""
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    author_url: Optional[str] = None
    license: Optional[str] = None
    license_url: Optional[str] = None
    source: str  # 'flickr', 'wikipedia', 'custom'


# Chart data schemas
class ChartDataPoint(BaseModel):
    """Single data point for charts."""
    date: str
    count: int


class SpeciesChartData(BaseModel):
    """Chart data for a species over time."""
    species: str
    com_name: str
    data: list[ChartDataPoint]


# Notification schemas
class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""
    title: Optional[str] = None
    body: Optional[str] = None
    config: Optional[str] = None


class NotificationResponse(BaseModel):
    """Response from notification endpoint."""
    success: bool
    message: str
