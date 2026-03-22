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

	let privacyThreshold = '0';
	let fullDisk: 'purge' | 'keep' = 'purge';
	let purgeThreshold = '95';
	let maxFilesSpecies = '0';
	let silenceUpdateIndicator = false;
	let automaticUpdate = false;
	let rawSpectrogram = false;
	let rareSpeciesThreshold = '30';
	let customImage = '';
	let customImageTitle = '';

	let recCard = '';
	let channels = '2';
	let recordingLength = '15';
	let extractionLength = '';
	let audiofmt = 'mp3';
	let birdnetpiUrl = '';
	let rtspStream = '';
	let rtspStreamToLivestream = '0';
	let activateFreqshiftInLivestream = false;
	let caddyPassword = '';

	let freqshiftTool: 'sox' | 'ffmpeg' = 'sox';
	let freqshiftHi = '6000';
	let freqshiftLo = '3000';
	let freqshiftReconnectDelay = '4000';
	let freqshiftPitch = '-1500';

	let logLevelBirdnetRecordingService: 'error' | 'warning' | 'info' | 'debug' = 'error';
	let logLevelLiveAudioStreamService: 'error' | 'warning' | 'info' | 'debug' = 'error';
	let logLevelSpectrogramViewerService: 'error' | 'warning' | 'info' | 'debug' = 'error';

	function populateForm(configData: Config) {
		currentConfig = configData;
		privacyThreshold = String(configData.privacy_threshold);
		fullDisk = configData.full_disk;
		purgeThreshold = String(configData.purge_threshold);
		maxFilesSpecies = String(configData.max_files_species);
		silenceUpdateIndicator = configData.silence_update_indicator;
		automaticUpdate = configData.automatic_update;
		rawSpectrogram = configData.raw_spectrogram;
		rareSpeciesThreshold = String(configData.rare_species_threshold);
		customImage = configData.custom_image;
		customImageTitle = configData.custom_image_title;

		recCard = configData.rec_card;
		channels = String(configData.channels);
		recordingLength = String(configData.recording_length);
		extractionLength = configData.extraction_length === null ? '' : String(configData.extraction_length);
		audiofmt = configData.audiofmt;
		birdnetpiUrl = configData.birdnetpi_url;
		rtspStream = configData.rtsp_stream.split(',').filter(Boolean).join('\n');
		rtspStreamToLivestream = String(configData.rtsp_stream_to_livestream);
		activateFreqshiftInLivestream = configData.activate_freqshift_in_livestream;
		caddyPassword = '';

		freqshiftTool = configData.freqshift_tool;
		freqshiftHi = String(configData.freqshift_hi);
		freqshiftLo = String(configData.freqshift_lo);
		freqshiftReconnectDelay = String(configData.freqshift_reconnect_delay);
		freqshiftPitch = String(configData.freqshift_pitch);

		logLevelBirdnetRecordingService = configData.log_level_birdnet_recording_service;
		logLevelLiveAudioStreamService = configData.log_level_live_audio_stream_service;
		logLevelSpectrogramViewerService = configData.log_level_spectrogram_viewer_service;
	}

	async function loadConfig() {
		if (!$auth.isAuthenticated) {
			showLoginModal = true;
			loading = false;
			return;
		}

		loading = true;
		try {
			const configData = await configApi.get(auth.getCredentials());
			populateForm(configData);
		} catch (e: any) {
			if (e.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to load advanced configuration:', e);
				toasts.show('Failed to load advanced configuration', 'error');
			}
		} finally {
			loading = false;
		}
	}

	async function saveConfig() {
		saving = true;
		try {
			const payload: Partial<Config> & Record<string, unknown> = {
				privacy_threshold: parseInt(privacyThreshold, 10),
				full_disk: fullDisk,
				purge_threshold: parseInt(purgeThreshold, 10),
				max_files_species: parseInt(maxFilesSpecies, 10),
				silence_update_indicator: silenceUpdateIndicator,
				automatic_update: automaticUpdate,
				raw_spectrogram: rawSpectrogram,
				rare_species_threshold: parseInt(rareSpeciesThreshold, 10),
				custom_image: customImage,
				custom_image_title: customImageTitle,
				rec_card: recCard,
				channels: parseInt(channels, 10),
				recording_length: parseInt(recordingLength, 10),
				audiofmt,
				birdnetpi_url: birdnetpiUrl,
				rtsp_stream: rtspStream
					.split('\n')
					.map((value) => value.trim())
					.filter(Boolean)
					.join(','),
				rtsp_stream_to_livestream: parseInt(rtspStreamToLivestream || '0', 10),
				activate_freqshift_in_livestream: activateFreqshiftInLivestream,
				freqshift_tool: freqshiftTool,
				freqshift_hi: parseInt(freqshiftHi, 10),
				freqshift_lo: parseInt(freqshiftLo, 10),
				freqshift_reconnect_delay: parseInt(freqshiftReconnectDelay, 10),
				freqshift_pitch: parseInt(freqshiftPitch, 10),
				log_level_birdnet_recording_service: logLevelBirdnetRecordingService,
				log_level_live_audio_stream_service: logLevelLiveAudioStreamService,
				log_level_spectrogram_viewer_service: logLevelSpectrogramViewerService,
			};

			payload.extraction_length =
				extractionLength.trim() === '' ? null : parseInt(extractionLength, 10);
			if (caddyPassword.trim() !== '') {
				payload.caddy_password = caddyPassword;
			}

			const result = await configApi.update(payload, auth.getCredentials());
			toasts.show(result.message, 'success');
			await loadConfig();
		} catch (e: any) {
			console.error('Failed to save advanced settings:', e);
			toasts.show(e?.message || 'Failed to save advanced settings', 'error');
		} finally {
			saving = false;
		}
	}

	function handleLogin() {
		auth.login(passwordInput);
		passwordInput = '';
		showLoginModal = false;
		loadConfig();
	}

	onMount(loadConfig);
</script>

<svelte:head>
	<title>Advanced Settings - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex flex-wrap items-center justify-between gap-3">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Advanced Settings</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">Operational, capture, stream, accessibility, and logging controls</p>
		</div>
		<a href="/settings" class="btn-secondary">Back to Settings</a>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !$auth.isAuthenticated}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400 mb-4">Please log in to access advanced settings</p>
			<button on:click={() => (showLoginModal = true)} class="btn-primary">Log in</button>
		</div>
	{:else}
		<form on:submit|preventDefault={saveConfig} class="space-y-6">
			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Operations</h2>
				</div>
				<div class="card-body grid gap-4 md:grid-cols-2">
					<div>
						<label for="privacyThreshold" class="label">Privacy Threshold</label>
						<input id="privacyThreshold" type="range" min="0" max="3" bind:value={privacyThreshold} class="w-full" />
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Current value: {privacyThreshold}%</p>
					</div>
					<div>
						<label for="fullDisk" class="label">Disk Full Behavior</label>
						<select id="fullDisk" bind:value={fullDisk} class="select">
							<option value="purge">Purge old files</option>
							<option value="keep">Stop services and keep data</option>
						</select>
					</div>
					<div>
						<label for="purgeThreshold" class="label">Purge Threshold (%)</label>
						<input id="purgeThreshold" type="number" min="20" max="99" bind:value={purgeThreshold} class="input" />
					</div>
					<div>
						<label for="maxFilesSpecies" class="label">Max Files Per Species</label>
						<input id="maxFilesSpecies" type="number" min="0" bind:value={maxFilesSpecies} class="input" />
					</div>
					<div>
						<label for="rareSpeciesThreshold" class="label">Rare Species Threshold (days)</label>
						<input id="rareSpeciesThreshold" type="number" min="1" bind:value={rareSpeciesThreshold} class="input" />
					</div>
					<div class="space-y-3">
						<label class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={silenceUpdateIndicator} />
							<span class="text-sm text-gray-700 dark:text-gray-300">Silence update indicator</span>
						</label>
						<label class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={automaticUpdate} />
							<span class="text-sm text-gray-700 dark:text-gray-300">Automatic weekly update</span>
						</label>
						<label class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={rawSpectrogram} />
							<span class="text-sm text-gray-700 dark:text-gray-300">Minimalist spectrograms</span>
						</label>
					</div>
					<div class="md:col-span-2 grid gap-4 md:grid-cols-2">
						<div>
							<label for="customImage" class="label">Custom Image Path</label>
							<input id="customImage" type="text" bind:value={customImage} class="input" />
						</div>
						<div>
							<label for="customImageTitle" class="label">Custom Image Label</label>
							<input id="customImageTitle" type="text" bind:value={customImageTitle} class="input" />
						</div>
					</div>
				</div>
			</div>

			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Capture and Stream</h2>
				</div>
				<div class="card-body grid gap-4 md:grid-cols-2">
					<div>
						<label for="recCard" class="label">Audio Card</label>
						<input id="recCard" type="text" bind:value={recCard} class="input" />
					</div>
					<div>
						<label for="channels" class="label">Audio Channels</label>
						<input id="channels" type="number" min="1" max="32" bind:value={channels} class="input" />
					</div>
					<div>
						<label for="recordingLength" class="label">Recording Length (seconds)</label>
						<input id="recordingLength" type="number" min="3" max="60" bind:value={recordingLength} class="input" />
					</div>
					<div>
						<label for="extractionLength" class="label">Extraction Length (seconds)</label>
						<input id="extractionLength" type="number" min="3" max="60" bind:value={extractionLength} class="input" placeholder="Leave blank to keep default" />
					</div>
					<div>
						<label for="audiofmt" class="label">Extraction Audio Format</label>
						<input id="audiofmt" type="text" bind:value={audiofmt} class="input" />
					</div>
					<div>
						<label for="birdnetpiUrl" class="label">BirdNET-Pi URL</label>
						<input id="birdnetpiUrl" type="url" bind:value={birdnetpiUrl} class="input" placeholder="https://birds.example.com" />
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
							Set this only when BirdNET-Pi is serving the public hostname directly. Leave it blank when using Cloudflare Tunnel or another proxy/tunnel that already handles TLS and redirects.
						</p>
					</div>
					<div class="md:col-span-2">
						<label for="rtspStream" class="label">RTSP Streams</label>
						<textarea
							id="rtspStream"
							bind:value={rtspStream}
							class="input min-h-[120px] font-mono text-sm"
							placeholder="One RTSP URL per line"></textarea>
					</div>
					<div>
						<label for="rtspStreamToLivestream" class="label">RTSP Stream Index for Livestream</label>
						<input id="rtspStreamToLivestream" type="number" min="0" bind:value={rtspStreamToLivestream} class="input" />
					</div>
					<div class="space-y-3">
						<label class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
							<input type="checkbox" bind:checked={activateFreqshiftInLivestream} />
							<span class="text-sm text-gray-700 dark:text-gray-300">Enable frequency shift in livestream</span>
						</label>
					</div>
					<div class="md:col-span-2">
						<label for="caddyPassword" class="label">BirdNET-Pi Password</label>
						<input
							id="caddyPassword"
							type="password"
							bind:value={caddyPassword}
							class="input"
							placeholder={currentConfig?.password_configured ? 'Leave blank to keep current password' : 'Set a password'} />
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Use only if you want to change the current password.</p>
					</div>
				</div>
			</div>

			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Accessibility</h2>
				</div>
				<div class="card-body grid gap-4 md:grid-cols-2">
					<div>
						<label for="freqshiftTool" class="label">Frequency Shift Tool</label>
						<select id="freqshiftTool" bind:value={freqshiftTool} class="select">
							<option value="sox">sox</option>
							<option value="ffmpeg">ffmpeg</option>
						</select>
					</div>
					<div>
						<label for="freqshiftReconnectDelay" class="label">Livestream Reconnect Delay (ms)</label>
						<input id="freqshiftReconnectDelay" type="number" min="1000" max="10000" bind:value={freqshiftReconnectDelay} class="input" />
					</div>
					<div>
						<label for="freqshiftHi" class="label">Origin Frequency (Hz)</label>
						<input id="freqshiftHi" type="number" min="0" max="20000" bind:value={freqshiftHi} class="input" />
					</div>
					<div>
						<label for="freqshiftLo" class="label">Target Frequency (Hz)</label>
						<input id="freqshiftLo" type="number" min="0" max="20000" bind:value={freqshiftLo} class="input" />
					</div>
					<div class="md:col-span-2">
						<label for="freqshiftPitch" class="label">Pitch Shift (100ths of a semitone)</label>
						<input id="freqshiftPitch" type="number" min="-4000" max="4000" bind:value={freqshiftPitch} class="input" />
					</div>
				</div>
			</div>

			<div class="card">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Logging</h2>
				</div>
				<div class="card-body grid gap-4 md:grid-cols-3">
					<div>
						<label for="logBirdnetRecording" class="label">BirdNET Recording</label>
						<select id="logBirdnetRecording" bind:value={logLevelBirdnetRecordingService} class="select">
							<option value="error">Errors only</option>
							<option value="warning">Warning</option>
							<option value="info">Info</option>
							<option value="debug">Debug</option>
						</select>
					</div>
					<div>
						<label for="logLiveAudio" class="label">Live Audio Stream</label>
						<select id="logLiveAudio" bind:value={logLevelLiveAudioStreamService} class="select">
							<option value="error">Errors only</option>
							<option value="warning">Warning</option>
							<option value="info">Info</option>
							<option value="debug">Debug</option>
						</select>
					</div>
					<div>
						<label for="logSpectrogram" class="label">Spectrogram Viewer</label>
						<select id="logSpectrogram" bind:value={logLevelSpectrogramViewerService} class="select">
							<option value="error">Errors only</option>
							<option value="warning">Warning</option>
							<option value="info">Info</option>
							<option value="debug">Debug</option>
						</select>
					</div>
				</div>
			</div>

			<div class="flex justify-end">
				<button type="submit" disabled={saving} class="btn-primary">
					{#if saving}
						<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
					{/if}
					Save Advanced Settings
				</button>
			</div>
		</form>
	{/if}
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="advancedPassword" class="label">Password</label>
			<input
				id="advancedPassword"
				type="password"
				bind:value={passwordInput}
				class="input"
				placeholder="Enter password"
			/>
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
