<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { detections, integrations, type RangeChartData } from '$lib/api';
	import { ExternalLinks } from '$lib/components';
	import { toasts } from '$lib/stores';

	let ChartJS: typeof import('chart.js/auto').default;

	// Range modes
	type RangeMode = 'day' | 'week' | 'month' | 'year';
	let rangeMode: RangeMode = 'day';

	// Navigation anchor — the "current" date/period being viewed
	let anchorDate: string = '';
	let availableDates: string[] = [];

	let chartData: RangeChartData | null = null;
	let loading = false;
	let exportLoading = false;

	let mainCanvas: HTMLCanvasElement;
	let speciesCanvas: HTMLCanvasElement;
	let mainChart: any = null;
	let speciesChart: any = null;

	let selectedSpecies: Set<string> = new Set();
	let isDark = false;
	let prefersReducedMotion = false;

	function detectTheme() {
		isDark = document.documentElement.classList.contains('dark');
	}

	// ── Date helpers ──────────────────────────────────────────────

	function todayStr(): string {
		const d = new Date();
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function dateFromStr(s: string): Date {
		const [y, m, d] = s.split('-').map(Number);
		return new Date(y, m - 1, d);
	}

	function formatDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	/** Return {start, end} for the range around anchorDate given the mode. */
	function getRange(anchor: string, mode: RangeMode): { start: string; end: string } {
		const d = dateFromStr(anchor);
		if (mode === 'day') {
			return { start: anchor, end: anchor };
		}
		if (mode === 'week') {
			const end = new Date(d);
			const start = new Date(d);
			start.setDate(end.getDate() - 6);
			return { start: formatDate(start), end: formatDate(end) };
		}
		if (mode === 'month') {
			const end = new Date(d);
			const start = new Date(d);
			start.setDate(end.getDate() - 29);
			return { start: formatDate(start), end: formatDate(end) };
		}
		// year
		return { start: `${d.getFullYear()}-01-01`, end: `${d.getFullYear()}-12-31` };
	}

	/** Human-readable label for the current range */
	function rangeLabel(anchor: string, mode: RangeMode): string {
		if (!anchor) return '';
		const d = dateFromStr(anchor);
		if (mode === 'day') return anchor;
		if (mode === 'week') {
			const { start, end } = getRange(anchor, 'week');
			return `${start}  —  ${end}`;
		}
		if (mode === 'month') {
			const { start, end } = getRange(anchor, 'month');
			return `${start}  —  ${end}`;
		}
		return String(d.getFullYear());
	}

	function groupByForMode(mode: RangeMode): 'hour' | 'day' | 'week' | 'month' {
		if (mode === 'day') return 'hour';
		if (mode === 'week') return 'day';
		if (mode === 'month') return 'day';
		return 'day';
	}

	function parseRangeMode(value: string | null): RangeMode {
		if (value === 'day' || value === 'week' || value === 'month' || value === 'year') return value;
		return 'day';
	}

	function parseInitialStateFromUrl() {
		if (typeof window === 'undefined') return;
		const params = new URLSearchParams(window.location.search);
		rangeMode = parseRangeMode(params.get('mode'));

		const date = params.get('date');
		if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
			anchorDate = date;
		}
	}

	// ── Navigation ────────────────────────────────────────────────

	function navigate(direction: -1 | 1) {
		const d = dateFromStr(anchorDate);
		if (rangeMode === 'day') {
			d.setDate(d.getDate() + direction);
		} else if (rangeMode === 'week') {
			d.setDate(d.getDate() + direction * 7);
		} else if (rangeMode === 'month') {
			d.setDate(d.getDate() + direction * 30);
		} else {
			d.setFullYear(d.getFullYear() + direction);
		}
		anchorDate = formatDate(d);
		loadChartData();
	}

	function goToToday() {
		anchorDate = todayStr();
		loadChartData();
	}

	function changeMode(mode: RangeMode) {
		rangeMode = mode;
		selectedSpecies = new Set();
		loadChartData();
	}

	// ── Data loading ──────────────────────────────────────────────

	async function loadDates() {
		try {
			const result = await detections.dates();
			availableDates = result.dates;
			if (!anchorDate && availableDates.length > 0) {
				anchorDate = availableDates[0]; // most recent date
			} else if (!anchorDate) {
				anchorDate = todayStr();
			}
			await loadChartData();
		} catch (e) {
			console.error('Failed to load dates:', e);
		}
	}

	async function loadChartData() {
		if (!anchorDate) return;
		loading = true;
		selectedSpecies = new Set();
		try {
			const { start, end } = getRange(anchorDate, rangeMode);
			chartData = await detections.chartDataRange({
				start,
				end,
				group_by: groupByForMode(rangeMode),
			});
		} catch (e) {
			console.error('Failed to load chart data:', e);
			toasts.show('Failed to load chart data', 'error');
			chartData = null;
		} finally {
			loading = false;
		}
		await tick();
		renderCharts();
	}

	function reviewDateForBucket(period: number | string): string {
		if (rangeMode === 'day') return anchorDate;
		if (rangeMode === 'week' || rangeMode === 'month') return period as string;
		const value = String(period);
		return `${value}-01`;
	}

	function openReviewFromBucket(bucketIndex: number) {
		if (!chartData) return;
		const bucket = chartData.buckets[bucketIndex];
		if (!bucket) return;
		const params = new URLSearchParams();
		params.set('date', reviewDateForBucket(bucket.period));
		if (selectedSpecies.size === 1) {
			const sci = Array.from(selectedSpecies)[0];
			params.set('species', sci);
		}
		window.location.href = `/detections?${params.toString()}`;
	}

	// ── Species toggle ────────────────────────────────────────────

	function toggleSpecies(sciName: string) {
		if (rangeMode === 'year') return;
		if (selectedSpecies.has(sciName)) {
			selectedSpecies.delete(sciName);
		} else {
			selectedSpecies.add(sciName);
		}
		selectedSpecies = new Set(selectedSpecies);
		renderCharts();
	}

	function clearSelectedSpecies() {
		selectedSpecies = new Set();
		renderCharts();
	}

	// ── Colors ────────────────────────────────────────────────────

	const SPECIES_COLORS = [
		'#16a34a', '#2563eb', '#d97706', '#dc2626', '#7c3aed',
		'#0891b2', '#c026d3', '#ea580c', '#4f46e5', '#059669',
		'#e11d48', '#0d9488', '#ca8a04', '#6366f1', '#84cc16',
	];

	function getChartColors() {
		return {
			text: isDark ? '#d1d5db' : '#374151',
			textMuted: isDark ? '#9ca3af' : '#6b7280',
			grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
			barBg: isDark ? 'rgba(34,197,94,0.6)' : 'rgba(22,163,74,0.7)',
			barBorder: isDark ? 'rgb(34,197,94)' : 'rgb(22,163,74)',
			barHoverBg: isDark ? 'rgba(34,197,94,0.85)' : 'rgba(22,163,74,0.9)',
			otherBg: isDark ? 'rgba(107,114,128,0.35)' : 'rgba(156,163,175,0.4)',
			otherBorder: isDark ? 'rgba(107,114,128,0.5)' : 'rgba(156,163,175,0.6)',
			doughnutColors: SPECIES_COLORS.slice(0, 10),
		};
	}

	function getSpeciesColor(sciName: string): string {
		if (!chartData) return SPECIES_COLORS[0];
		const idx = chartData.top_species.findIndex(s => s.sci_name === sciName);
		if (idx >= 0) return SPECIES_COLORS[idx % SPECIES_COLORS.length];
		let hash = 0;
		for (let i = 0; i < sciName.length; i++) hash = (hash * 31 + sciName.charCodeAt(i)) | 0;
		return SPECIES_COLORS[Math.abs(hash) % SPECIES_COLORS.length];
	}

	// ── Chart labels ──────────────────────────────────────────────

	function getHourLabel(hour: number): string {
		if (hour === 0) return '12am';
		if (hour === 12) return '12pm';
		return hour < 12 ? `${hour}am` : `${hour - 12}pm`;
	}

	function getBucketLabel(period: number | string, mode: RangeMode): string {
		if (mode === 'day') return getHourLabel(period as number);
		if (mode === 'week' || mode === 'month') {
			// period is YYYY-MM-DD
			const d = dateFromStr(period as string);
			if (mode === 'week') {
				return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
			}
			return d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
		}
		// fallback
		const [y, m] = (period as string).split('-');
		const d = new Date(Number(y), Number(m) - 1, 1);
		return d.toLocaleDateString('en-US', { month: 'short' });
	}

	function getXTickSkip(): number {
		if (rangeMode === 'day') return 3;   // show every 3rd hour
		if (rangeMode === 'week') return 1;  // show every day
		if (rangeMode === 'month') return 4; // show every 4th day
		return 1;
	}

	const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	const YEAR_WEEK_COLORS = [
		'rgba(22, 163, 74, 0.95)',
		'rgba(34, 197, 94, 0.85)',
		'rgba(74, 222, 128, 0.8)',
		'rgba(134, 239, 172, 0.75)',
		'rgba(187, 247, 208, 0.7)',
		'rgba(220, 252, 231, 0.65)',
	];

	function weekOfMonth(date: Date): number {
		const firstOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
		const mondayOffset = (firstOfMonth.getDay() + 6) % 7;
		return Math.floor((mondayOffset + date.getDate() - 1) / 7) + 1;
	}

	function buildYearWeekBreakdown(
		buckets: { period: number | string; count: number }[]
	): { labels: string[]; totalsByWeek: number[][]; weekCount: number } {
		const totalsByWeek = Array.from({ length: 12 }, () => new Array(6).fill(0));
		let maxWeek = 0;
		for (const bucket of buckets) {
			const period = String(bucket.period);
			if (!/^\d{4}-\d{2}-\d{2}$/.test(period)) continue;
			const d = dateFromStr(period);
			const monthIndex = d.getMonth();
			const weekIndex = weekOfMonth(d) - 1;
			totalsByWeek[monthIndex][weekIndex] += bucket.count;
			maxWeek = Math.max(maxWeek, weekIndex + 1);
		}
		return {
			labels: MONTH_LABELS,
			totalsByWeek,
			weekCount: Math.max(1, maxWeek),
		};
	}

	function openReviewForMonth(monthIndex: number) {
		const params = new URLSearchParams();
		const year = dateFromStr(anchorDate).getFullYear();
		params.set('date', `${year}-${String(monthIndex + 1).padStart(2, '0')}-01`);
		window.location.href = `/detections?${params.toString()}`;
	}

	// ── Chart rendering ───────────────────────────────────────────

	function renderCharts() {
		if (!chartData || !ChartJS) return;
		detectTheme();
		const colors = getChartColors();
		renderMainChart(colors);
		renderSpeciesChart(colors);
	}

	function renderMainChart(colors: ReturnType<typeof getChartColors>) {
		if (!chartData || !mainCanvas) return;
		if (mainChart) mainChart.destroy();

		let labels: string[] = chartData.buckets.map(b => getBucketLabel(b.period, rangeMode));
		let totalCounts = chartData.buckets.map(b => b.count);
		let datasets: any[];

		if (rangeMode === 'year') {
			const breakdown = buildYearWeekBreakdown(chartData.buckets);
			labels = breakdown.labels;
			totalCounts = breakdown.totalsByWeek.map((month) => month.reduce((sum, count) => sum + count, 0));
			datasets = Array.from({ length: breakdown.weekCount }, (_v, weekIndex) => ({
				label: `Week ${weekIndex + 1}`,
				data: breakdown.totalsByWeek.map((month) => month[weekIndex] ?? 0),
				backgroundColor: YEAR_WEEK_COLORS[weekIndex % YEAR_WEEK_COLORS.length],
				borderColor: colors.barBorder,
				borderWidth: 1,
				borderRadius: 2,
			}));
		} else if (selectedSpecies.size === 0) {
			datasets = [{
				label: 'Detections',
				data: totalCounts,
				backgroundColor: colors.barBg,
				borderColor: colors.barBorder,
				borderWidth: 1,
				borderRadius: 4,
				hoverBackgroundColor: colors.barHoverBg,
			}];
		} else {
			// Build species-indexed map from species_buckets
			const speciesMap = new Map(chartData.species_buckets.map(sb => [sb.sci_name, sb]));
			datasets = [];
			const selectedTotals = new Array(chartData.buckets.length).fill(0);

			for (const sciName of selectedSpecies) {
				const sb = speciesMap.get(sciName);
				if (!sb) continue;
				const color = getSpeciesColor(sciName);
				datasets.push({
					label: sb.com_name,
					data: sb.counts,
					backgroundColor: color + 'cc',
					borderColor: color,
					borderWidth: 1,
					borderRadius: 2,
				});
				for (let i = 0; i < sb.counts.length; i++) {
					selectedTotals[i] += sb.counts[i];
				}
			}

			const otherData = totalCounts.map((t, i) => Math.max(0, t - selectedTotals[i]));
			if (otherData.some(v => v > 0)) {
				datasets.push({
					label: 'Other',
					data: otherData,
					backgroundColor: colors.otherBg,
					borderColor: colors.otherBorder,
					borderWidth: 1,
					borderRadius: 2,
				});
			}
		}

		const tickSkip = getXTickSkip();
		const isStacked = rangeMode === 'year' || selectedSpecies.size > 0;

		mainChart = new ChartJS(mainCanvas, {
			type: 'bar',
			data: { labels, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: { duration: prefersReducedMotion ? 0 : 150, easing: 'linear' },
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						display: rangeMode === 'year' || selectedSpecies.size > 0,
						position: 'top',
						labels: {
							color: colors.text,
							usePointStyle: true,
							pointStyle: 'rectRounded',
							padding: 16,
							font: { size: 12 },
						},
					},
					tooltip: {
						backgroundColor: isDark ? '#1f2937' : '#fff',
						titleColor: colors.text,
						bodyColor: colors.text,
						borderColor: colors.grid,
						borderWidth: 1,
						padding: 12,
						cornerRadius: 8,
						callbacks: {
							label: (ctx) => {
								const val = ctx.parsed.y;
								if (val === 0) return '';
								return ` ${ctx.dataset.label}: ${val} detection${val !== 1 ? 's' : ''}`;
							},
						},
					},
				},
				scales: {
					x: {
						stacked: isStacked,
						grid: { display: false },
						ticks: {
							color: colors.textMuted,
							font: { size: 11 },
							maxRotation: rangeMode === 'week' ? 45 : 0,
							callback: function(_value, index) {
								return index % tickSkip === 0 ? labels[index] : '';
							},
						},
					},
					y: {
						stacked: isStacked,
						beginAtZero: true,
						grid: { color: colors.grid },
						ticks: {
							color: colors.textMuted,
							font: { size: 11 },
							precision: 0,
						},
					},
				},
				onClick: (_event, elements) => {
					if (!elements || elements.length === 0) return;
					if (rangeMode === 'year') {
						openReviewForMonth(elements[0].index);
						return;
					}
					openReviewFromBucket(elements[0].index);
				},
			},
		});
	}

	function renderSpeciesChart(colors: ReturnType<typeof getChartColors>) {
		if (!chartData || !speciesCanvas || chartData.top_species.length === 0) return;
		if (speciesChart) speciesChart.destroy();

		const species = chartData.top_species.slice(0, 8);

		speciesChart = new ChartJS(speciesCanvas, {
			type: 'doughnut',
			data: {
				labels: species.map(s => s.com_name),
				datasets: [{
					data: species.map(s => s.count),
					backgroundColor: colors.doughnutColors.slice(0, species.length),
					borderWidth: 0,
					hoverOffset: 6,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '55%',
				animation: { duration: prefersReducedMotion ? 0 : 180, easing: 'linear' },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: isDark ? '#1f2937' : '#fff',
						titleColor: colors.text,
						bodyColor: colors.text,
						borderColor: colors.grid,
						borderWidth: 1,
						padding: 12,
						cornerRadius: 8,
						callbacks: {
							label: (ctx) => {
								const total = (ctx.dataset.data as number[]).reduce((a, b) => a + b, 0);
								const pct = ((ctx.parsed / total) * 100).toFixed(0);
								return ` ${ctx.parsed} detections (${pct}%)`;
							},
						},
					},
				},
			},
		});
	}

	// ── eBird export ──────────────────────────────────────────────

	async function exportEbird() {
		if (!anchorDate) return;
		exportLoading = true;
		try {
			const exportDate = rangeMode === 'day' ? anchorDate : anchorDate;
			const result = await integrations.ebirdExport(exportDate);
			const blob = new Blob([result.csv], { type: 'text/csv' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `ebird-export-${exportDate}.csv`;
			a.click();
			URL.revokeObjectURL(url);
			toasts.show(`Exported ${result.species_count} species`, 'success');
		} catch (e) {
			console.error('Failed to export:', e);
			toasts.show('Failed to export eBird data', 'error');
		} finally {
			exportLoading = false;
		}
	}

	// ── Peak stat ─────────────────────────────────────────────────

	function peakLabel(): string {
		if (!chartData || chartData.buckets.length === 0) return '—';
		if (rangeMode === 'year') {
			const breakdown = buildYearWeekBreakdown(chartData.buckets);
			const monthlyTotals = breakdown.totalsByWeek.map((month) => month.reduce((sum, count) => sum + count, 0));
			const max = Math.max(...monthlyTotals);
			if (max === 0) return '—';
			const peakMonth = monthlyTotals.findIndex((count) => count === max);
			return MONTH_LABELS[peakMonth] ?? '—';
		}
		const max = Math.max(...chartData.buckets.map(b => b.count));
		const bucket = chartData.buckets.find(b => b.count === max);
		if (!bucket || max === 0) return '—';
		if (rangeMode === 'day') return getHourLabel(bucket.period as number);
		return getBucketLabel(bucket.period, rangeMode);
	}

	function peakStatName(): string {
		if (rangeMode === 'day') return 'Peak Hour';
		if (rangeMode === 'week') return 'Peak Day';
		if (rangeMode === 'month') return 'Peak Day';
		return 'Peak Month';
	}

	// ── Lifecycle ─────────────────────────────────────────────────

	let themeObserver: MutationObserver;

	onMount(async () => {
		const module = await import('chart.js/auto');
		ChartJS = module.default;
		prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

		parseInitialStateFromUrl();
		loadDates();

		themeObserver = new MutationObserver(() => {
			if (chartData) renderCharts();
		});
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class'],
		});
	});

	onDestroy(() => {
		if (mainChart) mainChart.destroy();
		if (speciesChart) speciesChart.destroy();
		if (themeObserver) themeObserver.disconnect();
	});
</script>

<svelte:head>
	<title>Insights - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Insights</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">Trends and pattern analysis</p>
	</div>

	<!-- Range Mode Tabs + Navigation -->
	<div class="card mb-6 overflow-hidden">
			<!-- Mode tabs -->
			<div class="overflow-x-auto border-b border-gray-200 px-3 py-3 dark:border-dark-border">
				<div class="flex min-w-max gap-2">
					{#each /** @type {[RangeMode, string][]} */([['day', 'Day'], ['week', 'Week'], ['month', 'Month'], ['year', 'Year']]) as [mode, label]}
						<button
							on:click={() => changeMode(mode as RangeMode)}
							class="rounded-xl px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors
								{rangeMode === mode
									? 'bg-primary-600 text-white shadow-sm'
									: 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-dark-nav dark:text-gray-300 dark:hover:bg-dark-hover'}"
						>
							{label}
						</button>
					{/each}
				</div>
			</div>

			<!-- Date navigation -->
			<div class="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
				<button on:click={() => navigate(-1)} class="btn-ghost">
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				<span class="sr-only sm:not-sr-only sm:ml-1">Previous</span>
			</button>

				<div class="flex flex-col items-center gap-1 text-center sm:flex-row sm:gap-3 sm:text-left">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
						{rangeLabel(anchorDate, rangeMode)}
					</span>
					<span class="text-xs text-gray-500 dark:text-gray-400">
						Tap or click a bar to open matching detections in Review
					</span>
					{#if anchorDate !== todayStr()}
						<button
							on:click={goToToday}
						class="text-xs text-primary-600 dark:text-primary-400 hover:underline"
					>
						Today
					</button>
				{/if}
			</div>

			<button on:click={() => navigate(1)} class="btn-ghost">
				<span class="sr-only sm:not-sr-only sm:mr-1">Next</span>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</button>
		</div>

		<!-- Day mode: date dropdown for quick jump -->
		{#if rangeMode === 'day' && availableDates.length > 0}
			<div class="px-4 pb-4">
				<select
					bind:value={anchorDate}
					on:change={loadChartData}
					class="select w-full text-sm"
				>
					{#each availableDates as date}
						<option value={date}>{date}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>

		{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
		{:else if chartData}
			<!-- Summary stats -->
			<div class="grid grid-cols-1 gap-4 mb-6 sm:grid-cols-3">
				<div class="stat-card">
					<p class="stat-value">{chartData.total_detections}</p>
					<p class="stat-label">Total Detections</p>
			</div>
			<div class="stat-card">
				<p class="stat-value">{chartData.species_count}</p>
				<p class="stat-label">Species Detected</p>
			</div>
			<div class="stat-card">
				<p class="stat-value">{peakLabel()}</p>
				<p class="stat-label">{peakStatName()}</p>
			</div>
		</div>

			<!-- Main chart -->
			<div class="card mb-6">
				<div class="card-header flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<h2 class="font-semibold text-gray-900 dark:text-gray-100">
							{rangeMode === 'day' ? 'Detections by Hour' :
							 rangeMode === 'week' ? 'Last 7 Days' :
							 rangeMode === 'month' ? 'Last 30 Days' :
							 'Monthly Detections (Weekly Breakdown)'}
						</h2>
						<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
							Select a chart bar to jump straight into the matching review queue.
						</p>
						{#if selectedSpecies.size > 0}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Showing {selectedSpecies.size} selected species
						</p>
					{/if}
				</div>
				{#if rangeMode === 'day'}
					<button
						on:click={exportEbird}
						disabled={exportLoading}
						class="btn-secondary btn-sm"
					>
						{#if exportLoading}
							<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
						{/if}
						Export to eBird
					</button>
				{/if}
			</div>
			<div class="card-body">
				{#if chartData.total_detections > 0}
					<div class="h-72">
						<canvas bind:this={mainCanvas}></canvas>
					</div>
				{:else}
					<div class="h-72 flex items-center justify-center">
						<p class="text-gray-400 dark:text-gray-500">No detections in this period</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Species breakdown -->
		{#if chartData.top_species.length > 0}
			<div class="grid md:grid-cols-3 gap-6 mb-6">
				<!-- Doughnut chart -->
				<div class="card">
					<div class="card-header">
						<h2 class="font-semibold text-gray-900 dark:text-gray-100">
							Species Distribution
						</h2>
					</div>
					<div class="card-body">
						<div class="h-56">
							<canvas bind:this={speciesCanvas}></canvas>
						</div>
					</div>
				</div>

				<!-- Top species list -->
				<div class="card md:col-span-2">
					<div class="card-header flex items-center justify-between">
						<h2 class="font-semibold text-gray-900 dark:text-gray-100">
							Top Species
						</h2>
						<div class="flex items-center gap-2">
							{#if selectedSpecies.size > 0 && rangeMode !== 'year'}
								<button
									on:click={clearSelectedSpecies}
									class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
								>
									Clear selections
								</button>
							{/if}
							<span class="text-xs text-gray-400 dark:text-gray-500">
								{rangeMode === 'year' ? 'Selection unavailable in Year view' : 'Click to show on chart'}
							</span>
						</div>
					</div>
					<div class="divide-y divide-gray-200 dark:divide-dark-border">
						{#each chartData.top_species as sp, i}
							<div class="flex items-center gap-0">
								<button
									on:click={() => toggleSpecies(sp.sci_name)}
									disabled={rangeMode === 'year'}
									class="flex items-center gap-4 flex-1 min-w-0 px-6 py-3 transition-colors
										{selectedSpecies.has(sp.sci_name)
											? 'bg-gray-100 dark:bg-dark-border'
											: 'hover:bg-gray-50 dark:hover:bg-dark-border/50'}
										disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:bg-transparent"
									title="Toggle {sp.com_name} on chart"
								>
									<span
										class="w-3 h-3 rounded-full flex-shrink-0 transition-all
											{selectedSpecies.has(sp.sci_name) ? 'ring-2 ring-offset-2 ring-offset-white dark:ring-offset-gray-800' : ''}"
										style="background-color: {SPECIES_COLORS[i % SPECIES_COLORS.length]};
											{selectedSpecies.has(sp.sci_name) ? `ring-color: ${SPECIES_COLORS[i % SPECIES_COLORS.length]}` : ''}"></span>
									<div class="flex-1 min-w-0 text-left">
										<p class="font-medium text-gray-900 dark:text-gray-100 truncate">{sp.com_name}</p>
										<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate">{sp.sci_name}</p>
									</div>
									<div class="flex items-center gap-4 flex-shrink-0">
										<span class="badge-primary">{(sp.max_confidence * 100).toFixed(0)}%</span>
										<div class="text-right">
											<span class="text-lg font-semibold text-primary-600 dark:text-primary-400">{sp.count}</span>
										</div>
									</div>
								</button>
								<div class="px-3 py-3 flex items-center gap-2 flex-shrink-0">
									<ExternalLinks sciName={sp.sci_name} comName={sp.com_name} compact={true} />
									<a
										href="/species/{encodeURIComponent(sp.sci_name)}"
										class="text-gray-400 hover:text-primary-500 dark:text-gray-500 dark:hover:text-primary-400 transition-colors"
										title="View {sp.com_name} details"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
										</svg>
									</a>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		<!-- View detections link (day mode) -->
		{#if rangeMode === 'day'}
			<div class="text-center">
				<a
					href="/detections?date={anchorDate}"
					class="text-primary-600 dark:text-primary-400 hover:underline"
				>
					Open Review for {anchorDate} →
				</a>
			</div>
		{/if}
	{:else}
		<div class="card p-8 text-center">
			<p class="text-gray-600 dark:text-gray-400">No detection history available</p>
		</div>
	{/if}
</div>
