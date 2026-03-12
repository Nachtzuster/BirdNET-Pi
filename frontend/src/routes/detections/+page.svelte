<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import {
		detections,
		media,
		species as speciesApi,
		speciesLists,
		type Detection,
		type SpeciesSummary,
	} from '$lib/api';
	import { DetectionCard, Modal } from '$lib/components';
	import { auth, toasts } from '$lib/stores';

	let allDetections: Detection[] = [];
	let loading = true;
	let searchTerm = '';
	let selectedDate = '';
	let selectedSpecies = '';
	let newOnDateOnly = false;
	let speciesOptions: SpeciesSummary[] = [];
	let availableDates: string[] = [];
	let limit = 20;
	let offset = 0;
	let total = 0;
	let hasMore = false;
	let deletingFiles = new Set<string>();
	let shiftingFiles = new Set<string>();
	let showLoginModal = false;
	let passwordInput = '';
	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	let detectionsRequestId = 0;

	function todayStr(): string {
		const d = new Date();
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function speciesFolderFromFilename(filename: string): string {
		const match = filename.match(/^(.+?)-\d+-\d{4}-/);
		if (match?.[1]) return match[1];
		return filename.split(/-(?=\d)/, 1)[0] || filename;
	}

	function detectionRecordingsHref(detection: Detection): string {
		const params = new URLSearchParams({
			date: detection.Date,
			species: speciesFolderFromFilename(detection.File_Name),
			sci: detection.Sci_Name,
			com: detection.Com_Name,
		});
		return `/recordings?${params.toString()}`;
	}

	async function loadDetections(reset = false) {
		const requestId = ++detectionsRequestId;

		if (reset) {
			offset = 0;
			allDetections = [];
		}

		loading = true;
		try {
			const params: { limit: number; offset: number; date?: string; species?: string; search?: string; new_on_date?: boolean } = { limit, offset };
			if (selectedDate) params.date = selectedDate;
			if (selectedSpecies) params.species = selectedSpecies;
			if (searchTerm.trim()) params.search = searchTerm.trim();
			if (newOnDateOnly && selectedDate) params.new_on_date = true;

			const result = await detections.list(params);
			if (requestId !== detectionsRequestId) return;
			if (reset) {
				allDetections = result.detections;
			} else {
				allDetections = [...allDetections, ...result.detections];
			}
			total = result.total;
			hasMore = allDetections.length < total;
		} catch (e) {
			if (requestId !== detectionsRequestId) return;
			console.error('Failed to load detections:', e);
			toasts.show('Failed to load detections', 'error');
		} finally {
			if (requestId !== detectionsRequestId) return;
			loading = false;
		}
	}

	async function loadSpeciesOptions() {
		try {
			const result = await speciesApi.list({ sort: 'name', date: selectedDate || undefined });
			speciesOptions = result.species;
			if (selectedSpecies && !speciesOptions.some((item) => item.Sci_Name === selectedSpecies)) {
				selectedSpecies = '';
			}
		} catch (e) {
			console.error('Failed to load species options:', e);
		}
	}

	async function loadDates() {
		try {
			const result = await detections.dates();
			availableDates = result.dates;
		} catch (e) {
			console.error('Failed to load dates:', e);
		}
	}

	function loadMore() {
		offset += limit;
		loadDetections();
	}

	function handleDateChange() {
		if (!selectedDate) {
			newOnDateOnly = false;
		}
		loadSpeciesOptions();
		loadDetections(true);
	}

	function handleSpeciesChange() {
		loadDetections(true);
	}

	function handleNewOnDateToggle() {
		if (!selectedDate) {
			newOnDateOnly = false;
			return;
		}
		void loadDetections(true);
	}

	function queueSearch() {
		if (searchTimer) clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			void loadDetections(true);
		}, 250);
	}

	function clearDateFilter() {
		selectedDate = '';
		newOnDateOnly = false;
		void loadSpeciesOptions();
		void loadDetections(true);
	}

	function clearSpeciesFilter() {
		selectedSpecies = '';
		void loadDetections(true);
	}

	function clearSearchFilter() {
		searchTerm = '';
		if (searchTimer) clearTimeout(searchTimer);
		void loadDetections(true);
	}

	function clearAllFilters() {
		selectedDate = '';
		selectedSpecies = '';
		searchTerm = '';
		newOnDateOnly = false;
		if (searchTimer) clearTimeout(searchTimer);
		void loadSpeciesOptions();
		void loadDetections(true);
	}

	async function requireAuth(): Promise<boolean> {
		if ($auth.isAuthenticated) return true;
		showLoginModal = true;
		return false;
	}

	async function deleteDetectionFile(detection: Detection) {
		if (!(await requireAuth())) return;
		if (!confirm(`Delete recording and detection for ${detection.Com_Name} at ${detection.Time}?`)) return;

		deletingFiles = new Set(deletingFiles).add(detection.File_Name);
		try {
			await detections.delete(detection.File_Name, auth.getCredentials());
			allDetections = allDetections.filter((item) => item.File_Name !== detection.File_Name);
			total = Math.max(0, total - 1);
			hasMore = allDetections.length < total;
			toasts.show('Detection deleted', 'success');
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to delete detection:', e);
				toasts.show('Failed to delete detection', 'error');
			}
		} finally {
			const next = new Set(deletingFiles);
			next.delete(detection.File_Name);
			deletingFiles = next;
		}
	}

	async function shiftDetection(detection: Detection) {
		if (!(await requireAuth())) return;

		shiftingFiles = new Set(shiftingFiles).add(detection.File_Name);
		try {
			await media.createShifted(
				detection.Date,
				detection.Sci_Name,
				detection.File_Name,
				auth.getCredentials()
			);
			toasts.show('Shifted audio created', 'success');
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to shift detection:', e);
				toasts.show('Failed to shift audio', 'error');
			}
		} finally {
			const next = new Set(shiftingFiles);
			next.delete(detection.File_Name);
			shiftingFiles = next;
		}
	}

	async function excludeSpecies(detection: Detection) {
		if (!(await requireAuth())) return;
		const removeExisting = confirm(
			`Exclude ${detection.Com_Name} and remove existing detections/recordings now?`
		);
		try {
			await speciesLists.update('exclude', detection.Sci_Name, 'add', auth.getCredentials());
			if (removeExisting) {
				await speciesApi.delete(detection.Sci_Name, auth.getCredentials());
				allDetections = allDetections.filter((item) => item.Sci_Name !== detection.Sci_Name);
				total = allDetections.length;
				await loadSpeciesOptions();
				toasts.show('Species excluded and existing data removed', 'success');
			} else {
				toasts.show('Species added to Exclude list', 'success');
			}
		} catch (e: any) {
			if (e?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Failed to exclude species:', e);
				toasts.show('Failed to exclude species', 'error');
			}
		}
	}

	function handleLogin() {
		auth.login(passwordInput);
		passwordInput = '';
		showLoginModal = false;
	}

	onMount(() => {
		const query = new URLSearchParams(window.location.search);
		selectedDate = query.get('date') || todayStr();
		selectedSpecies = query.get('species') || '';
		searchTerm = query.get('search') || '';
		newOnDateOnly = query.get('new_on_date') === 'true';
		loadDates();
		loadSpeciesOptions();
		loadDetections(true);
	});

	onDestroy(() => {
		if (searchTimer) clearTimeout(searchTimer);
	});
</script>

<svelte:head>
	<title>Review - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Review</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Triage and clean up detections</p>
	</div>

	<!-- Filters -->
	<div class="mb-6 rounded-2xl border border-gray-200/80 bg-white/95 p-4 shadow-sm dark:border-dark-border/80 dark:bg-dark-card/95">
		<div class="flex flex-col gap-4 lg:flex-row lg:items-end">
			<!-- Search -->
			<div class="flex-1">
				<label for="search" class="label">Search</label>
				<input
					id="search"
					type="text"
					bind:value={searchTerm}
					on:input={queueSearch}
					placeholder="Search by species name..."
					class="input"
				/>
			</div>

			<!-- Date filter -->
			<div class="w-full md:w-48">
				<label for="date" class="label">Date</label>
				<select
					id="date"
					bind:value={selectedDate}
					on:change={handleDateChange}
					class="select"
				>
					<option value="">All dates</option>
					{#each availableDates as date}
						<option value={date}>{date}</option>
					{/each}
				</select>
			</div>

			<div class="w-full md:w-60">
				<label for="speciesFilter" class="label">Species</label>
				<select
					id="speciesFilter"
					bind:value={selectedSpecies}
					on:change={handleSpeciesChange}
					class="select"
				>
					<option value="">All species</option>
					{#each speciesOptions as species}
						<option value={species.Sci_Name}>{species.Com_Name}</option>
					{/each}
				</select>
			</div>

			<div class="w-full md:w-auto">
				<label class="label" for="newOnDateOnly">New on date</label>
				<button
					id="newOnDateOnly"
					type="button"
					role="switch"
					aria-checked={newOnDateOnly}
					on:click={() => {
						newOnDateOnly = !newOnDateOnly;
						handleNewOnDateToggle();
					}}
					disabled={!selectedDate}
					class="inline-flex w-full items-center justify-between gap-3 rounded-lg border px-4 py-2 text-sm font-medium transition-colors md:min-w-44 {newOnDateOnly
						? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200'
						: 'border-gray-300 bg-white text-gray-600 dark:border-dark-border dark:bg-dark-card dark:text-gray-300'} disabled:cursor-not-allowed disabled:opacity-50"
					title={selectedDate ? 'Show only species first detected on this date' : 'Select a date to enable this filter'}
				>
					<span>{newOnDateOnly ? 'New on date' : 'All species'}</span>
					<span
						class="inline-flex h-5 w-9 items-center rounded-full transition-colors {newOnDateOnly ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-dark-border'}"
					>
						<span
							class="ml-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform {newOnDateOnly ? 'translate-x-4' : ''}"
						></span>
					</span>
				</button>
			</div>

			{#if selectedDate || selectedSpecies || searchTerm || newOnDateOnly}
				<div class="flex items-end">
					<button class="btn-ghost w-full lg:w-auto" on:click={clearAllFilters}>
						Clear all
					</button>
				</div>
			{/if}
		</div>

		<div class="mt-4 flex flex-col gap-2 border-t border-gray-200/80 pt-4 dark:border-dark-border/80">
			<p class="text-sm text-gray-600 dark:text-gray-400">
				Showing {allDetections.length} of {total} {searchTerm ? 'matching detections' : 'detections'}
			</p>
			<div class="flex flex-wrap gap-2">
				{#if selectedDate}
					<button
						class="inline-flex items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/30 px-3 py-1 text-xs text-primary-700 dark:text-primary-300"
						on:click={clearDateFilter}
					>
						<span>Date: {selectedDate}</span>
						<span aria-hidden="true">×</span>
					</button>
				{/if}
				{#if selectedSpecies}
					<button
						class="inline-flex items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/30 px-3 py-1 text-xs text-primary-700 dark:text-primary-300"
						on:click={clearSpeciesFilter}
					>
						<span>Species: {selectedSpecies}</span>
						<span aria-hidden="true">×</span>
					</button>
				{/if}
					{#if searchTerm}
						<button
							class="inline-flex items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/30 px-3 py-1 text-xs text-primary-700 dark:text-primary-300"
							on:click={clearSearchFilter}
						>
							<span>Search: {searchTerm}</span>
							<span aria-hidden="true">×</span>
						</button>
					{/if}
					{#if newOnDateOnly}
						<button
							class="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
							on:click={() => {
								newOnDateOnly = false;
								void loadDetections(true);
							}}
						>
							<span>New on date</span>
							<span aria-hidden="true">×</span>
						</button>
					{/if}
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					Open a recording for details, then use Shift or cleanup actions only when needed.
			</p>
		</div>
	</div>

	<!-- Detections grid -->
	{#if loading && allDetections.length === 0}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if allDetections.length === 0}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400">
				{searchTerm ? 'No matching detections found' : 'No detections found'}
			</p>
			{#if searchTerm || selectedDate || selectedSpecies}
				<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
					Try clearing one or more filters to widen the review queue.
				</p>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			{#each allDetections as detection (detection.File_Name)}
				<div class="space-y-2 min-w-0">
					<DetectionCard
						{detection}
						href={detectionRecordingsHref(detection)}
					/>
					<div class="card p-3 flex flex-wrap items-center gap-2">
						<a class="btn-primary btn-sm" href={detectionRecordingsHref(detection)}>
							Open in Library
						</a>
						<button
							class="btn-secondary btn-sm"
							on:click={() => shiftDetection(detection)}
							disabled={shiftingFiles.has(detection.File_Name)}
						>
							{shiftingFiles.has(detection.File_Name) ? 'Shifting...' : 'Shift'}
						</button>
						<button
							class="inline-flex items-center justify-center rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-100 dark:border-amber-900/70 dark:bg-amber-900/20 dark:text-amber-200 dark:hover:bg-amber-900/30"
							on:click={() => excludeSpecies(detection)}
						>
							Exclude
						</button>
						<button
							class="inline-flex items-center justify-center rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-900/70 dark:bg-red-900/20 dark:text-red-200 dark:hover:bg-red-900/30"
							on:click={() => deleteDetectionFile(detection)}
							disabled={deletingFiles.has(detection.File_Name)}
						>
							{deletingFiles.has(detection.File_Name) ? 'Deleting...' : 'Delete'}
						</button>
					</div>
				</div>
			{/each}
		</div>

		<!-- Load more -->
		{#if hasMore}
			<div class="mt-6 text-center">
				<button
					on:click={loadMore}
					disabled={loading}
					class="btn-secondary"
				>
					{#if loading}
						<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
					{/if}
					Load more
				</button>
			</div>
		{/if}
	{/if}
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="detectionsPassword" class="label">Password</label>
			<input id="detectionsPassword" type="password" bind:value={passwordInput} class="input" placeholder="Enter password" />
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
