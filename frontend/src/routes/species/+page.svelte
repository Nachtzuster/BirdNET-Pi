<script lang="ts">
	import { onMount } from 'svelte';
	import { species as speciesApi, type SpeciesSummary } from '$lib/api';
	import { ExternalLinks, SpeciesImage } from '$lib/components';
	import { toasts } from '$lib/stores';

	let speciesList: SpeciesSummary[] = [];
	let loading = true;
	let sortBy = 'count';
	let searchTerm = '';

	$: filteredSpecies = searchTerm
		? speciesList.filter(
				(s) =>
					s.Com_Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
					s.Sci_Name.toLowerCase().includes(searchTerm.toLowerCase())
			)
		: speciesList;

	async function loadSpecies() {
		loading = true;
		try {
			const result = await speciesApi.list({ sort: sortBy });
			speciesList = result.species;
		} catch (e) {
			console.error('Failed to load species:', e);
			toasts.show('Failed to load species', 'error');
		} finally {
			loading = false;
		}
	}

	function handleSortChange() {
		loadSpecies();
	}

	function formatConfidence(confidence: number): string {
		return `${(confidence * 100).toFixed(0)}%`;
	}

	onMount(loadSpecies);
</script>

<svelte:head>
	<title>Species - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex items-center justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Species</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">All detected species</p>
		</div>
		<a href="/species/manage" class="btn-secondary">Manage Lists</a>
	</div>

	<!-- Filters -->
	<div class="card p-4 mb-6">
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
				<select
					id="sort"
					bind:value={sortBy}
					on:change={handleSortChange}
					class="select"
				>
					<option value="count">Detection count</option>
					<option value="confidence">Max confidence</option>
					<option value="date">Most recent</option>
					<option value="name">Name</option>
				</select>
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
			<p class="text-gray-600 dark:text-gray-400">No species found</p>
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
								{sp.Count} detections
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
