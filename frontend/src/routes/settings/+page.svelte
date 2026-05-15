<script lang="ts">
	import { onMount } from 'svelte';
	import { config as configApi, type Config } from '$lib/api';
	import { verifyPasswordLogin } from '$lib/auth';
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
	let updateChannel: 'stable' | 'prerelease' | 'edge' = 'stable';
	let model = '';
	let dataModelVersion = '1';
	let confidence = '';
	let sensitivity = '';
	let overlap = '';
	let birdweatherId = '';
	let infoSite: 'ALLABOUTBIRDS' | 'EBIRD' = 'ALLABOUTBIRDS';
	let imageProvider = '';
	let flickrApiKey = '';
	let flickrFilterEmail = '';
	let appriseConfig = '';
	let appriseNotificationTitle = '';
	let appriseNotificationBody = '';
	let appriseNotifyEachDetection = false;
	let appriseNotifyNewSpecies = false;
	let appriseNotifyNewSpeciesEachDay = false;
	let appriseWeeklyReport = false;
	let appriseMinSeconds = '';
	let appriseOnlyNotifySpeciesNames = '';
	let appriseOnlyNotifySpeciesNames2 = '';
	let testingNotification = false;

	let models: { name: string; active: boolean; supports_species_filter: boolean }[] = [];
	let languages: { code: string; active: boolean }[] = [];
	let previewThreshold = 0.03;
	let previewLoading = false;
	let previewCount: number | null = null;
	let previewSpecies: string[] = [];
	let modelSupportsSpeciesFilter = false;

	$: modelSupportsSpeciesFilter = models.find((candidate) => candidate.name === model)?.supports_species_filter ?? false;
	$: if (!modelSupportsSpeciesFilter) {
		previewCount = null;
		previewSpecies = [];
	}

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
			updateChannel = configData.update_channel;
			model = configData.model;
			dataModelVersion = String(configData.data_model_version);
			confidence = String(configData.confidence);
			sensitivity = String(configData.sensitivity);
			overlap = String(configData.overlap);
			birdweatherId = configData.birdweather_id;
			infoSite = configData.info_site;
			imageProvider = (configData.image_provider || '').toLowerCase();
			flickrApiKey = '';
			flickrFilterEmail = configData.flickr_filter_email;
			previewThreshold = configData.sf_thresh;
			appriseConfig = configData.apprise_config;
			appriseNotificationTitle = configData.apprise_notification_title;
			appriseNotificationBody = configData.apprise_notification_body;
			appriseNotifyEachDetection = configData.apprise_notify_each_detection;
			appriseNotifyNewSpecies = configData.apprise_notify_new_species;
			appriseNotifyNewSpeciesEachDay = configData.apprise_notify_new_species_each_day;
			appriseWeeklyReport = configData.apprise_weekly_report;
			appriseMinSeconds = String(configData.apprise_minimum_seconds_between_notifications_per_species);
			appriseOnlyNotifySpeciesNames = configData.apprise_only_notify_species_names;
			appriseOnlyNotifySpeciesNames2 = configData.apprise_only_notify_species_names_2;
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
			const payload: Partial<Config> & Record<string, unknown> = {
				site_name: siteName,
				latitude: parseFloat(latitude),
				longitude: parseFloat(longitude),
				database_lang: databaseLang,
				color_scheme: colorScheme,
				update_channel: updateChannel,
				info_site: infoSite,
				model,
				sf_thresh: Number(previewThreshold),
				data_model_version: parseInt(dataModelVersion, 10),
				confidence: parseFloat(confidence),
				sensitivity: parseFloat(sensitivity),
				overlap: parseFloat(overlap),
				birdweather_id: birdweatherId,
				image_provider: imageProvider,
				flickr_filter_email: flickrFilterEmail,
				apprise_config: appriseConfig,
				apprise_notification_title: appriseNotificationTitle,
				apprise_notification_body: appriseNotificationBody,
				apprise_notify_each_detection: appriseNotifyEachDetection,
				apprise_notify_new_species: appriseNotifyNewSpecies,
				apprise_notify_new_species_each_day: appriseNotifyNewSpeciesEachDay,
				apprise_weekly_report: appriseWeeklyReport,
				apprise_minimum_seconds_between_notifications_per_species: parseInt(appriseMinSeconds || '0', 10),
				apprise_only_notify_species_names: appriseOnlyNotifySpeciesNames,
				apprise_only_notify_species_names_2: appriseOnlyNotifySpeciesNames2,
			};
			if (flickrApiKey.trim() !== '') {
				payload.flickr_api_key = flickrApiKey;
			}
			const result = await configApi.update(
				payload,
				auth.getCredentials()
			);
			toasts.show(result.message, 'success');
			await loadConfig();
		} catch (e) {
			console.error('Failed to save config:', e);
			toasts.show('Failed to save configuration', 'error');
		} finally {
			saving = false;
		}
	}

	async function previewSpeciesList() {
		if (!modelSupportsSpeciesFilter) {
			return;
		}

		previewLoading = true;
		try {
			const result = await configApi.previewSpecies(Number(previewThreshold), model, parseInt(dataModelVersion, 10));
			previewCount = result.count;
			previewSpecies = result.species;
		} catch (e) {
			console.error('Failed to preview species list:', e);
			toasts.show('Failed to preview species list', 'error');
		} finally {
			previewLoading = false;
		}
	}

	async function sendTestNotification() {
		testingNotification = true;
		try {
			const result = await configApi.testNotification(
				{
					title: appriseNotificationTitle,
					body: appriseNotificationBody,
					config: appriseConfig,
				},
				auth.getCredentials()
			);
			toasts.show(result.message, result.success ? 'success' : 'error');
		} catch (e) {
			console.error('Failed to send test notification:', e);
			toasts.show('Failed to send test notification', 'error');
		} finally {
			testingNotification = false;
		}
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
		await loadConfig();
	}

	onMount(loadConfig);
</script>

<svelte:head>
	<title>Settings - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">Configure BirdNET-Pi</p>
		</div>
		<a href="/settings/advanced" class="btn-secondary">Advanced Settings</a>
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

			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Software Updates</h2>
				</div>
				<div class="card-body space-y-4">
					<div>
						<label for="updateChannel" class="label">Release Channel</label>
						<select id="updateChannel" bind:value={updateChannel} class="select">
							<option value="stable">Stable</option>
							<option value="prerelease">Pre-release</option>
							<option value="edge">Edge</option>
						</select>
					</div>
					<div class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
						Stable is the safest default. Pre-release may include release candidates, and Edge is intended for latest branch builds where breakage risk is higher.
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
						{#if modelSupportsSpeciesFilter}
							<div class="grid md:grid-cols-2 gap-4">
								<div>
									<label for="dataModelVersion" class="label">Species Range Model</label>
									<select id="dataModelVersion" bind:value={dataModelVersion} class="select">
										<option value="1">Version 1</option>
										<option value="2">Version 2</option>
									</select>
								</div>
							</div>
						{:else}
							<p class="text-sm text-gray-600 dark:text-gray-400">
								This model does not use the species range filter settings from the legacy interface.
							</p>
						{/if}
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
						{#if modelSupportsSpeciesFilter}
							<p class="text-sm text-gray-600 dark:text-gray-400">
								Preview species list size at the current occurrence threshold before saving.
							</p>
							<div class="flex flex-wrap items-end gap-3">
								<div class="min-w-[14rem]">
									<label for="previewThreshold" class="label">Occurrence Threshold</label>
									<input
										id="previewThreshold"
										type="number"
										step="0.0005"
										min="0.0005"
										max="0.99"
										bind:value={previewThreshold}
										class="input"
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
						{:else}
							<p class="text-sm text-gray-600 dark:text-gray-400">
								Species preview is only available for models that support range-based filtering.
							</p>
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
					<div class="grid md:grid-cols-2 gap-4">
						<div>
							<label for="imageProvider" class="label">Bird Photo Source</label>
							<select id="imageProvider" bind:value={imageProvider} class="select">
								<option value="">None</option>
								<option value="wikipedia">Wikipedia</option>
								<option value="flickr">Flickr</option>
							</select>
						</div>
						<div>
							<label for="infoSite" class="label">Species Info Source</label>
							<select id="infoSite" bind:value={infoSite} class="select">
								<option value="ALLABOUTBIRDS">allaboutbirds.org</option>
								<option value="EBIRD">ebird.org</option>
							</select>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								All About Birds is the default. eBird tends to have better coverage for some non-US species.
							</p>
						</div>
					</div>
					<div class="grid md:grid-cols-2 gap-4">
						<div>
							<label for="flickrApiKey" class="label">Flickr API Key</label>
							<input
								id="flickrApiKey"
								type="password"
								bind:value={flickrApiKey}
								class="input"
								placeholder={currentConfig?.has_flickr_key ? 'Leave blank to keep current key' : 'Enter Flickr API key'}
							/>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								Required only when using Flickr for bird images.
							</p>
						</div>
						<div>
							<label for="flickrFilterEmail" class="label">Preferred Flickr User Email</label>
							<input
								id="flickrFilterEmail"
								type="email"
								bind:value={flickrFilterEmail}
								class="input"
								placeholder="myflickraccount@gmail.com"
							/>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								Optional. Restricts Flickr image search to a preferred user account.
							</p>
						</div>
					</div>
				</div>
			</div>

			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Notifications</h2>
				</div>
				<div class="card-body space-y-4">
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Configure Apprise targets and choose which bird events generate alerts.
					</p>
					<div>
						<label for="appriseConfig" class="label">Apprise Configuration</label>
						<textarea
							id="appriseConfig"
							bind:value={appriseConfig}
							class="input min-h-[140px] font-mono text-sm"
							placeholder={`mailto://user:password@gmail.com\ntgram://bot_token/chat_id\nhttps://discordapp.com/api/webhooks/...`}></textarea>
					</div>
					<div>
						<label for="appriseTitle" class="label">Notification Title</label>
						<input id="appriseTitle" type="text" bind:value={appriseNotificationTitle} class="input" />
					</div>
					<div>
						<label for="appriseBody" class="label">Notification Body</label>
						<textarea
							id="appriseBody"
							bind:value={appriseNotificationBody}
							class="input min-h-[120px]"
							placeholder="$comname was detected with confidence $confidencepct"></textarea>
					</div>
					<div class="grid md:grid-cols-2 gap-4">
						<label class="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={appriseNotifyEachDetection} class="mt-1" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Notify on every detection</span>
						</label>
						<label class="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={appriseNotifyNewSpecies} class="mt-1" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Notify on infrequent species detections</span>
						</label>
						<label class="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={appriseNotifyNewSpeciesEachDay} class="mt-1" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Notify on first detection of each day</span>
						</label>
						<label class="flex items-start gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={appriseWeeklyReport} class="mt-1" />
							<span class="text-sm text-gray-700 dark:text-gray-300">
								Send weekly report notifications
								<a href="/reports/weekly" class="ml-1 text-primary-600 dark:text-primary-400 hover:underline">View report</a>
							</span>
						</label>
					</div>
					<div class="grid md:grid-cols-3 gap-4">
						<div>
							<label for="appriseMinSeconds" class="label">Minimum Seconds Between Species Alerts</label>
							<input id="appriseMinSeconds" type="number" min="0" bind:value={appriseMinSeconds} class="input" />
						</div>
						<div class="md:col-span-2">
							<label for="appriseExcludeSpecies" class="label">Exclude Species Names</label>
							<input
								id="appriseExcludeSpecies"
								type="text"
								bind:value={appriseOnlyNotifySpeciesNames}
								class="input"
								placeholder="Mourning Dove,American Crow" />
						</div>
					</div>
					<div>
						<label for="appriseIncludeSpecies" class="label">Only Notify For These Species</label>
						<input
							id="appriseIncludeSpecies"
							type="text"
							bind:value={appriseOnlyNotifySpeciesNames2}
							class="input"
							placeholder="Northern Cardinal,Carolina Chickadee" />
					</div>
					<div class="flex justify-end">
						<button type="button" class="btn-secondary" on:click={sendTestNotification} disabled={testingNotification}>
							{#if testingNotification}
								<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
							{/if}
							Send Test Notification
						</button>
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
