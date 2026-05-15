import { writable, derived } from 'svelte/store';
import type { Detection, DetectionStats, SpeciesSummary } from '$lib/api';

// Theme store
function createThemeStore() {
	const { subscribe, set, update } = writable<'light' | 'dark'>('light');

	return {
		subscribe,
		toggle: () => {
			update((theme) => {
				const newTheme = theme === 'light' ? 'dark' : 'light';
				if (typeof window !== 'undefined') {
					localStorage.setItem('theme', newTheme);
					document.documentElement.classList.toggle('dark', newTheme === 'dark');
				}
				return newTheme;
			});
		},
		set: (theme: 'light' | 'dark') => {
			if (typeof window !== 'undefined') {
				localStorage.setItem('theme', theme);
				document.documentElement.classList.toggle('dark', theme === 'dark');
			}
			set(theme);
		},
		init: () => {
			if (typeof window !== 'undefined') {
				const stored = localStorage.getItem('theme') as 'light' | 'dark' | null;
				const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
				const theme = stored || (prefersDark ? 'dark' : 'light');
				set(theme);
				document.documentElement.classList.toggle('dark', theme === 'dark');
			}
		},
	};
}

export const theme = createThemeStore();

// Auth store
interface AuthState {
	isAuthenticated: boolean;
	username: string;
	password: string;
}

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>({
		isAuthenticated: false,
		username: 'birdnet',
		password: '',
	});

	return {
		subscribe,
		login: (password: string) => {
			update((state) => ({
				...state,
				isAuthenticated: true,
				password,
			}));
		},
		logout: () => {
			set({
				isAuthenticated: false,
				username: 'birdnet',
				password: '',
			});
		},
		getCredentials: () => {
			let creds = { username: 'birdnet', password: '' };
			subscribe((state) => {
				creds = { username: state.username, password: state.password };
			})();
			return creds;
		},
	};
}

export const auth = createAuthStore();

// Latest detections store
export const latestDetections = writable<Detection[]>([]);

// Detection stats store
export const detectionStats = writable<DetectionStats | null>(null);

// Species list store
export const speciesList = writable<SpeciesSummary[]>([]);

// Site info store
interface SiteInfo {
	name: string;
	version: string;
	latitude: number;
	longitude: number;
	model: string;
}

export const siteInfo = writable<SiteInfo | null>(null);

// Loading states
export const isLoading = writable<Record<string, boolean>>({});

export function setLoading(key: string, loading: boolean) {
	isLoading.update((state) => ({ ...state, [key]: loading }));
}

// Error store
interface AppError {
	id: string;
	message: string;
	type: 'error' | 'warning' | 'info';
	timestamp: number;
}

function createErrorStore() {
	const { subscribe, update } = writable<AppError[]>([]);

	return {
		subscribe,
		add: (message: string, type: AppError['type'] = 'error') => {
			const error: AppError = {
				id: Math.random().toString(36).substring(7),
				message,
				type,
				timestamp: Date.now(),
			};
			update((errors) => [...errors, error]);

			// Auto-remove after 5 seconds
			setTimeout(() => {
				update((errors) => errors.filter((e) => e.id !== error.id));
			}, 5000);

			return error.id;
		},
		remove: (id: string) => {
			update((errors) => errors.filter((e) => e.id !== id));
		},
		clear: () => {
			update(() => []);
		},
	};
}

export const errors = createErrorStore();

// Notification store for toast messages
interface Toast {
	id: string;
	message: string;
	type: 'success' | 'error' | 'info' | 'warning';
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	return {
		subscribe,
		show: (message: string, type: Toast['type'] = 'info', duration = 3000) => {
			const toast: Toast = {
				id: Math.random().toString(36).substring(7),
				message,
				type,
			};
			update((toasts) => [...toasts, toast]);

			if (duration > 0) {
				setTimeout(() => {
					update((toasts) => toasts.filter((t) => t.id !== toast.id));
				}, duration);
			}

			return toast.id;
		},
		dismiss: (id: string) => {
			update((toasts) => toasts.filter((t) => t.id !== id));
		},
	};
}

export const toasts = createToastStore();

// Mobile menu state
export const isMobileMenuOpen = writable(false);

// Current audio playing
export const currentlyPlaying = writable<string | null>(null);
