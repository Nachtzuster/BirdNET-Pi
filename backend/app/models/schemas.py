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
    image_provider: str
    has_flickr_key: bool


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


class NotificationResponse(BaseModel):
    """Response from notification endpoint."""
    success: bool
    message: str
