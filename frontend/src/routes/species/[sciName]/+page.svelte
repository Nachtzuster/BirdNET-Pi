<script lang="ts">
	import { page } from '$app/stores';
	import { integrations, species as speciesApi, type Detection, type SpeciesExternalLinks, type SpeciesStats } from '$lib/api';
	import { DetectionCard, ExternalLinks, SpeciesImage } from '$lib/components';
	import { toasts } from '$lib/stores';

	$: sciName = decodeURIComponent($page.params.sciName ?? '');

	let stats: SpeciesStats | null = null;
	let detectionsList: Detection[] = [];
	let chartData: { date: string; count: number }[] = [];
	let speciesLinks: SpeciesExternalLinks | null = null;
	let loading = true;

	async function loadData() {
		if (!sciName) return;
		loading = true;
		try {
			const [statsData, detectionsData, chartResult] = await Promise.all([
				speciesApi.stats(sciName),
				speciesApi.detections(sciName, { limit: 12 }),
				speciesApi.chartData(sciName, 30),
			]);

			stats = statsData;
			detectionsList = detectionsData.detections;
			chartData = chartResult.data;
			speciesLinks = await integrations.speciesLinks(sciName, statsData.com_name);
		} catch (e) {
			console.error('Failed to load species data:', e);
			toasts.show('Failed to load species data', 'error');
		} finally {
			loading = false;
		}
	}

	function formatConfidence(confidence: number): string {
		return `${(confidence * 100).toFixed(0)}%`;
	}

	$: if (sciName) {
		void loadData();
	}
</script>

<svelte:head>
	<title>{stats?.com_name || sciName} - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<!-- Back link -->
	<a href="/species" class="text-primary-600 dark:text-primary-400 hover:underline text-sm mb-4 inline-block">
		← Back to species
	</a>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if stats}
		<!-- Header -->
		<div class="card p-6 mb-6">
			<div class="flex flex-col md:flex-row gap-6">
				<SpeciesImage sciName={sciName} size="lg" />
				<div class="flex-1">
					<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
						{stats.com_name}
					</h1>
					<p class="text-lg text-gray-500 dark:text-gray-400 italic">
						{stats.sci_name}
					</p>
					<ExternalLinks links={speciesLinks} compact={false} />

					<div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
						<div>
							<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_detections}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400">Detections</p>
						</div>
						<div>
							<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.days_detected}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400">Days</p>
						</div>
						<div>
							<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatConfidence(stats.max_confidence)}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400">Max Confidence</p>
						</div>
						<div>
							<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatConfidence(stats.avg_confidence)}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400">Avg Confidence</p>
						</div>
					</div>

					<div class="mt-4 text-sm text-gray-600 dark:text-gray-400">
						<p>First seen: {stats.first_detection}</p>
						<p>Last seen: {stats.last_detection}</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Activity chart (simple bar representation) -->
		{#if chartData.length > 0}
			<div class="card p-6 mb-6">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
					Last 30 Days Activity
				</h2>
				<div class="flex items-end gap-1 h-24">
					{#each chartData as day}
						{@const maxCount = Math.max(...chartData.map(d => d.count))}
						{@const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0}
						<div
							class="flex-1 bg-primary-500 rounded-t transition-all hover:bg-primary-600"
							style="height: {height}%"
							title="{day.date}: {day.count} detections"></div>
					{/each}
				</div>
				<div class="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
					<span>{chartData[0]?.date}</span>
					<span>{chartData[chartData.length - 1]?.date}</span>
				</div>
			</div>
		{/if}

		<!-- Recent detections -->
		<div class="mb-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				Recent Detections
			</h2>
			{#if detectionsList.length === 0}
				<div class="card p-8 text-center">
					<p class="text-gray-600 dark:text-gray-400">No detections found</p>
				</div>
			{:else}
				<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
					{#each detectionsList as detection (detection.File_Name)}
						<DetectionCard {detection} showImage={false} speciesLinks={speciesLinks} />
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400">Species not found</p>
		</div>
	{/if}
</div>
