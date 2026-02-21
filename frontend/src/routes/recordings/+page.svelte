<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, media } from '$lib/api';
	import { AudioPlayer, Modal } from '$lib/components';
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
	let deletingFiles = new Set<string>();
	let shiftingFiles = new Set<string>();
	let deletingShiftedFiles = new Set<string>();
	let shiftedAvailable: Record<string, boolean> = {};
	let showLoginModal = false;
	let passwordInput = '';

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
		} catch (e) {
			console.error('Failed to load files:', e);
			files = [];
		} finally {
			loading = false;
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

	async function requireAuth(): Promise<boolean> {
		if ($auth.isAuthenticated) return true;
		showLoginModal = true;
		return false;
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
		shiftingFiles = new Set(shiftingFiles).add(fileName);
		try {
			await media.createShifted(selectedDate, selectedSpecies, fileName);
			shiftedAvailable = { ...shiftedAvailable, [fileName]: true };
			toasts.show('Shifted audio created', 'success');
		} catch (e) {
			console.error('Failed to create shifted audio:', e);
			toasts.show('Failed to create shifted audio', 'error');
		} finally {
			const next = new Set(shiftingFiles);
			next.delete(fileName);
			shiftingFiles = next;
		}
	}

	async function deleteShifted(fileName: string) {
		deletingShiftedFiles = new Set(deletingShiftedFiles).add(fileName);
		try {
			await media.deleteShifted(selectedDate, selectedSpecies, fileName);
			shiftedAvailable = { ...shiftedAvailable, [fileName]: false };
			toasts.show('Shifted audio removed', 'success');
		} catch (e) {
			console.error('Failed to delete shifted audio:', e);
			toasts.show('Failed to remove shifted audio', 'error');
		} finally {
			const next = new Set(deletingShiftedFiles);
			next.delete(fileName);
			deletingShiftedFiles = next;
		}
	}

	function handleLogin() {
		auth.login(passwordInput);
		passwordInput = '';
		showLoginModal = false;
	}

	onMount(() => {
		const query = new URLSearchParams(window.location.search);
		queryDate = query.get('date') || '';
		querySpecies = query.get('species') || '';
		void loadDates();
	});
</script>

<svelte:head>
	<title>Recordings - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Recordings</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Browse audio files by date and species</p>
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
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					{formatBirdName(selectedSpecies)} - {selectedDate}
				</h2>
				<button
					on:click={() => { selectedSpecies = ''; files = []; }}
					class="text-sm text-primary-600 dark:text-primary-400 hover:underline"
				>
					← Back to species
				</button>
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
						<div class="card p-4">
							<div class="flex items-start gap-4">
								<!-- Spectrogram thumbnail -->
								{#if file.has_spectrogram}
									<img
										src={spectrogramUrl}
										alt="Spectrogram"
										class="w-32 h-20 object-cover rounded-lg bg-gray-200 dark:bg-dark-border flex-shrink-0"
										loading="lazy"
									/>
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
													class="btn-danger btn-sm"
													on:click={() => deleteFile(file.name)}
													disabled={deletingFiles.has(file.name)}
												>
													{deletingFiles.has(file.name) ? '...' : 'Delete'}
												</button>
											</div>
										</div>
										<p class="text-sm text-gray-500 dark:text-gray-400">{formatSize(file.size)}</p>
										<div class="mt-2">
											<AudioPlayer src={audioUrl} compact />
										</div>
										{#if shiftedAvailable[file.name]}
											<div class="mt-2">
												<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Shifted</p>
												<AudioPlayer src={shiftedUrl} compact />
											</div>
										{/if}
									</div>
							</div>
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
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
