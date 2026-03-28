<script lang="ts">
	import { onMount } from 'svelte';
	import { detections, type WeeklyReport } from '$lib/api';
	import { ExternalLinks } from '$lib/components';
	import { toasts } from '$lib/stores';

	let report: WeeklyReport | null = null;
	let loading = true;
	let currentEndDate = '';

	function dateFromStr(s: string): Date {
		const [y, m, d] = s.split('-').map(Number);
		return new Date(y, m - 1, d);
	}

	function formatDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function formatLongDate(value: string): string {
		const date = dateFromStr(value);
		return date.toLocaleDateString('en-US', {
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		});
	}

	function formatChange(value: number | null | undefined): string {
		if (value === null || value === undefined) return 'New activity';
		if (value === 0) return 'No change';
		return `${value > 0 ? '+' : ''}${value}%`;
	}

	function changeTone(value: number | null | undefined): string {
		if (value === null || value === undefined) return 'text-primary-600 dark:text-primary-400';
		if (value > 0) return 'text-green-600 dark:text-green-400';
		if (value < 0) return 'text-red-600 dark:text-red-400';
		return 'text-gray-500 dark:text-gray-400';
	}

	function syncUrl() {
		if (typeof window === 'undefined' || !currentEndDate) return;
		const url = new URL(window.location.href);
		url.searchParams.set('end', currentEndDate);
		window.history.replaceState({}, '', `${url.pathname}?${url.searchParams.toString()}`);
	}

	async function loadReport(endDate?: string) {
		loading = true;
		try {
			report = await detections.weeklyReport(endDate);
			currentEndDate = report.end_date;
			syncUrl();
		} catch (e) {
			console.error('Failed to load weekly report:', e);
			toasts.show('Failed to load weekly report', 'error');
		} finally {
			loading = false;
		}
	}

	function navigateWeeks(direction: -1 | 1) {
		if (!currentEndDate) return;
		const end = dateFromStr(currentEndDate);
		end.setDate(end.getDate() + direction * 7);
		void loadReport(formatDate(end));
	}

	onMount(() => {
		const params = new URLSearchParams(window.location.search);
		const end = params.get('end') || undefined;
		void loadReport(end);
	});
</script>

<svelte:head>
	<title>Weekly Report - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Weekly Report</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">A weekly summary of detections, species activity, and new arrivals</p>
		</div>
		<a href="/history?mode=week" class="btn-secondary">Open Insights</a>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if report}
		<div class="card mb-6 overflow-hidden">
			<div class="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
				<button on:click={() => navigateWeeks(-1)} class="btn-ghost">Previous Week</button>
				<div class="text-center">
					<p class="text-sm uppercase tracking-wide text-gray-500 dark:text-gray-400">{report.label}</p>
					<p class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{formatLongDate(report.start_date)} to {formatLongDate(report.end_date)}
					</p>
				</div>
				<button on:click={() => navigateWeeks(1)} class="btn-ghost">Next Week</button>
			</div>
		</div>

		<div class="grid gap-4 mb-6 sm:grid-cols-2 lg:grid-cols-4">
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Detections</p>
				<p class="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{report.total_detections}</p>
				<p class={`text-sm mt-2 ${changeTone(report.total_detections_change_pct)}`}>{formatChange(report.total_detections_change_pct)}</p>
			</div>
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Species Detected</p>
				<p class="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{report.species_count}</p>
				<p class={`text-sm mt-2 ${changeTone(report.species_count_change_pct)}`}>{formatChange(report.species_count_change_pct)}</p>
			</div>
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Previous Week</p>
				<p class="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{report.previous_total_detections}</p>
				<p class="text-sm mt-2 text-gray-500 dark:text-gray-400">detections</p>
			</div>
			<div class="card p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">First-Seen Species</p>
				<p class="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{report.first_seen_species.length}</p>
				<p class="text-sm mt-2 text-gray-500 dark:text-gray-400">new this week</p>
			</div>
		</div>

		<div class="grid gap-6 lg:grid-cols-2">
			<div class="card overflow-hidden">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">Top Species</h2>
				</div>
				<div class="divide-y divide-gray-200 dark:divide-dark-border">
					{#if report.top_species.length === 0}
						<div class="px-6 py-8 text-gray-500 dark:text-gray-400">No detections were recorded during this week.</div>
					{:else}
						{#each report.top_species as species, index}
							<div class="px-6 py-4 flex items-center justify-between gap-4">
								<div class="min-w-0">
									<p class="font-medium text-gray-900 dark:text-gray-100">{index + 1}. {species.com_name}</p>
									<p class="text-sm italic text-gray-500 dark:text-gray-400">{species.sci_name}</p>
									<p class={`text-sm mt-1 ${changeTone(species.change_pct)}`}>
										{#if species.is_new_this_week}
											New this week
										{:else}
											{formatChange(species.change_pct)} vs previous week
										{/if}
									</p>
								</div>
								<div class="flex items-center gap-3 shrink-0">
									<ExternalLinks sciName={species.sci_name} comName={species.com_name} compact={true} />
									<div class="text-right">
										<p class="text-2xl font-bold text-primary-600 dark:text-primary-400">{species.count}</p>
										<p class="text-xs text-gray-500 dark:text-gray-400">detections</p>
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</div>

			<div class="card overflow-hidden">
				<div class="card-header">
					<h2 class="font-semibold text-gray-900 dark:text-gray-100">First-Seen Species</h2>
				</div>
				<div class="divide-y divide-gray-200 dark:divide-dark-border">
					{#if report.first_seen_species.length === 0}
						<div class="px-6 py-8 text-gray-500 dark:text-gray-400">No new species were first detected during this week.</div>
					{:else}
						{#each report.first_seen_species as species}
							<div class="px-6 py-4 flex items-center justify-between gap-4">
								<div class="min-w-0">
									<p class="font-medium text-gray-900 dark:text-gray-100">{species.com_name}</p>
									<p class="text-sm italic text-gray-500 dark:text-gray-400">{species.sci_name}</p>
								</div>
								<div class="flex items-center gap-3 shrink-0">
									<ExternalLinks sciName={species.sci_name} comName={species.com_name} compact={true} />
									<div class="text-right">
										<p class="text-2xl font-bold text-primary-600 dark:text-primary-400">{species.count}</p>
										<p class="text-xs text-gray-500 dark:text-gray-400">detections</p>
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
