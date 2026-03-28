<script lang="ts">
	import { onMount } from 'svelte';
	import { system as systemApi, type ServiceStatus, type SystemInfo, type TimeConfig, type UpdateStatus } from '$lib/api';
	import { verifyPasswordLogin } from '$lib/auth';
	import { auth, toasts } from '$lib/stores';
	import { Modal } from '$lib/components';

	let systemInfo: SystemInfo | null = null;
	let services: ServiceStatus[] = [];
	let updateStatus: UpdateStatus | null = null;
	let updateLog = '';
	let loading = true;
	let updateLoading = false;
	let showLoginModal = false;
	let passwordInput = '';
	let actionLoading: Record<string, boolean> = {};
	let restoreFile: File | null = null;
	let restoring = false;
	let applyingUpdate = false;
	let createBackup = true;
	let updatePollHandle: ReturnType<typeof setInterval> | null = null;
	let timeConfig: TimeConfig | null = null;
	let timeTimezone = '';
	let timeNtpEnabled = true;
	let manualDate = '';
	let manualTime = '';
	let timeSaving = false;

	async function loadUpdateData(forceRefresh = false, silent = false) {
		if (!$auth.isAuthenticated) return;

		if (!silent) {
			updateLoading = true;
		}

		try {
			const status = await systemApi.updateStatus(auth.getCredentials(), forceRefresh);
			updateStatus = status;

			if (status.apply_state) {
				const logData = await systemApi.updateLog(auth.getCredentials(), 120);
				updateLog = logData.log;
			} else {
				updateLog = '';
			}
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else if (!silent) {
				console.error('Failed to load update status:', e);
				toasts.show('Failed to load software update status', 'error');
			}
		} finally {
			updateLoading = false;
		}
	}

	async function loadData() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			loading = false;
			return;
		}

		loading = true;
		try {
			const [infoData, servicesData, timeData] = await Promise.all([
				systemApi.info(auth.getCredentials()),
				systemApi.services(auth.getCredentials()),
				systemApi.timeConfig(auth.getCredentials()),
			]);
			systemInfo = infoData;
			services = servicesData.services;
			timeConfig = timeData;
			timeTimezone = timeData.timezone;
			timeNtpEnabled = timeData.ntp_enabled;
			manualDate = timeData.current_date;
			manualTime = timeData.current_time;
			await loadUpdateData(false, true);
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to load system info:', e);
				toasts.show('Failed to load system information', 'error');
			}
		} finally {
			loading = false;
		}
	}

	async function saveTimeConfig() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		if (!timeNtpEnabled && (!manualDate || !manualTime)) {
			toasts.show('Manual date and time are both required when NTP is disabled', 'error');
			return;
		}

		timeSaving = true;
		try {
			const result = await systemApi.updateTimeConfig(
				{
					timezone: timeTimezone,
					ntp_enabled: timeNtpEnabled,
					date: timeNtpEnabled ? undefined : manualDate,
					time: timeNtpEnabled ? undefined : manualTime,
				},
				auth.getCredentials()
			);
			timeConfig = result;
			timeTimezone = result.timezone;
			timeNtpEnabled = result.ntp_enabled;
			manualDate = result.current_date;
			manualTime = result.current_time;
			toasts.show('Time settings updated', 'success');
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show(e.message || 'Failed to update time settings', 'error');
			}
		} finally {
			timeSaving = false;
		}
	}

	async function refreshUpdateStatus() {
		await loadUpdateData(true);
		if (updateStatus && !updateStatus.error) {
			toasts.show('Software update status refreshed', 'success');
		}
	}

	async function applyRecommendedUpdate() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		if (!updateStatus?.recommended.target) {
			toasts.show('No update target is available for the current channel', 'error');
			return;
		}

		const warning =
			updateStatus.update_channel === 'stable'
				? `Apply the recommended stable update ${updateStatus.recommended.target}?`
				: `Apply the recommended ${updateStatus.update_channel} update ${updateStatus.recommended.target}? Non-stable channels may include breaking changes.`;

		if (!confirm(`${warning}\n\nA backup will ${createBackup ? '' : 'not '}be created before the update.`)) {
			return;
		}

		applyingUpdate = true;
		try {
			await systemApi.applyUpdate(
				{
					channel: updateStatus.update_channel,
					create_backup: createBackup,
				},
				auth.getCredentials()
			);
			toasts.show('Software update started', 'success');
			await loadUpdateData(true);
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show(e.message || 'Failed to start software update', 'error');
			}
		} finally {
			applyingUpdate = false;
		}
	}

	async function controlService(service: string, action: string) {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		actionLoading[service] = true;
		try {
			await systemApi.controlService(service, action, auth.getCredentials());
			toasts.show(`Service ${service} ${action} successful`, 'success');
			const result = await systemApi.services(auth.getCredentials());
			services = result.services;
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show(`Failed to ${action} ${service}`, 'error');
			}
		} finally {
			actionLoading[service] = false;
		}
	}

	async function restartAllServices() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		actionLoading['all'] = true;
		try {
			await systemApi.restartServices(auth.getCredentials());
			toasts.show('Services restart initiated', 'success');
			setTimeout(loadData, 3000);
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show('Failed to restart services', 'error');
			}
		} finally {
			actionLoading['all'] = false;
		}
	}

	async function rebootSystem() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		if (!confirm('Are you sure you want to reboot the system?')) return;

		try {
			await systemApi.reboot(auth.getCredentials());
			toasts.show('System reboot initiated', 'info');
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show('Failed to reboot', 'error');
			}
		}
	}

	async function shutdownSystem() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		if (!confirm('Are you sure you want to shut down the system?')) return;

		try {
			await systemApi.shutdown(auth.getCredentials());
			toasts.show('System shutdown initiated', 'info');
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show('Failed to shut down the system', 'error');
			}
		}
	}

	async function clearAllData() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}

		const warning = 'Clear ALL detections, recordings, and derived data? This cannot be undone and may take up to a couple of minutes.';
		if (!confirm(warning)) return;

		actionLoading['clear-data'] = true;
		try {
			await systemApi.clearData(auth.getCredentials());
			toasts.show('All data cleared successfully', 'success');
			await loadData();
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show(e.message || 'Failed to clear all data', 'error');
			}
		} finally {
			actionLoading['clear-data'] = false;
		}
	}

	async function restoreBackup() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			return;
		}
		if (!restoreFile) {
			toasts.show('Select a backup file first', 'error');
			return;
		}
		if (!confirm('Restoring a backup will overwrite current data. Continue?')) return;

		restoring = true;
		try {
			await systemApi.restore(restoreFile, auth.getCredentials());
			toasts.show('Restore completed successfully', 'success');
			restoreFile = null;
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show('Restore failed', 'error');
			}
		} finally {
			restoring = false;
		}
	}

	function onRestoreFileSelected(event: Event) {
		const target = event.currentTarget as HTMLInputElement;
		restoreFile = target.files?.[0] ?? null;
	}

	async function handleLogin() {
		const result = await verifyPasswordLogin(passwordInput);
		if (!result.ok) {
			toasts.show(result.message || 'Failed to authenticate', 'error');
			return;
		}

		showLoginModal = false;
		passwordInput = '';
		toasts.show('Authenticated', 'success');
		await loadData();
	}

	onMount(() => {
		loadData();
		updatePollHandle = setInterval(() => {
			if ($auth.isAuthenticated) {
				loadUpdateData(false, true);
			}
		}, 10000);

		return () => {
			if (updatePollHandle) {
				clearInterval(updatePollHandle);
			}
		};
	});
</script>

<svelte:head>
	<title>System - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">System</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">System information, services, backups, and software updates</p>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !$auth.isAuthenticated}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400 mb-4">Please log in to access system information</p>
			<button on:click={() => (showLoginModal = true)} class="btn-primary">
				Log in
			</button>
		</div>
	{:else}
		<div class="card mb-6">
			<div class="card-header">
				<h2 class="font-semibold text-gray-900 dark:text-gray-100">System Information</h2>
			</div>
			<div class="card-body">
				<div class="grid md:grid-cols-2 gap-4">
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Version</p>
						<p class="font-mono text-gray-900 dark:text-gray-100">{systemInfo?.version || 'Unknown'}</p>
					</div>
					<div>
						<p class="text-sm text-gray-500 dark:text-gray-400">Uptime</p>
						<p class="text-gray-900 dark:text-gray-100">{systemInfo?.uptime || 'Unknown'}</p>
					</div>
					{#if systemInfo?.disk_usage}
						<div>
							<p class="text-sm text-gray-500 dark:text-gray-400">Disk Usage</p>
							<p class="text-gray-900 dark:text-gray-100">
								{systemInfo.disk_usage.used} / {systemInfo.disk_usage.total} ({systemInfo.disk_usage.percent})
							</p>
						</div>
						<div>
							<p class="text-sm text-gray-500 dark:text-gray-400">Available</p>
							<p class="text-gray-900 dark:text-gray-100">{systemInfo.disk_usage.available}</p>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="card mb-6">
			<div class="card-header">
				<h2 class="font-semibold text-gray-900 dark:text-gray-100">Time and Date</h2>
			</div>
			<div class="card-body space-y-4">
				<div class="grid md:grid-cols-2 gap-4">
					<div>
						<label for="timeTimezone" class="label">Timezone</label>
						<input id="timeTimezone" list="timezone-options" bind:value={timeTimezone} class="input" />
						<datalist id="timezone-options">
							{#each timeConfig?.available_timezones || [] as timezone}
								<option value={timezone}></option>
							{/each}
						</datalist>
					</div>
					<label class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3 self-end">
						<input type="checkbox" bind:checked={timeNtpEnabled} />
						<span class="text-sm text-gray-700 dark:text-gray-300">Use automatic time from NTP</span>
					</label>
				</div>
				<div class="grid md:grid-cols-2 gap-4">
					<div>
						<label for="manualDate" class="label">Manual Date</label>
						<input id="manualDate" type="date" bind:value={manualDate} class="input" disabled={timeNtpEnabled} />
					</div>
					<div>
						<label for="manualTime" class="label">Manual Time</label>
						<input id="manualTime" type="time" bind:value={manualTime} class="input" disabled={timeNtpEnabled} />
					</div>
				</div>
				<div class="flex items-center justify-between gap-3">
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Current system value: {timeConfig?.current_date || 'Unknown'} {timeConfig?.current_time || ''}
					</p>
					<button on:click={saveTimeConfig} class="btn-secondary" disabled={timeSaving}>
						{#if timeSaving}
							<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
						{/if}
						Save Time Settings
					</button>
				</div>
			</div>
		</div>

		<div class="card mb-6">
			<div class="card-header flex items-center justify-between gap-3">
				<div>
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Software Updates</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Current channel: <span class="font-medium text-gray-700 dark:text-gray-200">{updateStatus?.update_channel || 'Unknown'}</span>.
						Change it on <a href="/settings" class="text-primary-600 hover:underline">Settings</a>.
					</p>
				</div>
				<button on:click={refreshUpdateStatus} class="btn-secondary btn-sm" disabled={updateLoading}>
					{#if updateLoading}
						<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
					{/if}
					Refresh
				</button>
			</div>
			<div class="card-body space-y-4">
				{#if updateStatus}
					<div class="grid md:grid-cols-2 gap-4">
						<div class="rounded-lg border border-gray-200 dark:border-dark-border p-4">
							<p class="text-sm text-gray-500 dark:text-gray-400">Installed Version</p>
							<p class="font-mono text-gray-900 dark:text-gray-100">{updateStatus.installed.service_version}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-3">Git Ref</p>
							<p class="font-mono text-gray-900 dark:text-gray-100">
								{updateStatus.installed.current_tag || updateStatus.installed.current_branch}
							</p>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-3">Commit</p>
							<p class="font-mono text-gray-900 dark:text-gray-100">{updateStatus.installed.current_commit}</p>
						</div>
						<div class="rounded-lg border border-gray-200 dark:border-dark-border p-4">
							<p class="text-sm text-gray-500 dark:text-gray-400">Recommendation</p>
							<p class="text-gray-900 dark:text-gray-100 font-medium">{updateStatus.recommended.summary}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-3">Latest Stable</p>
							<p class="font-mono text-gray-900 dark:text-gray-100">{updateStatus.available.stable.tag || 'Unavailable'}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-3">Latest Prerelease</p>
							<p class="font-mono text-gray-900 dark:text-gray-100">{updateStatus.available.prerelease.tag || 'Unavailable'}</p>
						</div>
					</div>

					<div class="rounded-lg border border-gray-200 dark:border-dark-border p-4">
						<div class="grid md:grid-cols-3 gap-4">
							<div>
								<p class="text-sm text-gray-500 dark:text-gray-400">Stable Channel</p>
								<p class="text-gray-900 dark:text-gray-100">
									{updateStatus.available.stable.update_available ? 'Update available' : 'Up to date'}
								</p>
							</div>
							<div>
								<p class="text-sm text-gray-500 dark:text-gray-400">Prerelease Channel</p>
								<p class="text-gray-900 dark:text-gray-100">
									{updateStatus.available.prerelease.update_available ? 'Update available' : 'Up to date'}
								</p>
							</div>
							<div>
								<p class="text-sm text-gray-500 dark:text-gray-400">Edge Branch</p>
								<p class="text-gray-900 dark:text-gray-100">
									{updateStatus.available.edge.branch} • {updateStatus.available.edge.commits_behind} commit(s) behind
								</p>
							</div>
						</div>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-4">
							Last remote check: {updateStatus.checked_at} {updateStatus.cached ? '(cached)' : '(fresh)'}
						</p>
						{#if updateStatus.error}
							<p class="text-sm text-red-600 dark:text-red-400 mt-3">{updateStatus.error}</p>
						{/if}
					</div>

					<div class="rounded-lg border border-gray-200 dark:border-dark-border p-4 space-y-3">
						<label class="flex items-center gap-3 text-sm text-gray-700 dark:text-gray-300">
							<input type="checkbox" bind:checked={createBackup} />
							Create backup before applying update
						</label>
						<button
							on:click={applyRecommendedUpdate}
							class="btn-primary"
							disabled={
								applyingUpdate ||
								updateLoading ||
								!updateStatus.recommended.target ||
								!!updateStatus.apply_state?.running
							}
						>
							{#if applyingUpdate}
								<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
							{/if}
							Apply Recommended Update
						</button>
						<p class="text-xs text-gray-500 dark:text-gray-400">
							The updater applies the currently selected release channel. Use the main Settings page to switch between stable, prerelease, and edge.
						</p>
					</div>

					{#if updateStatus.apply_state}
						<div class="rounded-lg border border-gray-200 dark:border-dark-border p-4 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="text-sm text-gray-500 dark:text-gray-400">Updater Status</p>
									<p class="font-medium text-gray-900 dark:text-gray-100">
										{updateStatus.apply_state.status} • {updateStatus.apply_state.stage}
									</p>
								</div>
								{#if updateStatus.apply_state.running}
									<span class="text-xs font-medium text-amber-700 dark:text-amber-300">Running</span>
								{/if}
							</div>
							<p class="text-sm text-gray-700 dark:text-gray-300">{updateStatus.apply_state.message}</p>
							<div class="grid md:grid-cols-2 gap-4 text-sm">
								<div>
									<p class="text-gray-500 dark:text-gray-400">Target</p>
									<p class="font-mono text-gray-900 dark:text-gray-100">
										{updateStatus.apply_state.target || 'Automatic'}
									</p>
								</div>
								<div>
									<p class="text-gray-500 dark:text-gray-400">Updated</p>
									<p class="text-gray-900 dark:text-gray-100">{updateStatus.apply_state.updated_at || 'Unknown'}</p>
								</div>
							</div>
							{#if updateStatus.apply_state.error}
								<p class="text-sm text-red-600 dark:text-red-400">{updateStatus.apply_state.error}</p>
							{/if}
							{#if updateLog}
								<div>
									<p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Recent Updater Log</p>
									<pre class="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-x-auto max-h-80">{updateLog}</pre>
								</div>
							{/if}
						</div>
					{/if}
				{:else}
					<p class="text-gray-600 dark:text-gray-400">Software update information is unavailable.</p>
				{/if}
			</div>
		</div>

		<div class="card mb-6">
			<div class="card-header flex items-center justify-between">
				<h2 class="font-semibold text-gray-900 dark:text-gray-100">Services</h2>
				<button
					on:click={restartAllServices}
					disabled={actionLoading['all']}
					class="btn-secondary btn-sm"
				>
					{#if actionLoading['all']}
						<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
					{/if}
					Restart All
				</button>
			</div>
			<div class="divide-y divide-gray-200 dark:divide-dark-border">
				{#each services as service}
					<div class="px-6 py-4 flex items-center justify-between">
						<div class="flex items-center gap-3">
							<span
								class="w-3 h-3 rounded-full"
								class:bg-green-500={service.active}
								class:bg-red-500={!service.active}></span>
							<div>
								<p class="font-medium text-gray-900 dark:text-gray-100">{service.name}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">
									{service.status} • {service.enabled ? 'Enabled' : 'Disabled'}
								</p>
							</div>
						</div>
						<div class="flex gap-2">
							<button
								on:click={() => controlService(service.name, service.enabled ? 'disable' : 'enable')}
								disabled={actionLoading[service.name]}
								class="btn-secondary btn-sm"
							>
								{service.enabled ? 'Disable' : 'Enable'}
							</button>
							{#if service.active}
								<button
									on:click={() => controlService(service.name, 'restart')}
									disabled={actionLoading[service.name]}
									class="btn-secondary btn-sm"
								>
									Restart
								</button>
								<button
									on:click={() => controlService(service.name, 'stop')}
									disabled={actionLoading[service.name]}
									class="btn-danger btn-sm"
								>
									Stop
								</button>
							{:else}
								<button
									on:click={() => controlService(service.name, 'start')}
									disabled={actionLoading[service.name]}
									class="btn-primary btn-sm"
								>
									Start
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>

		<div class="card">
			<div class="card-header">
				<h2 class="font-semibold text-gray-900 dark:text-gray-100">System Actions</h2>
			</div>
				<div class="card-body">
					<div class="flex flex-wrap gap-4">
						<button on:click={rebootSystem} class="btn-danger">
							Reboot System
						</button>
						<button on:click={shutdownSystem} class="btn-danger">
							Shutdown System
						</button>
						<a href="/api/system/backup" class="btn-secondary">
							Download Backup
						</a>
				</div>
				<div class="mt-4 rounded-lg border border-gray-200 dark:border-dark-border p-4">
					<p class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">Restore Backup</p>
					<div class="flex flex-col md:flex-row md:items-center gap-3">
						<input type="file" accept=".tar.gz,.tgz,.gz" on:change={onRestoreFileSelected} class="input" />
						<button on:click={restoreBackup} class="btn-danger" disabled={restoring || !restoreFile}>
							{#if restoring}
								<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
							{/if}
							Restore
						</button>
					</div>
					{#if restoreFile}
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Selected: {restoreFile.name}</p>
					{/if}
				</div>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-4">
						Warning: These actions may interrupt bird detection temporarily.
					</p>
					<div class="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/60 dark:bg-red-950/30">
						<p class="text-sm font-semibold text-red-800 dark:text-red-200">Danger Zone</p>
						<p class="text-sm text-red-700 dark:text-red-300 mt-1">
							Clearing all data removes detections, recordings, and generated media.
						</p>
						<button
							on:click={clearAllData}
							class="btn-danger mt-4"
							disabled={actionLoading['clear-data']}
						>
							{#if actionLoading['clear-data']}
								<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
							{/if}
							Clear All Data
						</button>
					</div>
				</div>
			</div>
	{/if}
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="password" class="label">Password</label>
			<input
				id="password"
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
			<button type="submit" class="btn-primary">
				Log in
			</button>
		</div>
	</form>
</Modal>
