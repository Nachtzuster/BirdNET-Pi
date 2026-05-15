<script lang="ts">
	import { onMount } from 'svelte';
	import { system as systemApi, type PublicSystemStatus } from '$lib/api';
	import { auth, toasts } from '$lib/stores';
	import { Modal } from '$lib/components';

	let publicStatus: PublicSystemStatus | null = null;
	let loading = true;
	let statusState: 'online' | 'degraded' | 'offline' = 'online';
	let statusText = 'Online';
	let refreshTimer: ReturnType<typeof setInterval> | undefined;

	let adminVerified = false;
	let showAdminLinks = false;
	let showLoginModal = false;
	let passwordInput = '';
	let verifyingLogin = false;

	function formatTimestamp(value: string | null): string {
		if (!value) return 'Unavailable';
		const normalized = value.includes('T') ? value : value.replace(' ', 'T');
		const date = new Date(normalized);
		if (Number.isNaN(date.getTime())) return value;
		return date.toLocaleString();
	}

	async function loadStatus() {
		try {
			publicStatus = await systemApi.publicStatus();
			statusState = publicStatus.status === 'degraded' ? 'degraded' : 'online';
			statusText = statusState === 'degraded' ? 'Degraded' : 'Online';
		} catch (error) {
			console.error('Failed to load public status:', error);
			statusState = 'offline';
			statusText = 'Offline';
			publicStatus = null;
		} finally {
			loading = false;
		}
	}

	async function verifyExistingSession() {
		if (!$auth.isAuthenticated) return;

		try {
			await systemApi.info(auth.getCredentials());
			adminVerified = true;
		} catch (error: any) {
			if (error?.status === 401) {
				auth.logout();
			}
			adminVerified = false;
		}
	}

	function openAdminAccess() {
		if (adminVerified) {
			showAdminLinks = !showAdminLinks;
			return;
		}
		showLoginModal = true;
	}

	async function handleAdminLogin() {
		if (!passwordInput.trim()) return;

		verifyingLogin = true;
		auth.login(passwordInput);
		try {
			await systemApi.info(auth.getCredentials());
			adminVerified = true;
			showAdminLinks = true;
			showLoginModal = false;
			passwordInput = '';
			toasts.show('Authenticated', 'success');
		} catch (error: any) {
			auth.logout();
			adminVerified = false;
			toasts.show(error?.status === 401 ? 'Invalid password' : 'Failed to authenticate', 'error');
		} finally {
			verifyingLogin = false;
		}
	}

	onMount(() => {
		void Promise.all([loadStatus(), verifyExistingSession()]);

		refreshTimer = setInterval(() => {
			void loadStatus();
		}, 30000);

		return () => {
			if (refreshTimer) clearInterval(refreshTimer);
		};
	});
</script>

<svelte:head>
	<title>Status - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex items-start justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Status</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">High-level system health and runtime information</p>
		</div>
		<button
			on:click={openAdminAccess}
			class="p-2 rounded-lg bg-gray-200 dark:bg-dark-card border border-gray-300 dark:border-dark-border text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-dark-hover"
			aria-label="Admin access"
			title={adminVerified ? 'Admin shortcuts' : 'Authenticate for admin access'}
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l.7 2.153a1 1 0 00.95.69h2.264c.969 0 1.371 1.24.588 1.81l-1.832 1.332a1 1 0 00-.364 1.118l.7 2.153c.3.921-.755 1.688-1.54 1.118l-1.832-1.332a1 1 0 00-1.176 0l-1.832 1.332c-.784.57-1.838-.197-1.539-1.118l.7-2.153a1 1 0 00-.364-1.118L6.547 7.58c-.783-.57-.38-1.81.588-1.81h2.264a1 1 0 00.95-.69l.7-2.153z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v7m0 0l-3-3m3 3l3-3" />
			</svg>
		</button>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<div class="grid md:grid-cols-3 gap-4 mb-6">
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Server</p>
				<div class="flex items-center gap-2">
					<span
						class="w-3 h-3 rounded-full"
						class:bg-green-500={statusState === 'online'}
						class:bg-amber-500={statusState === 'degraded'}
						class:bg-red-500={statusState === 'offline'}></span>
					<p class="font-semibold text-gray-900 dark:text-gray-100">{statusText}</p>
				</div>
			</div>
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400 mb-1">Uptime</p>
				<p class="font-semibold text-gray-900 dark:text-gray-100">{publicStatus?.uptime || 'Unavailable'}</p>
			</div>
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400 mb-1">Version</p>
				<p class="font-semibold text-gray-900 dark:text-gray-100">{publicStatus?.version || 'Unknown'}</p>
			</div>
		</div>

		<div class="card p-4 mb-6">
			<p class="text-sm text-gray-500 dark:text-gray-400">Last detection update</p>
			<p class="mt-1 text-gray-900 dark:text-gray-100">{formatTimestamp(publicStatus?.last_detection || null)}</p>
			<p class="mt-4 text-sm text-gray-500 dark:text-gray-400">Last checked</p>
			<p class="mt-1 text-gray-900 dark:text-gray-100">{formatTimestamp(publicStatus?.checked_at || null)}</p>

			{#if publicStatus?.service_summary && publicStatus.status === 'degraded'}
				<p class="mt-4 text-sm text-amber-600 dark:text-amber-400">
					Core services active: {publicStatus.service_summary.core_active}/{publicStatus.service_summary.core_total}
				</p>
				{#if publicStatus.service_summary.inactive_core_services.length > 0}
					<p class="mt-1 text-sm text-amber-600 dark:text-amber-400">
						Inactive: {publicStatus.service_summary.inactive_core_services.join(', ')}
					</p>
				{/if}
			{/if}
		</div>

		{#if adminVerified && showAdminLinks}
			<div class="card p-4">
				<h2 class="font-semibold text-gray-900 dark:text-gray-100 mb-3">Admin Shortcuts</h2>
				<div class="flex flex-wrap gap-3">
					<a href="/settings" class="btn-primary">Settings</a>
					<a href="/settings/system" class="btn-secondary">System</a>
					<a href="/live-logs" class="btn-secondary">Live Logs</a>
					<a href="/species/manage" class="btn-secondary">Species Lists</a>
				</div>
			</div>
		{/if}
	{/if}
</div>

<Modal bind:open={showLoginModal} title="Admin Authentication">
	<form on:submit|preventDefault={handleAdminLogin} class="space-y-4">
		<div>
			<label for="statusPassword" class="label">Password</label>
			<input
				id="statusPassword"
				type="password"
				bind:value={passwordInput}
				class="input"
				placeholder="Enter password"
			/>
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">
				Cancel
			</button>
			<button type="submit" class="btn-primary" disabled={verifyingLogin}>
				{#if verifyingLogin}
					<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
				{/if}
				Authenticate
			</button>
		</div>
	</form>
</Modal>
