<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, integrations, media, type SpeciesExternalLinks } from '$lib/api';
	import { verifyPasswordLogin } from '$lib/auth';
	import { AudioPlayer, ExternalLinks, Modal } from '$lib/components';
	import { auth, toasts } from '$lib/stores';
	import { formatBirdName } from '$lib';

	let dates: string[] = [];
	let selectedDate = '';
	let speciesForDate: { name: string; count: number }[] = [];
	let selectedSpecies = '';
	let files: { name: string; has_spectrogram: boolean; size: number }[] = [];
	let loading = false;
	let queryDate = '';
	let querySpecies = '';
	let querySci = '';
	let queryCom = '';
	let deletingFiles = new Set<string>();
	let shiftingFiles = new Set<string>();
	let deletingShiftedFiles = new Set<string>();
	let shiftedAvailable: Record<string, boolean> = {};
	let shiftedChecked: Record<string, boolean> = {};
	let showShifted = false;
	let speciesLinks: SpeciesExternalLinks | null = null;
	let showLoginModal = false;
	let passwordInput = '';
	let expandedSpectrogramFiles = new Set<string>();
	let postLoginRedirect: string | null = null;

	async function loadDates() {
		try {
			const result = await media.dates();
			dates = result.dates;
			if (dates.length > 0) {
				selectedDate = queryDate && dates.includes(queryDate) ? queryDate : dates[0];
				await loadSpecies(!!querySpecies);

				if (querySpecies && speciesForDate.some((sp) => sp.name === querySpecies)) {
					selectedSpecies = querySpecies;
					await loadFiles();
				}
			}
		} catch (e) {
			console.error('Failed to load dates:', e);
			toasts.show('Failed to load dates', 'error');
		}
	}

	async function loadSpecies(preserveSelection = false) {
		if (!selectedDate) return;
		
		loading = true;
		try {
			const result = await media.speciesForDate(selectedDate);
			speciesForDate = result.species;
			if (!preserveSelection) selectedSpecies = '';
			files = [];
		} catch (e) {
			console.error('Failed to load species:', e);
			speciesForDate = [];
		} finally {
			loading = false;
		}
	}

	async function loadFiles() {
		if (!selectedDate || !selectedSpecies) return;
		
		loading = true;
		try {
			const result = await media.filesForSpecies(selectedDate, selectedSpecies);
			files = result.files;
			shiftedAvailable = {};
			shiftedChecked = {};
			await loadSpeciesLinks();
			if (showShifted) await probeShiftedForAll();
		} catch (e) {
			console.error('Failed to load files:', e);
			files = [];
		} finally {
			loading = false;
		}
	}

	async function loadSpeciesLinks() {
		try {
			if (querySci && selectedSpecies === querySpecies) {
				speciesLinks = await integrations.speciesLinks(querySci, queryCom || undefined);
				return;
			}
			const meta = await media.speciesMeta(selectedDate, selectedSpecies);
			speciesLinks = await integrations.speciesLinks(meta.sci_name, meta.com_name);
		} catch {
			speciesLinks = null;
		}
	}

	function handleDateChange() {
		void loadSpecies();
	}

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function requireAuth(redirectTo: string | null = null): Promise<boolean> {
		if ($auth.isAuthenticated) {
			postLoginRedirect = null;
			return true;
		}
		postLoginRedirect = redirectTo;
		showLoginModal = true;
		return false;
	}

	async function openFileManager() {
		if (!(await requireAuth('/files'))) return;
		window.location.href = '/files';
	}

	async function deleteFile(fileName: string) {
		if (!(await requireAuth())) return;
		if (!confirm(`Delete recording file ${fileName}?`)) return;

		deletingFiles = new Set(deletingFiles).add(fileName);
		try {
			await detections.delete(fileName, auth.getCredentials());
			files = files.filter((f) => f.name !== fileName);
			speciesForDate = speciesForDate
				.map((sp) => (sp.name === selectedSpecies ? { ...sp, count: Math.max(0, sp.count - 1) } : sp))
				.filter((sp) => sp.count > 0);
			toasts.show('Recording deleted', 'success');
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to delete recording:', e);
				toasts.show('Failed to delete recording', 'error');
			}
		} finally {
			const next = new Set(deletingFiles);
			next.delete(fileName);
			deletingFiles = next;
		}
	}

	async function createShifted(fileName: string) {
		if (!(await requireAuth())) return;

		shiftingFiles = new Set(shiftingFiles).add(fileName);
		try {
			await media.createShifted(selectedDate, selectedSpecies, fileName, auth.getCredentials());
			shiftedAvailable = { ...shiftedAvailable, [fileName]: true };
			toasts.show('Shifted audio created', 'success');
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to create shifted audio:', e);
				toasts.show('Failed to create shifted audio', 'error');
			}
		} finally {
			const next = new Set(shiftingFiles);
			next.delete(fileName);
			shiftingFiles = next;
		}
	}

	async function deleteShifted(fileName: string) {
		if (!(await requireAuth())) return;

		deletingShiftedFiles = new Set(deletingShiftedFiles).add(fileName);
		try {
			await media.deleteShifted(selectedDate, selectedSpecies, fileName, auth.getCredentials());
			shiftedAvailable = { ...shiftedAvailable, [fileName]: false };
			toasts.show('Shifted audio removed', 'success');
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to delete shifted audio:', e);
				toasts.show('Failed to remove shifted audio', 'error');
			}
		} finally {
			const next = new Set(deletingShiftedFiles);
			next.delete(fileName);
			deletingShiftedFiles = next;
		}
	}

	async function probeShifted(fileName: string) {
		if (shiftedChecked[fileName]) return;
		const url = media.shiftedAudioUrl(selectedDate, selectedSpecies, fileName);
		try {
			const response = await fetch(url, { method: 'HEAD' });
			shiftedAvailable = { ...shiftedAvailable, [fileName]: response.ok };
		} catch {
			shiftedAvailable = { ...shiftedAvailable, [fileName]: false };
		} finally {
			shiftedChecked = { ...shiftedChecked, [fileName]: true };
		}
	}

	async function probeShiftedForAll() {
		await Promise.all(files.map((file) => probeShifted(file.name)));
	}

	async function handleShowShiftedToggle() {
		showShifted = !showShifted;
		if (showShifted) {
			await probeShiftedForAll();
		}
	}

	function toggleSpectrogram(fileName: string) {
		const next = new Set(expandedSpectrogramFiles);
		if (next.has(fileName)) {
			next.delete(fileName);
		} else {
			next.add(fileName);
		}
		expandedSpectrogramFiles = next;
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

		if (postLoginRedirect) {
			const destination = postLoginRedirect;
			postLoginRedirect = null;
			window.location.href = destination;
		}
	}

	function cancelLogin() {
		passwordInput = '';
		postLoginRedirect = null;
		showLoginModal = false;
	}

	onMount(() => {
		const query = new URLSearchParams(window.location.search);
		queryDate = query.get('date') || '';
		querySpecies = query.get('species') || '';
		querySci = query.get('sci') || '';
		queryCom = query.get('com') || '';
		void loadDates();
	});
</script>

<svelte:head>
	<title>Library - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Library</h1>
				<p class="mt-1 text-gray-600 dark:text-gray-400">Historical file management</p>
			</div>
			<button type="button" class="btn-secondary" on:click={openFileManager}>Open File Manager</button>
		</div>
	</div>

	<!-- Filters -->
	<div class="card p-4 mb-6">
		<div class="grid md:grid-cols-2 gap-4">
			<!-- Date selector -->
			<div>
				<label for="date" class="label">Date</label>
				<select
					id="date"
					bind:value={selectedDate}
					on:change={handleDateChange}
					class="select"
				>
					{#each dates as date}
						<option value={date}>{date}</option>
					{/each}
				</select>
			</div>

			<!-- Species selector -->
			<div>
				<label for="species" class="label">Species</label>
				<select
					id="species"
					bind:value={selectedSpecies}
					on:change={loadFiles}
					class="select"
					disabled={speciesForDate.length === 0}
				>
					<option value="">Select a species...</option>
					{#each speciesForDate as sp}
						<option value={sp.name}>{formatBirdName(sp.name)} ({sp.count})</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<!-- Species summary for selected date -->
	{#if selectedDate && !selectedSpecies}
		<div class="mb-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				Species for {selectedDate}
			</h2>
			{#if speciesForDate.length === 0}
				<div class="card p-8 text-center">
					<p class="text-gray-600 dark:text-gray-400">No recordings for this date</p>
				</div>
			{:else}
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
					{#each speciesForDate as sp}
						<button
							on:click={() => { selectedSpecies = sp.name; loadFiles(); }}
							class="card p-4 text-left hover:shadow-lg transition-shadow"
						>
							<p class="font-medium text-gray-900 dark:text-gray-100 truncate">{formatBirdName(sp.name)}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400">{sp.count} files</p>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- Files list -->
	{#if selectedSpecies}
		<div>
			<div class="flex items-center justify-between mb-4">
				<div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{formatBirdName(selectedSpecies)} - {selectedDate}
					</h2>
					<div class="mt-1">
						<ExternalLinks links={speciesLinks} compact={true} />
					</div>
				</div>
				<div class="flex items-center gap-3">
					<label class="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
						<input type="checkbox" checked={showShifted} on:change={handleShowShiftedToggle} />
						<span>Show shifted</span>
					</label>
				<button
					on:click={() => { selectedSpecies = ''; files = []; }}
					class="text-sm text-primary-600 dark:text-primary-400 hover:underline"
				>
					← Back to species
				</button>
				</div>
			</div>

			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if files.length === 0}
				<div class="card p-8 text-center">
					<p class="text-gray-600 dark:text-gray-400">No files found</p>
				</div>
			{:else}
				<div class="space-y-4">
					{#each files as file}
						{@const audioUrl = media.audioUrl(selectedDate, selectedSpecies, file.name)}
						{@const spectrogramUrl = media.spectrogramUrl(selectedDate, selectedSpecies, file.name)}
						{@const shiftedUrl = media.shiftedAudioUrl(selectedDate, selectedSpecies, file.name)}
						{@const temporalZoomUrls = {
							'0.85': media.temporalZoomAudioUrl(selectedDate, selectedSpecies, file.name, 0.85),
							'0.7': media.temporalZoomAudioUrl(selectedDate, selectedSpecies, file.name, 0.7),
							'0.6': media.temporalZoomAudioUrl(selectedDate, selectedSpecies, file.name, 0.6),
							'0.5': media.temporalZoomAudioUrl(selectedDate, selectedSpecies, file.name, 0.5),
						}}
						{@const temporalZoomPrepareUrls = {
							'0.85': media.temporalZoomPrepareUrl(selectedDate, selectedSpecies, file.name, 0.85),
							'0.7': media.temporalZoomPrepareUrl(selectedDate, selectedSpecies, file.name, 0.7),
							'0.6': media.temporalZoomPrepareUrl(selectedDate, selectedSpecies, file.name, 0.6),
							'0.5': media.temporalZoomPrepareUrl(selectedDate, selectedSpecies, file.name, 0.5),
						}}
						{@const spectrogramExpanded = expandedSpectrogramFiles.has(file.name)}
						<div class="card p-4">
							<div class="flex items-start gap-4">
								<!-- Spectrogram thumbnail -->
								{#if file.has_spectrogram && !spectrogramExpanded}
									<button
										type="button"
										class="group relative block w-32 h-20 flex-shrink-0 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-dark-card"
										on:click={() => toggleSpectrogram(file.name)}
										aria-expanded={spectrogramExpanded}
										aria-label={`Expand spectrogram for ${file.name}`}
										title="Expand spectrogram"
									>
										<img
											src={spectrogramUrl}
											alt="Spectrogram"
											class="w-32 h-20 object-cover rounded-lg bg-gray-200 dark:bg-dark-border"
											loading="lazy"
										/>
										<span class="absolute right-1.5 top-1.5 inline-flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-gray-700 shadow-sm ring-1 ring-gray-200 backdrop-blur transition-colors group-hover:bg-white dark:bg-gray-900/85 dark:text-gray-200 dark:ring-gray-700 dark:group-hover:bg-gray-900">
											<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
												<path fill-rule="evenodd" d="M5.22 7.47a.75.75 0 0 1 1.06 0L10 11.19l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 8.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
											</svg>
										</span>
									</button>
								{:else if file.has_spectrogram}
									<div class="w-32 h-20 flex-shrink-0"></div>
								{:else}
									<div class="w-32 h-20 bg-gray-200 dark:bg-dark-border rounded-lg flex items-center justify-center flex-shrink-0">
										<span class="text-xs text-gray-500">No spectrogram</span>
									</div>
								{/if}

								<!-- File info -->
									<div class="flex-1 min-w-0">
										<div class="flex items-center justify-between gap-2">
											<p class="font-medium text-gray-900 dark:text-gray-100 truncate">{file.name}</p>
											<div class="flex items-center gap-2">
												{#if shiftedAvailable[file.name]}
													<button
														class="btn-secondary btn-sm"
														on:click={() => deleteShifted(file.name)}
														disabled={deletingShiftedFiles.has(file.name)}
													>
														{deletingShiftedFiles.has(file.name) ? '...' : 'Unshift'}
													</button>
												{:else}
													<button
														class="btn-secondary btn-sm"
														on:click={() => createShifted(file.name)}
														disabled={shiftingFiles.has(file.name)}
													>
														{shiftingFiles.has(file.name) ? '...' : 'Shift'}
													</button>
												{/if}
												<button
													class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
													on:click={() => deleteFile(file.name)}
													disabled={deletingFiles.has(file.name)}
													title="Delete recording"
													aria-label="Delete recording"
												>
													{#if deletingFiles.has(file.name)}
														<span class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
													{:else}
														<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
															<path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M8 6V4h8v2m-9 0 1 14h8l1-14" />
														</svg>
													{/if}
												</button>
											</div>
										</div>
										<p class="text-sm text-gray-500 dark:text-gray-400">{formatSize(file.size)}</p>
										<div class="mt-2">
											<AudioPlayer
												src={audioUrl}
												compact
												temporalZoomProminent={spectrogramExpanded}
												{temporalZoomUrls}
												{temporalZoomPrepareUrls}
											/>
										</div>
										{#if showShifted && shiftedAvailable[file.name]}
											<div class="mt-2">
												<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Shifted</p>
												<AudioPlayer src={shiftedUrl} compact />
											</div>
										{/if}
									</div>
							</div>
							{#if file.has_spectrogram && spectrogramExpanded}
								<button
									type="button"
									class="group relative mt-4 block w-full rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-dark-card"
									on:click={() => toggleSpectrogram(file.name)}
									aria-expanded={spectrogramExpanded}
									aria-label={`Collapse spectrogram for ${file.name}`}
									title="Collapse spectrogram"
								>
									<img
										src={spectrogramUrl}
										alt="Spectrogram"
										class="block w-full h-[68vh] md:h-[72vh] object-contain rounded-lg bg-gray-100 dark:bg-dark-border p-2"
										loading="lazy"
									/>
									<span class="absolute right-2 top-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-gray-700 shadow-sm ring-1 ring-gray-200 backdrop-blur transition-colors group-hover:bg-white dark:bg-gray-900/85 dark:text-gray-200 dark:ring-gray-700 dark:group-hover:bg-gray-900">
										<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
											<path fill-rule="evenodd" d="M14.78 12.53a.75.75 0 0 1-1.06 0L10 8.81l-3.72 3.72a.75.75 0 0 1-1.06-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06Z" clip-rule="evenodd" />
										</svg>
									</span>
								</button>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="recordingsPassword" class="label">Password</label>
			<input id="recordingsPassword" type="password" bind:value={passwordInput} class="input" placeholder="Enter password" />
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={cancelLogin} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
