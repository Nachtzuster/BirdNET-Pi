<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, type Detection } from '$lib/api';
	import { DetectionCard } from '$lib/components';
	import { toasts } from '$lib/stores';

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

	function todayStr(): string {
		const d = new Date();
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function detectionRecordingsHref(detection: Detection): string {
		const params = new URLSearchParams({
			date: detection.Date,
			species: detection.Sci_Name,
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
				<DetectionCard {detection} href={detectionRecordingsHref(detection)} />
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
