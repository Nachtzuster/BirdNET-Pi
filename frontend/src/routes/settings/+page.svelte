<script lang="ts">
	import { onMount } from 'svelte';
	import { config as configApi, type Config } from '$lib/api';
	import { auth, toasts } from '$lib/stores';
	import { Modal } from '$lib/components';

	let currentConfig: Config | null = null;
	let loading = true;
	let saving = false;
	let showLoginModal = false;
	let passwordInput = '';

	// Form fields
	let siteName = '';
	let latitude = '';
	let longitude = '';
	let databaseLang = '';
	let colorScheme = '';
	let model = '';
	let confidence = '';
	let sensitivity = '';
	let overlap = '';
	let birdweatherId = '';

	let models: { name: string; active: boolean }[] = [];
	let languages: { code: string; active: boolean }[] = [];
	let previewThreshold = 0.03;
	let previewLoading = false;
	let previewCount: number | null = null;
	let previewSpecies: string[] = [];

	async function loadConfig() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			loading = false;
			return;
		}

		loading = true;
		try {
			const [configData, modelsData, langsData] = await Promise.all([
				configApi.get(auth.getCredentials()),
				configApi.models(),
				configApi.languages(),
			]);

			currentConfig = configData;
			models = modelsData.models;
			languages = langsData.languages;

			// Populate form
			siteName = configData.site_name;
			latitude = String(configData.latitude);
			longitude = String(configData.longitude);
			databaseLang = configData.database_lang;
			colorScheme = configData.color_scheme;
			model = configData.model;
			confidence = String(configData.confidence);
			sensitivity = String(configData.sensitivity);
			overlap = String(configData.overlap);
			birdweatherId = configData.birdweather_id;
			previewThreshold = Number(configData.confidence) || 0.03;
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				toasts.show('Failed to load configuration', 'error');
			}
		} finally {
			loading = false;
		}
	}

	async function saveConfig() {
		saving = true;
		try {
			await configApi.update(
				{
					site_name: siteName,
					latitude: parseFloat(latitude),
					longitude: parseFloat(longitude),
					database_lang: databaseLang,
					color_scheme: colorScheme,
					model,
					confidence: parseFloat(confidence),
					sensitivity: parseFloat(sensitivity),
					overlap: parseFloat(overlap),
					birdweather_id: birdweatherId,
				},
				auth.getCredentials()
			);
			toasts.show('Configuration saved', 'success');
		} catch (e) {
			console.error('Failed to save config:', e);
			toasts.show('Failed to save configuration', 'error');
		} finally {
			saving = false;
		}
	}

	async function previewSpeciesList() {
		previewLoading = true;
		try {
			const result = await configApi.previewSpecies(previewThreshold);
			previewCount = result.count;
			previewSpecies = result.species;
		} catch (e) {
			console.error('Failed to preview species list:', e);
			toasts.show('Failed to preview species list', 'error');
		} finally {
			previewLoading = false;
		}
	}

	function handleLogin() {
		auth.login(passwordInput);
		showLoginModal = false;
		loadConfig();
	}

	onMount(loadConfig);
</script>

<svelte:head>
	<title>Settings - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Configure BirdNET-Pi</p>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !$auth.isAuthenticated}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400 mb-4">Please log in to access settings</p>
			<button on:click={() => showLoginModal = true} class="btn-primary">
				Log in
			</button>
		</div>
	{:else}
		<form on:submit|preventDefault={saveConfig} class="space-y-6">
			<!-- Site Settings -->
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Site Settings</h2>
				</div>
				<div class="card-body space-y-4">
					<div>
						<label for="siteName" class="label">Site Name</label>
						<input
							id="siteName"
							type="text"
							bind:value={siteName}
							class="input"
						/>
					</div>
					<div class="grid md:grid-cols-2 gap-4">
						<div>
							<label for="latitude" class="label">Latitude</label>
							<input
								id="latitude"
								type="number"
								step="0.0001"
								bind:value={latitude}
								class="input"
							/>
						</div>
						<div>
							<label for="longitude" class="label">Longitude</label>
							<input
								id="longitude"
								type="number"
								step="0.0001"
								bind:value={longitude}
								class="input"
							/>
						</div>
					</div>
				</div>
			</div>

			<!-- Display Settings -->
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Display</h2>
				</div>
				<div class="card-body space-y-4">
					<div class="grid md:grid-cols-2 gap-4">
						<div>
							<label for="language" class="label">Language</label>
							<select id="language" bind:value={databaseLang} class="select">
								{#each languages as lang}
									<option value={lang.code}>{lang.code}</option>
								{/each}
							</select>
						</div>
						<div>
							<label for="colorScheme" class="label">Color Scheme</label>
							<select id="colorScheme" bind:value={colorScheme} class="select">
								<option value="light">Light</option>
								<option value="dark">Dark</option>
							</select>
						</div>
					</div>
				</div>
			</div>

			<!-- Model Settings -->
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Analysis</h2>
				</div>
				<div class="card-body space-y-4">
					<div>
						<label for="model" class="label">Model</label>
						<select id="model" bind:value={model} class="select">
							{#each models as m}
								<option value={m.name}>{m.name}</option>
							{/each}
						</select>
					</div>
					<div class="grid md:grid-cols-3 gap-4">
						<div>
							<label for="confidence" class="label">Confidence Threshold</label>
							<input
								id="confidence"
								type="number"
								step="0.05"
								min="0"
								max="1"
								bind:value={confidence}
								class="input"
							/>
						</div>
						<div>
							<label for="sensitivity" class="label">Sensitivity</label>
							<input
								id="sensitivity"
								type="number"
								step="0.1"
								min="0.5"
								max="1.5"
								bind:value={sensitivity}
								class="input"
							/>
						</div>
						<div>
							<label for="overlap" class="label">Overlap</label>
							<input
								id="overlap"
								type="number"
								step="0.1"
								min="0"
								max="2.9"
								bind:value={overlap}
								class="input"
							/>
						</div>
					</div>
				</div>
			</div>

			<!-- Species Preview -->
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Species Preview</h2>
				</div>
				<div class="card-body space-y-4">
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Preview species list size at a threshold before applying model settings.
					</p>
					<div class="flex flex-wrap items-end gap-3">
						<div>
							<label for="previewThreshold" class="label">Threshold</label>
							<input
								id="previewThreshold"
								type="number"
								step="0.01"
								min="0"
								max="1"
								bind:value={previewThreshold}
								class="input w-36"
							/>
						</div>
						<button type="button" class="btn-secondary" on:click={previewSpeciesList} disabled={previewLoading}>
							{#if previewLoading}
								<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
							{/if}
							Preview
						</button>
					</div>
					{#if previewCount !== null}
						<p class="text-sm text-gray-700 dark:text-gray-300">Matching species: <strong>{previewCount}</strong></p>
						{#if previewSpecies.length > 0}
							<div class="max-h-44 overflow-auto rounded-lg border border-gray-200 dark:border-dark-border p-3 text-sm text-gray-700 dark:text-gray-300">
								{previewSpecies.slice(0, 50).join(', ')}
								{#if previewSpecies.length > 50}
									…
								{/if}
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<!-- Integrations -->
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Integrations</h2>
				</div>
				<div class="card-body space-y-4">
					<div>
						<label for="birdweatherId" class="label">BirdWeather Station ID</label>
						<input
							id="birdweatherId"
							type="text"
							bind:value={birdweatherId}
							placeholder="Leave empty to disable"
							class="input"
						/>
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
							Get your station ID from <a href="https://birdweather.com" target="_blank" rel="noopener" class="text-primary-600 dark:text-primary-400 hover:underline">birdweather.com</a>
						</p>
					</div>
				</div>
			</div>

			<!-- Save button -->
			<div class="flex justify-end">
				<button type="submit" disabled={saving} class="btn-primary">
					{#if saving}
						<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
					{/if}
					Save Changes
				</button>
			</div>
		</form>
	{/if}
</div>

<!-- Login Modal -->
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
			<button type="button" on:click={() => showLoginModal = false} class="btn-secondary">
				Cancel
			</button>
			<button type="submit" class="btn-primary">
				Log in
			</button>
		</div>
	</form>
</Modal>
