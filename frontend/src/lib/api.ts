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

// Config API
export const config = {
	get: (auth: { username: string; password: string }) => request<Config>('/config', { auth }),

	update: (data: Partial<Config>, auth: { username: string; password: string }) =>
		request('/config', { method: 'PUT', body: data, auth }),

	testNotification: (data: { title?: string; body?: string }, auth: { username: string; password: string }) =>
		request<{ success: boolean; message: string }>('/config/test-notification', { method: 'POST', body: data, auth }),

	models: () => request<{ models: { name: string; active: boolean }[]; current: string }>('/config/models'),

	languages: () => request<{ languages: { code: string; active: boolean }[]; current: string }>('/config/languages'),

	previewSpecies: (threshold: number) =>
		request<{ threshold: number; count: number; species: string[] }>(`/config/preview-species?threshold=${threshold}`),
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
};

// Integrations API
export const integrations = {
	image: (sciName: string) => request<BirdImage>(`/image/${encodeURIComponent(sciName)}`),

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
	model: string;
	confidence: number;
	sensitivity: number;
	overlap: number;
	birdweather_id: string;
	image_provider: string;
	has_flickr_key: boolean;
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
