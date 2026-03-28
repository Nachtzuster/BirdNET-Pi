<script lang="ts">
	import { onMount } from 'svelte';
	import { system as systemApi } from '$lib/api';
	import { verifyPasswordLogin } from '$lib/auth';
	import { auth, toasts } from '$lib/stores';
	import { Modal } from '$lib/components';

	const services = [
		{ value: 'birdnet_analysis', label: 'birdnet_analysis' },
		{ value: 'birdnet_recording', label: 'birdnet_recording' },
		{ value: 'chart_viewer', label: 'chart_viewer' },
		{ value: 'spectrogram_viewer', label: 'spectrogram_viewer' },
		{ value: 'livestream', label: 'livestream' },
		{ value: 'icecast2', label: 'icecast2' },
		{ value: 'birdnet_log', label: 'birdnet_log' },
	];

	let selectedService = 'birdnet_analysis';
	let linesToFetch = 300;
	let allLines: string[] = [];
	let isPolling = true;
	let loading = true;
	let pollTimer: ReturnType<typeof setInterval> | undefined;
	let searchTerm = '';
	let inferenceOnly = true;

	let showLoginModal = false;
	let passwordInput = '';
	let logContainer: HTMLDivElement | undefined;

	$: filteredLines = allLines.filter((line) => {
		const matchesInference = !inferenceOnly || /(infer|confidence|chunk|species|score|detect|birdnet|predic)/i.test(line);
		const matchesSearch = !searchTerm || line.toLowerCase().includes(searchTerm.toLowerCase());
		return matchesInference && matchesSearch;
	});

	async function loadLogs() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			loading = false;
			return;
		}

		const shouldStickToBottom = logContainer
			? logContainer.scrollTop + logContainer.clientHeight >= logContainer.scrollHeight - 32
			: true;

		try {
			const result = await systemApi.logs(selectedService, linesToFetch, auth.getCredentials());
			allLines = result.logs.split('\n').filter(Boolean);
		} catch (error: any) {
			if (error?.status === 401) {
				auth.logout();
				showLoginModal = true;
				return;
			}
			console.error('Failed to load logs:', error);
		} finally {
			loading = false;
		}

		if (shouldStickToBottom && logContainer) {
			requestAnimationFrame(() => {
				if (logContainer) logContainer.scrollTop = logContainer.scrollHeight;
			});
		}
	}

	function restartPolling() {
		if (pollTimer) clearInterval(pollTimer);
		if (isPolling) {
			pollTimer = setInterval(() => {
				void loadLogs();
			}, 2000);
		}
	}

	function handleServiceChange() {
		void loadLogs();
	}

	async function handleLogin() {
		const result = await verifyPasswordLogin(passwordInput);
		if (!result.ok) {
			toasts.show(result.message || 'Failed to authenticate', 'error');
			return;
		}

		passwordInput = '';
		showLoginModal = false;
		toasts.show('Authenticated', 'success');
		void loadLogs();
		restartPolling();
	}

	onMount(() => {
		void loadLogs();
		restartPolling();
		return () => {
			if (pollTimer) clearInterval(pollTimer);
		};
	});

</script>

<svelte:head>
	<title>Live Logs - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Live Logs</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Real-time service logs with inference-focused filtering</p>
	</div>

	<div class="card p-4 mb-4">
		<div class="grid md:grid-cols-5 gap-3 items-end">
			<div class="md:col-span-2">
				<label for="service" class="label">Service</label>
				<select id="service" bind:value={selectedService} on:change={handleServiceChange} class="select">
					{#each services as service}
						<option value={service.value}>{service.label}</option>
					{/each}
				</select>
			</div>
			<div>
				<label for="lines" class="label">Lines</label>
				<select id="lines" bind:value={linesToFetch} on:change={handleServiceChange} class="select">
					<option value={100}>100</option>
					<option value={300}>300</option>
					<option value={500}>500</option>
					<option value={1000}>1000</option>
				</select>
			</div>
			<div>
				<label for="search" class="label">Find text</label>
				<input id="search" type="text" bind:value={searchTerm} class="input" placeholder="Filter lines..." />
			</div>
			<div class="flex gap-2">
				<button
					on:click={() => {
						isPolling = !isPolling;
						restartPolling();
						toasts.show(isPolling ? 'Live updates enabled' : 'Live updates paused', 'info', 1200);
					}}
					class="btn-secondary w-full"
				>
					{isPolling ? 'Pause' : 'Resume'}
				</button>
			</div>
		</div>
		<div class="mt-3 flex items-center gap-3 text-sm">
			<label class="flex items-center gap-2 text-gray-700 dark:text-gray-300">
				<input type="checkbox" bind:checked={inferenceOnly} />
				Inference lines only
			</label>
			<span class="text-gray-500 dark:text-gray-400">{filteredLines.length} shown</span>
		</div>
	</div>

	<div class="card p-0 overflow-hidden">
		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
			</div>
		{:else}
			<div
				bind:this={logContainer}
				class="h-[60vh] overflow-auto bg-black text-green-300 font-mono text-xs p-4 whitespace-pre-wrap"
			>
				{#if filteredLines.length === 0}
					No log lines match current filters.
				{:else}
					{#each filteredLines as line}
						<div>{line}</div>
					{/each}
				{/if}
			</div>
		{/if}
	</div>
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="logPassword" class="label">Password</label>
			<input id="logPassword" type="password" bind:value={passwordInput} class="input" placeholder="Enter password" />
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
