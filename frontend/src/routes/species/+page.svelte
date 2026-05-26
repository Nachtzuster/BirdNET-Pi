<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, species as speciesApi, type SpeciesSummary } from '$lib/api';
	import { ExternalLinks, SpeciesImage } from '$lib/components';
	import { toasts } from '$lib/stores';

	type DateFilter = 'all' | 'today' | 'pick';

	let speciesList: SpeciesSummary[] = [];
	let loading = true;
	let sortBy = 'count';
	let searchTerm = '';
	let dateFilter: DateFilter = 'all';
	let pickedDate = '';
	let availableDates: string[] = [];

	$: filteredSpecies = searchTerm
		? speciesList.filter(
				(s) =>
					s.Com_Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
					s.Sci_Name.toLowerCase().includes(searchTerm.toLowerCase())
			)
		: speciesList;

	$: subtitle =
		dateFilter === 'today'
			? `Species detected today (${todayStr()})`
			: dateFilter === 'pick' && pickedDate
				? `Species detected on ${pickedDate}`
				: 'All detected species';

	$: emptyMessage =
		dateFilter === 'all'
			? 'No species found'
			: dateFilter === 'today'
				? 'No species detected today yet'
				: pickedDate
					? `No species detected on ${pickedDate}`
					: 'Choose a date to view species';

	function todayStr(): string {
		const d = new Date();
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function activeDateParam(): string | undefined {
		if (dateFilter === 'today') return todayStr();
		if (dateFilter === 'pick' && pickedDate) return pickedDate;
		return undefined;
	}

	function syncUrl() {
		if (typeof window === 'undefined') return;
		const url = new URL(window.location.href);
		if (dateFilter === 'all') {
			url.searchParams.delete('date');
		} else if (dateFilter === 'today') {
			url.searchParams.set('date', 'today');
		} else if (pickedDate) {
			url.searchParams.set('date', pickedDate);
		} else {
			url.searchParams.delete('date');
		}
		const search = url.searchParams.toString();
		window.history.replaceState({}, '', search ? `${url.pathname}?${search}` : url.pathname);
	}

	function parseUrl() {
		if (typeof window === 'undefined') return;
		const date = new URLSearchParams(window.location.search).get('date');
		if (!date) {
			dateFilter = 'all';
			return;
		}
		if (date === 'today') {
			dateFilter = 'today';
			return;
		}
		if (/^\d{4}-\d{2}-\d{2}$/.test(date)) {
			dateFilter = 'pick';
			pickedDate = date;
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

	async function loadSpecies() {
		if (dateFilter === 'pick' && !pickedDate) {
			speciesList = [];
			loading = false;
			return;
		}

		loading = true;
		try {
			const date = activeDateParam();
			const result = await speciesApi.list({ sort: sortBy, date });
			speciesList = result.species;
		} catch (e) {
			console.error('Failed to load species:', e);
			toasts.show('Failed to load species', 'error');
		} finally {
			loading = false;
		}
	}

	function setDateFilter(filter: DateFilter) {
		dateFilter = filter;
		if (filter === 'pick' && !pickedDate) {
			pickedDate = availableDates[0] || todayStr();
		}
		syncUrl();
		void loadSpecies();
	}

	function handlePickedDateChange() {
		syncUrl();
		void loadSpecies();
	}

	function handleSortChange() {
		void loadSpecies();
	}

	function formatConfidence(confidence: number): string {
		return `${(confidence * 100).toFixed(0)}%`;
	}

	onMount(async () => {
		parseUrl();
		await loadDates();
		if (dateFilter === 'pick' && !pickedDate) {
			pickedDate = availableDates[0] || todayStr();
		}
		await loadSpecies();
	});
</script>

<svelte:head>
	<title>Species - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex items-center justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Species</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">{subtitle}</p>
		</div>
		<a href="/species/manage" class="btn-secondary">Manage Lists</a>
	</div>

	<!-- Filters -->
	<div class="card p-4 mb-6">
		<div class="flex flex-col gap-4">
			<div>
				<span class="label block mb-2">Time range</span>
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
					<div class="inline-flex rounded-lg border border-gray-200 dark:border-dark-border overflow-hidden text-sm">
						<button
							type="button"
							class="px-4 py-2 {dateFilter === 'today'
								? 'bg-primary-600 text-white'
								: 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-dark-border'}"
							on:click={() => setDateFilter('today')}
						>
							Today
						</button>
						<button
							type="button"
							class="px-4 py-2 border-l border-gray-200 dark:border-dark-border {dateFilter === 'all'
								? 'bg-primary-600 text-white'
								: 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-dark-border'}"
							on:click={() => setDateFilter('all')}
						>
							All time
						</button>
						<button
							type="button"
							class="px-4 py-2 border-l border-gray-200 dark:border-dark-border {dateFilter === 'pick'
								? 'bg-primary-600 text-white'
								: 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-dark-border'}"
							on:click={() => setDateFilter('pick')}
						>
							Pick date
						</button>
					</div>
					{#if dateFilter === 'pick'}
						<div class="w-full sm:w-auto sm:min-w-[12rem]">
							<label for="pickedDate" class="sr-only">Date</label>
							<select
								id="pickedDate"
								bind:value={pickedDate}
								on:change={handlePickedDateChange}
								class="select w-full text-sm"
							>
								{#if availableDates.length === 0}
									<option value={pickedDate}>{pickedDate || 'No dates yet'}</option>
								{:else}
									{#each availableDates as date}
										<option value={date}>{date}</option>
									{/each}
								{/if}
							</select>
						</div>
					{/if}
				</div>
			</div>

			<div class="flex flex-col md:flex-row gap-4">
				<div class="flex-1">
					<label for="search" class="label">Search</label>
					<input
						id="search"
						type="text"
						bind:value={searchTerm}
						placeholder="Search species..."
						class="input"
					/>
				</div>
				<div class="w-full md:w-48">
					<label for="sort" class="label">Sort by</label>
					<select id="sort" bind:value={sortBy} on:change={handleSortChange} class="select">
						<option value="count">Detection count</option>
						<option value="confidence">Max confidence</option>
						<option value="date">Most recent</option>
						<option value="name">Name</option>
					</select>
				</div>
			</div>
		</div>
	</div>

	<!-- Species count -->
	<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
		{filteredSpecies.length} species
	</p>

	<!-- Species list -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if filteredSpecies.length === 0}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400">{emptyMessage}</p>
		</div>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each filteredSpecies as sp (sp.Sci_Name)}
				<div class="card p-4 flex gap-4 hover:shadow-lg transition-shadow">
					<SpeciesImage sciName={sp.Sci_Name} size="sm" />
					<div class="flex-1 min-w-0">
						<a href="/species/{encodeURIComponent(sp.Sci_Name)}">
							<h3 class="font-semibold text-gray-900 dark:text-gray-100 truncate hover:underline">
								{sp.Com_Name}
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate">
								{sp.Sci_Name}
							</p>
						</a>
						<div class="mt-1">
							<ExternalLinks sciName={sp.Sci_Name} comName={sp.Com_Name} compact={true} />
						</div>
						<div class="mt-2 flex items-center gap-4 text-sm">
							<span class="text-gray-600 dark:text-gray-400">
								{sp.Count} {sp.Count === 1 ? 'detection' : 'detections'}{dateFilter === 'all' ? '' : ' on this day'}
							</span>
							<span class="badge-primary">
								{formatConfidence(sp.MaxConfidence)}
							</span>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
