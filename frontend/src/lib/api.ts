/**
 * API client for BirdNET-Pi backend
 */

const API_BASE = '/api';

interface RequestOptions {
	method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'HEAD';
	body?: unknown;
	auth?: { username: string; password: string };
}

class ApiError extends Error {
	constructor(public status: number, message: string) {
		super(message);
		this.name = 'ApiError';
	}
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
	const { method = 'GET', body, auth } = options;

	const headers: HeadersInit = {};
	const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
	if (body && !isFormData) {
		headers['Content-Type'] = 'application/json';
	}

	if (auth) {
		headers['Authorization'] = `Basic ${btoa(`${auth.username}:${auth.password}`)}`;
	}

	const response = await fetch(`${API_BASE}${endpoint}`, {
		method,
		headers,
		body: body ? (isFormData ? (body as FormData) : JSON.stringify(body)) : undefined,
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(response.status, error.detail || response.statusText);
	}

	return response.json();
}

async function requestBlob(
	endpoint: string,
	options: RequestOptions = {}
): Promise<{ blob: Blob; filename: string | null }> {
	const { method = 'GET', auth } = options;
	const headers: HeadersInit = {};

	if (auth) {
		headers['Authorization'] = `Basic ${btoa(`${auth.username}:${auth.password}`)}`;
	}

	const response = await fetch(`${API_BASE}${endpoint}`, {
		method,
		headers,
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new ApiError(response.status, error.detail || response.statusText);
	}

	const disposition = response.headers.get('Content-Disposition');
	let filename: string | null = null;

	if (disposition) {
		const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
		if (utf8Match) {
			filename = decodeURIComponent(utf8Match[1]);
		} else {
			const basicMatch = disposition.match(/filename="?([^"]+)"?/i);
			if (basicMatch) filename = basicMatch[1];
		}
	}

	return {
		blob: await response.blob(),
		filename,
	};
}

// Detection API
export const detections = {
	list: (params?: { limit?: number; offset?: number; date?: string; species?: string; search?: string; new_on_date?: boolean }) => {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));
		if (params?.date) searchParams.set('date', params.date);
		if (params?.species) searchParams.set('species', params.species);
		if (params?.search) searchParams.set('search', params.search);
		if (params?.new_on_date) searchParams.set('new_on_date', 'true');
		const query = searchParams.toString();
		return request<DetectionList>(`/detections${query ? `?${query}` : ''}`);
	},

	today: (params?: { limit?: number; search?: string }) => {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.search) searchParams.set('search', params.search);
		const query = searchParams.toString();
		return request<{ detections: Detection[]; date: string }>(`/detections/today${query ? `?${query}` : ''}`);
	},

	latest: () => request<Detection | null>('/detections/latest'),

	stats: () => request<DetectionStats>('/detections/stats'),

	newSpeciesToday: () => request<Detection[]>('/detections/new-species-today'),

	dates: () => request<{ dates: string[] }>('/detections/dates'),

	chartData: (date: string) => request<ChartData>(`/detections/chart-data/${date}`),

	chartDataRange: (params: { start: string; end: string; group_by: 'hour' | 'day' | 'week' | 'month' }) => {
		const searchParams = new URLSearchParams({
			start: params.start,
			end: params.end,
			group_by: params.group_by,
		});
		return request<RangeChartData>(`/detections/chart-data-range?${searchParams}`);
	},

	dailyReport: (date?: string) =>
		request<DailyReport>(
			`/detections/daily-report${date ? `?date=${encodeURIComponent(date)}` : ''}`
		),

	weeklyReport: (endDate?: string) =>
		request<WeeklyReport>(
			`/detections/weekly-report${endDate ? `?end_date=${encodeURIComponent(endDate)}` : ''}`
		),

	delete: (filename: string, auth: { username: string; password: string }) =>
		request(`/detections/${encodeURIComponent(filename)}`, { method: 'DELETE', auth }),
};

// Species API
export const species = {
	list: (params?: { sort?: string; date?: string }) => {
		const searchParams = new URLSearchParams();
		if (params?.sort) searchParams.set('sort', params.sort);
		if (params?.date) searchParams.set('date', params.date);
		const query = searchParams.toString();
		return request<SpeciesList>(`/species${query ? `?${query}` : ''}`);
	},

	detections: (sciName: string, params?: { limit?: number; offset?: number }) => {
		const searchParams = new URLSearchParams();
		if (params?.limit) searchParams.set('limit', String(params.limit));
		if (params?.offset) searchParams.set('offset', String(params.offset));
		const query = searchParams.toString();
		return request<SpeciesDetectionsResponse>(`/species/${encodeURIComponent(sciName)}/detections${query ? `?${query}` : ''}`);
	},

	chartData: (sciName: string, days = 7) =>
		request<SpeciesChartData>(`/species/${encodeURIComponent(sciName)}/chart-data?days=${days}`),

	stats: (sciName: string) => request<SpeciesStats>(`/species/${encodeURIComponent(sciName)}/stats`),

	delete: (sciName: string, auth: { username: string; password: string }) =>
		request(`/species/${encodeURIComponent(sciName)}`, { method: 'DELETE', auth }),

	getLists: (sciName: string) => request<SpeciesListMembership>(`/species/${encodeURIComponent(sciName)}/lists`),
};

// Species lists API
export const speciesLists = {
	get: (listType: string) => request<{ list_type: string; species: string[] }>(`/species-lists/${listType}`),

	update: (listType: string, species: string, action: 'add' | 'remove', auth: { username: string; password: string }) =>
		request(`/species-lists/${listType}`, {
			method: 'POST',
			body: { species, action },
			auth,
		}),
};

// Media API
export const media = {
	audioUrl: (date: string, species: string, filename: string) =>
		`${API_BASE}/media/audio/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,

	temporalZoomAudioUrl: (date: string, species: string, filename: string, rate: number) =>
		`${API_BASE}/media/tempo/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}?rate=${rate}`,

	temporalZoomPrepareUrl: (date: string, species: string, filename: string, rate: number) =>
		`${API_BASE}/media/tempo/prepare/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}?rate=${rate}`,

	spectrogramUrl: (date: string, species: string, filename: string) =>
		`${API_BASE}/media/spectrogram/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,

	chartUrl: (date: string) => `${API_BASE}/media/chart/${date}`,

	dates: () => request<{ dates: string[] }>('/media/dates'),

	speciesForDate: (date: string) => request<{ date: string; species: { name: string; count: number }[] }>(`/media/dates/${date}/species`),

	filesForSpecies: (date: string, species: string) =>
		request<{ date: string; species: string; files: { name: string; has_spectrogram: boolean; size: number }[] }>(
			`/media/dates/${date}/${encodeURIComponent(species)}/files`
		),

	speciesMeta: (date: string, species: string) =>
		request<{ date: string; species: string; sci_name: string; com_name: string }>(
			`/media/dates/${date}/${encodeURIComponent(species)}/meta`
		),

	shiftedAudioUrl: (date: string, species: string, filename: string) =>
		`${API_BASE}/media/shifted/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,

	createShifted: (
		date: string,
		species: string,
		filename: string,
		auth: { username: string; password: string },
		pitch = -1000
	) =>
		request<{ message: string; path: string }>(
			`/media/shift/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}?pitch=${pitch}`,
			{ method: 'POST', auth }
		),

	deleteShifted: (
		date: string,
		species: string,
		filename: string,
		auth: { username: string; password: string }
	) =>
		request<{ message: string }>(
			`/media/shift/${date}/${encodeURIComponent(species)}/${encodeURIComponent(filename)}`,
			{ method: 'DELETE', auth }
	),
};

// File manager API
export const fileManager = {
	roots: (auth: { username: string; password: string }) =>
		request<FileRootsResponse>('/files/roots', { auth }),

	list: (root: string, path: string, auth: { username: string; password: string }) => {
		const searchParams = new URLSearchParams({ root });
		if (path) searchParams.set('path', path);
		return request<FileListingResponse>(`/files/list?${searchParams.toString()}`, { auth });
	},

	delete: (root: string, path: string, auth: { username: string; password: string }) => {
		const searchParams = new URLSearchParams({ root, path });
		return request<{ message: string; path: string }>(`/files?${searchParams.toString()}`, {
			method: 'DELETE',
			auth,
		});
	},

	download: (root: string, path: string, auth: { username: string; password: string }) => {
		const searchParams = new URLSearchParams({ root, path });
		return requestBlob(`/files/download?${searchParams.toString()}`, { auth });
	},
};

// Config API
export const config = {
	get: (auth: { username: string; password: string }) => request<Config>('/config', { auth }),

	update: (data: Partial<Config>, auth: { username: string; password: string }) =>
		request<{ message: string; updated_fields: string[]; applied_actions: string[] }>('/config', {
			method: 'PUT',
			body: data,
			auth,
		}),

	testNotification: (data: { title?: string; body?: string; config?: string }, auth: { username: string; password: string }) =>
		request<{ success: boolean; message: string }>('/config/test-notification', { method: 'POST', body: data, auth }),
	models: () =>
		request<{ models: { name: string; active: boolean; supports_species_filter: boolean }[]; current: string }>('/config/models'),

	languages: () => request<{ languages: { code: string; active: boolean }[]; current: string }>('/config/languages'),

	previewSpecies: (threshold: number, model: string, dataModelVersion: number) =>
		request<{ threshold: number; model: string; data_model_version: number; count: number; species: string[] }>(
			`/config/preview-species?threshold=${threshold}&model=${encodeURIComponent(model)}&data_model_version=${dataModelVersion}`
		),
};

// System API
export const system = {
	publicStatus: () =>
		request<PublicSystemStatus>('/system/public-status'),

	info: (auth: { username: string; password: string }) => request<SystemInfo>('/system/info', { auth }),

	services: (auth: { username: string; password: string }) => request<{ services: ServiceStatus[] }>('/system/services', { auth }),

	controlService: (service: string, action: string, auth: { username: string; password: string }) =>
		request(`/system/services/${service}/${action}`, { method: 'POST', auth }),

	restartServices: (auth: { username: string; password: string }) =>
		request('/system/restart-services', { method: 'POST', auth }),

	reboot: (auth: { username: string; password: string }) =>
		request('/system/reboot', { method: 'POST', auth }),

	shutdown: (auth: { username: string; password: string }) =>
		request('/system/shutdown', { method: 'POST', auth }),

	clearData: (auth: { username: string; password: string }) =>
		request('/system/clear-data', { method: 'POST', auth }),

	logs: (service: string, lines: number, auth: { username: string; password: string }) =>
		request<{ service: string; lines: number; logs: string }>(`/system/logs/${service}?lines=${lines}`, { auth }),

	updateStatus: (auth: { username: string; password: string }, forceRefresh = false) =>
		request<UpdateStatus>(
			`/system/update-status${forceRefresh ? '?force_refresh=true' : ''}`,
			{ auth }
		),

	updateLog: (auth: { username: string; password: string }, lines = 200) =>
		request<{ lines: number; log: string }>(`/system/update-log?lines=${lines}`, { auth }),

	applyUpdate: (
		data: { channel?: 'stable' | 'prerelease' | 'edge'; target?: string; branch?: string; create_backup?: boolean },
		auth: { username: string; password: string }
	) => request<{ message: string; channel: string; target: string | null; create_backup: boolean }>('/system/apply-update', { method: 'POST', body: data, auth }),

	restore: (file: File, auth: { username: string; password: string }) => {
		const formData = new FormData();
		formData.append('file', file);
		return request<{ message: string; output?: string }>('/system/restore', { method: 'POST', body: formData, auth });
	},

	liveStreamUrl: (auth: { username: string; password: string }) =>
		request<{ url: string; expires_at: string; ttl_seconds: number }>('/system/live-stream-url', { method: 'POST', auth }),

	timeConfig: (auth: { username: string; password: string }) =>
		request<TimeConfig>('/system/time-config', { auth }),

	updateTimeConfig: (data: { timezone?: string; ntp_enabled?: boolean; date?: string; time?: string }, auth: { username: string; password: string }) =>
		request<TimeConfig>('/system/time-config', { method: 'PUT', body: data, auth }),
};

// Integrations API
export const integrations = {
	image: (sciName: string) => request<BirdImage | null>(`/image/${encodeURIComponent(sciName)}`),

	blacklistImage: (sciName: string, auth: { username: string; password: string }) =>
		request(`/image/${encodeURIComponent(sciName)}/blacklist`, { method: 'POST', auth }),

	birdweatherStatus: () => request<{ enabled: boolean; station_id: string | null; station_url: string | null }>('/birdweather/status'),

	labels: () => request<{ language: string; count: number; labels: Record<string, string> }>('/labels'),

	speciesLinks: (sciName: string, comName?: string) => {
		const searchParams = new URLSearchParams();
		if (comName) searchParams.set('com_name', comName);
		const query = searchParams.toString();
		return request<SpeciesExternalLinks>(`/species-links/${encodeURIComponent(sciName)}${query ? `?${query}` : ''}`);
	},

	ebirdExport: (date: string, minConfidence = 0.75) =>
		request<{ date: string; species_count: number; csv: string }>(`/ebird/export/${date}?min_confidence=${minConfidence}`),
};

// Health API
export const health = {
	check: () => request<{ status: string; site_name: string }>('/health'),
	info: () => request<{ name: string; version: string; site_name: string; latitude: number; longitude: number; model: string }>('/info'),
};

// Types
export interface Detection {
	Date: string;
	Time: string;
	Sci_Name: string;
	Com_Name: string;
	Confidence: number;
	Lat: number | null;
	Lon: number | null;
	Cutoff: number | null;
	Week: number | null;
	Sens: number | null;
	Overlap: number | null;
	File_Name: string;
}

export interface DetectionList {
	detections: Detection[];
	total: number;
	limit: number;
	offset: number;
}

export interface DetectionStats {
	total_count: number;
	todays_count: number;
	hour_count: number;
	new_species_today: number;
	todays_species_tally: number;
	species_tally: number;
}

export interface WeeklyReportSpecies {
	sci_name: string;
	com_name: string;
	count: number;
	previous_count?: number;
	change_pct?: number | null;
	is_new_this_week?: boolean;
}

export interface DailyReportSpecies {
	sci_name: string;
	com_name: string;
	count: number;
	previous_count?: number;
	change_pct?: number | null;
	is_new_this_day?: boolean;
}

export interface DailyReport {
	label: string;
	date: string;
	previous_date: string;
	total_detections: number;
	previous_total_detections: number;
	total_detections_change_pct: number | null;
	species_count: number;
	previous_species_count: number;
	species_count_change_pct: number | null;
	peak_hour: number | null;
	top_species: DailyReportSpecies[];
	first_seen_species: DailyReportSpecies[];
}

export interface WeeklyReport {
	label: string;
	start_date: string;
	end_date: string;
	week_number: number;
	year: number;
	total_detections: number;
	previous_total_detections: number;
	total_detections_change_pct: number | null;
	species_count: number;
	previous_species_count: number;
	species_count_change_pct: number | null;
	top_species: WeeklyReportSpecies[];
	first_seen_species: WeeklyReportSpecies[];
}

export interface SpeciesSummary {
	Date: string;
	Time: string;
	File_Name: string;
	Com_Name: string;
	Sci_Name: string;
	Count: number;
	MaxConfidence: number;
}

export interface SpeciesList {
	species: SpeciesSummary[];
	total: number;
}

export interface SpeciesChartData {
	species: string;
	com_name: string;
	days: number;
	data: { date: string; count: number }[];
}

export interface SpeciesStats {
	sci_name: string;
	com_name: string;
	total_detections: number;
	days_detected: number;
	first_detection: string;
	last_detection: string;
	avg_confidence: number;
	max_confidence: number;
}

export interface SpeciesDetectionsResponse {
	species: string;
	detections: Detection[];
	total: number;
	limit: number;
	offset: number;
}

export interface SpeciesListMembership {
	species: string;
	lists: Record<'include' | 'exclude' | 'whitelist' | 'confirmed', boolean>;
}

export interface Config {
	site_name: string;
	latitude: number;
	longitude: number;
	database_lang: string;
	color_scheme: string;
	update_channel: 'stable' | 'prerelease' | 'edge';
	info_site: 'ALLABOUTBIRDS' | 'EBIRD';
	model: string;
	sf_thresh: number;
	data_model_version: number;
	confidence: number;
	sensitivity: number;
	overlap: number;
	birdweather_id: string;
	image_provider: string;
	has_flickr_key: boolean;
	flickr_filter_email: string;
	password_configured: boolean;
	birdnetpi_url: string;
	rtsp_stream: string;
	rtsp_stream_to_livestream: number;
	activate_freqshift_in_livestream: boolean;
	apprise_config: string;
	apprise_notification_title: string;
	apprise_notification_body: string;
	apprise_notify_each_detection: boolean;
	apprise_notify_new_species: boolean;
	apprise_notify_new_species_each_day: boolean;
	apprise_weekly_report: boolean;
	apprise_minimum_seconds_between_notifications_per_species: number;
	apprise_only_notify_species_names: string;
	apprise_only_notify_species_names_2: string;
	privacy_threshold: number;
	full_disk: 'purge' | 'keep';
	purge_threshold: number;
	max_files_species: number;
	rec_card: string;
	channels: number;
	recording_length: number;
	extraction_length: number | null;
	audiofmt: string;
	silence_update_indicator: boolean;
	automatic_update: boolean;
	raw_spectrogram: boolean;
	rare_species_threshold: number;
	custom_image: string;
	custom_image_title: string;
	freqshift_tool: 'sox' | 'ffmpeg';
	freqshift_hi: number;
	freqshift_lo: number;
	freqshift_reconnect_delay: number;
	freqshift_pitch: number;
	log_level_birdnet_recording_service: 'error' | 'warning' | 'info' | 'debug';
	log_level_live_audio_stream_service: 'error' | 'warning' | 'info' | 'debug';
	log_level_spectrogram_viewer_service: 'error' | 'warning' | 'info' | 'debug';
}

export interface ServiceStatus {
	name: string;
	active: boolean;
	enabled: boolean;
	status: string;
}

export interface SystemInfo {
	version: string;
	uptime: string | null;
	disk_usage: { total: string; used: string; available: string; percent: string } | null;
	services: ServiceStatus[];
}

export interface TimeConfig {
	timezone: string;
	ntp_enabled: boolean;
	current_date: string;
	current_time: string;
	available_timezones: string[];
}

export interface PublicSystemStatus {
	status: 'online' | 'offline' | 'degraded' | string;
	checked_at: string;
	uptime: string | null;
	last_detection: string | null;
	version: string;
	service_summary?: {
		core_total: number;
		core_active: number;
		inactive_core_services: string[];
	};
}

export interface UpdateInstalledState {
	service_version: string;
	git_hash: string;
	git_branch: string;
	current_commit: string;
	current_branch: string;
	current_tag: string | null;
}

export interface UpdateReleaseState {
	channel: 'stable' | 'prerelease';
	tag: string | null;
	installed_version: string;
	update_available: boolean;
}

export interface UpdateEdgeState {
	branch: string;
	remote: string;
	current_commit: string;
	remote_commit: string | null;
	commits_behind: number;
	update_available: boolean;
}

export interface UpdateRecommendation {
	channel: 'stable' | 'prerelease' | 'edge';
	target: string | null;
	target_type: 'tag' | 'branch' | string;
	update_available: boolean;
	summary: string;
}

export interface UpdateApplyState {
	status: string;
	stage: string;
	channel: string;
	target: string | null;
	target_type: string | null;
	message: string;
	started_at: string | null;
	updated_at: string | null;
	pid: number | null;
	previous_ref: string | null;
	current_ref: string | null;
	backup_created: boolean;
	backup_path: string | null;
	error: string | null;
	running: boolean;
}

export interface UpdateStatus {
	installed: UpdateInstalledState;
	update_channel: 'stable' | 'prerelease' | 'edge';
	available: {
		stable: UpdateReleaseState;
		prerelease: UpdateReleaseState;
		edge: UpdateEdgeState;
	};
	recommended: UpdateRecommendation;
	apply_state: UpdateApplyState | null;
	current_commit: string;
	commits_behind: number;
	update_available: boolean;
	checked_at: string;
	cache_ttl_seconds: number;
	cached: boolean;
	error?: string;
}

export interface SpeciesHourly {
	sci_name: string;
	com_name: string;
	hourly: number[];
}

export interface ChartData {
	date: string;
	total_detections: number;
	species_count: number;
	hourly: { hour: number; count: number }[];
	top_species: { com_name: string; sci_name: string; count: number; max_confidence: number }[];
	species_hourly: SpeciesHourly[];
}

export interface RangeChartData {
	start: string;
	end: string;
	group_by: 'hour' | 'day' | 'week' | 'month';
	total_detections: number;
	species_count: number;
	buckets: { period: number | string; count: number }[];
	top_species: { com_name: string; sci_name: string; count: number; max_confidence: number }[];
	species_buckets: { sci_name: string; com_name: string; counts: number[] }[];
}

export interface BirdImage {
	url: string;
	title: string | null;
	author: string | null;
	author_url: string | null;
	license: string | null;
	license_url: string | null;
	source: string;
}

export interface FileRoot {
	id: string;
	label: string;
	description: string;
	available: boolean;
	file_count: number | null;
	total_size: number | null;
}

export interface FileRootsResponse {
	roots: FileRoot[];
}

export interface FileEntry {
	name: string;
	path: string;
	entry_type: 'file' | 'directory';
	size: number | null;
	file_count: number | null;
	total_size: number | null;
	modified_at: string;
}

export interface FileListingResponse {
	root: string;
	root_label: string;
	current_path: string;
	parent_path: string | null;
	entries: FileEntry[];
}

export interface SpeciesExternalLinks {
	sci_name: string;
	com_name: string | null;
	english_name: string;
	ebird: {
		available: boolean;
		code: string | null;
		url: string | null;
	};
	allaboutbirds: {
		available: boolean;
		slug: string | null;
		url: string | null;
	};
}

export { ApiError };
