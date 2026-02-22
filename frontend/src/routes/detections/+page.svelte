<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, integrations, type Detection, type SpeciesExternalLinks } from '$lib/api';
	import { DetectionCard, Modal } from '$lib/components';
	import { auth, toasts } from '$lib/stores';

	let allDetections: Detection[] = [];
	let loading = true;
	let searchTerm = '';
	let selectedDate = '';
	let selectedSpecies = '';
	let availableDates: string[] = [];
	let limit = 20;
	let offset = 0;
	let total = 0;
	let hasMore = false;
	let speciesLinksBySci: Record<string, SpeciesExternalLinks> = {};
	let deletingFiles = new Set<string>();
	let showLoginModal = false;
	let passwordInput = '';

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
		});
		return `/recordings?${params.toString()}`;
	}

	$: filteredDetections = searchTerm
		? allDetections.filter(
				(d) =>
					d.Com_Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
					d.Sci_Name.toLowerCase().includes(searchTerm.toLowerCase())
			)
		: allDetections;

	async function loadSpeciesLinks(items: Detection[]) {
		const entries = Array.from(
			new Map(items.map((item) => [item.Sci_Name, item.Com_Name])).entries()
		);
		const missing = entries.filter(([sciName]) => !speciesLinksBySci[sciName]);
		if (missing.length === 0) return;

		const loaded = await Promise.all(
			missing.map(async ([sciName, comName]) => {
				try {
					const links = await integrations.speciesLinks(sciName, comName);
					return [sciName, links] as const;
				} catch {
					return null;
				}
			})
		);

		const next = { ...speciesLinksBySci };
		for (const item of loaded) {
			if (!item) continue;
			next[item[0]] = item[1];
		}
		speciesLinksBySci = next;
	}

	async function loadDetections(reset = false) {
		if (reset) {
			offset = 0;
			allDetections = [];
		}

		loading = true;
		try {
			const params: { limit: number; offset: number; date?: string; species?: string } = { limit, offset };
			if (selectedDate) params.date = selectedDate;
			if (selectedSpecies) params.species = selectedSpecies;

			const result = await detections.list(params);
			if (reset) {
				allDetections = result.detections;
			} else {
				allDetections = [...allDetections, ...result.detections];
			}
			await loadSpeciesLinks(result.detections);
			total = result.total;
			hasMore = allDetections.length < total;
		} catch (e) {
			console.error('Failed to load detections:', e);
			toasts.show('Failed to load detections', 'error');
		} finally {
			loading = false;
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
		loadDetections(true);
	}

	function clearSpeciesFilter() {
		selectedSpecies = '';
		loadDetections(true);
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
		loadDates();
		loadDetections(true);
	});
</script>

<svelte:head>
	<title>Detections - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Detections</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Browse all bird detections</p>
	</div>

	<!-- Filters -->
	<div class="card p-4 mb-6">
		<div class="flex flex-col md:flex-row gap-4">
			<!-- Search -->
			<div class="flex-1">
				<label for="search" class="label">Search</label>
				<input
					id="search"
					type="text"
					bind:value={searchTerm}
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
		</div>
	</div>

	<!-- Results count -->
	<div class="mb-4 flex flex-col gap-2">
		<p class="text-sm text-gray-600 dark:text-gray-400">
			Showing {filteredDetections.length} of {total} detections
		</p>
		{#if selectedSpecies}
			<div class="inline-flex w-fit items-center gap-2 rounded-full bg-primary-100 dark:bg-primary-900/30 px-3 py-1 text-xs text-primary-700 dark:text-primary-300">
				<span>Species filter: {selectedSpecies}</span>
				<button class="underline" on:click={clearSpeciesFilter}>Clear</button>
			</div>
		{/if}
	</div>

	<!-- Detections grid -->
	{#if loading && allDetections.length === 0}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if filteredDetections.length === 0}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400">No detections found</p>
		</div>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each filteredDetections as detection (detection.File_Name)}
				<DetectionCard
					{detection}
					href={detectionRecordingsHref(detection)}
					allowDelete={true}
					deleting={deletingFiles.has(detection.File_Name)}
					speciesLinks={speciesLinksBySci[detection.Sci_Name] || null}
					on:delete={(event) => deleteDetectionFile(event.detail)}
				/>
			{/each}
		</div>

		<!-- Load more -->
		{#if hasMore && !searchTerm}
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
