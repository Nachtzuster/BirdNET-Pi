<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { detections, health, species as speciesApi, system as systemApi, type Detection, type DetectionStats, type SpeciesSummary, type RangeChartData } from '$lib/api';
	import { StatsCard, DetectionCard, ExternalLinks, SpeciesImage, Modal } from '$lib/components';
	import { auth, toasts } from '$lib/stores';

	let ChartJS: typeof import('chart.js/auto').default;

	let stats: DetectionStats | null = null;
	let topSpeciesToday: SpeciesSummary[] = [];
	let topSpeciesAllTime: SpeciesSummary[] = [];
	let topSpeciesMode: 'today' | 'all' = 'today';
	let topSpeciesExpanded = false;

	const TOP_SPECIES_PREVIEW = 6;
	let siteName: string = 'BirdNET-Pi';
	let loading = true;
	let refreshInterval: ReturnType<typeof setInterval>;

	let hourlyData: RangeChartData | null = null;
	let sparkCanvas: HTMLCanvasElement;
	let sparkChart: any = null;
	let isDark = false;
	type DetectionGroup = {
		sciName: string;
		comName: string;
		latest: Detection;
		count: number;
		detections: Detection[];
	};
	let groupedDetections: DetectionGroup[] = [];
	let newSpeciesTodayDetections: Detection[] = [];
	let newSpeciesTodaySet: Set<string> = new Set();
	let prefersReducedMotion = false;
	let liveAudioUrl = '';
	let liveAudioExpiresAt = '';
	let liveAudioLoading = false;
	let liveAudioVisible = false;
	let showLiveAudioLoginModal = false;
	let liveAudioPassword = '';
	let liveAudioElement: HTMLAudioElement | null = null;

	function detectTheme() {
		isDark = document.documentElement.classList.contains('dark');
	}

	function todayStr(): string {
		const d = new Date();
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function groupLatest(items: Detection[]): DetectionGroup[] {
		const grouped = new Map<string, DetectionGroup>();
		for (const detection of items) {
			const existing = grouped.get(detection.Sci_Name);
			if (existing) {
				existing.count += 1;
				existing.detections.push(detection);
			} else {
				grouped.set(detection.Sci_Name, {
					sciName: detection.Sci_Name,
					comName: detection.Com_Name,
					latest: detection,
					count: 1,
					detections: [detection],
				});
			}
		}
		return Array.from(grouped.values());
	}

	function detectionTimestamp(detection: Detection): number {
		return new Date(`${detection.Date}T${detection.Time}`).getTime();
	}

	function sortDetectionGroups(groups: DetectionGroup[], pinnedSpecies: Set<string>): DetectionGroup[] {
		return [...groups].sort((a, b) => {
			const aPinned = pinnedSpecies.has(a.sciName);
			const bPinned = pinnedSpecies.has(b.sciName);
			if (aPinned !== bPinned) return aPinned ? -1 : 1;
			return detectionTimestamp(b.latest) - detectionTimestamp(a.latest);
		});
	}

	function uniqueDetections(items: Detection[]): Detection[] {
		const byKey = new Map<string, Detection>();
		for (const detection of items) {
			const key = `${detection.Date}|${detection.Time}|${detection.Sci_Name}|${detection.File_Name}`;
			if (!byKey.has(key)) byKey.set(key, detection);
		}
		return Array.from(byKey.values());
	}

	function isPinnedNewSpecies(sciName: string): boolean {
		return newSpeciesTodaySet.has(sciName);
	}

	function detectionsHref(detection: Detection, options?: { newOnDate?: boolean }): string {
		const params = new URLSearchParams({
			date: detection.Date,
			species: detection.Sci_Name,
		});
		if (options?.newOnDate) params.set('new_on_date', 'true');
		return `/detections?${params.toString()}`;
	}

	function insightsHref(scope: string): string {
		if (scope === 'species_today') return '/species?date=today';
		if (scope === 'all_species') return '/species';
		const params = new URLSearchParams({
			mode: 'day',
			date: todayStr(),
			scope,
		});
		return `/history?${params.toString()}`;
	}

	$: displayedTopSpecies = topSpeciesMode === 'today' ? topSpeciesToday : topSpeciesAllTime;
	$: visibleTopSpecies = topSpeciesExpanded
		? displayedTopSpecies
		: displayedTopSpecies.slice(0, TOP_SPECIES_PREVIEW);
	$: canExpandTopSpecies = displayedTopSpecies.length > TOP_SPECIES_PREVIEW;
	$: speciesViewAllHref = topSpeciesMode === 'today' ? `/species?date=today` : '/species';

	function setTopSpeciesMode(mode: 'today' | 'all') {
		topSpeciesMode = mode;
		topSpeciesExpanded = false;
	}

	async function loadData() {
		if (typeof document !== 'undefined' && document.hidden) return;

		try {
			const today = todayStr();
			const [statsData, detectionsData, newSpeciesData, infoData, speciesTodayData, speciesAllTimeData, hourly] = await Promise.all([
				detections.stats(),
				detections.today({ limit: 24 }),
				detections.newSpeciesToday(),
				health.info(),
				speciesApi.list({ sort: 'count', date: today }),
				speciesApi.list({ sort: 'count' }),
				detections.chartDataRange({ start: today, end: today, group_by: 'hour' }),
			]);

			const pinnedSpecies = new Set(newSpeciesData.map((detection) => detection.Sci_Name));
			const mergedDetections = uniqueDetections([...newSpeciesData, ...detectionsData.detections]);

			stats = statsData;
			newSpeciesTodayDetections = newSpeciesData;
			newSpeciesTodaySet = pinnedSpecies;
			groupedDetections = sortDetectionGroups(groupLatest(mergedDetections), pinnedSpecies);
			siteName = infoData.site_name;
			topSpeciesToday = speciesTodayData.species;
			topSpeciesAllTime = speciesAllTimeData.species;
			topSpeciesExpanded = false;
			hourlyData = hourly;
		} catch (e) {
			console.error('Failed to load data:', e);
			toasts.show('Failed to load data', 'error');
		} finally {
			loading = false;
		}
		await tick();
		renderSparkline();
	}

	function getHourLabel(hour: number): string {
		if (hour === 0) return '12am';
		if (hour === 12) return '12pm';
		return hour < 12 ? `${hour}am` : `${hour - 12}pm`;
	}

	function renderSparkline() {
		if (!hourlyData || !ChartJS || !sparkCanvas) return;
		detectTheme();

		if (sparkChart) sparkChart.destroy();

		const labels = hourlyData.buckets.map(b => getHourLabel(b.period as number));
		const counts = hourlyData.buckets.map(b => b.count);
		const maxCount = Math.max(...counts);

		const barColor = isDark ? 'rgba(34,197,94,0.6)' : 'rgba(22,163,74,0.7)';
		const barHover = isDark ? 'rgba(34,197,94,0.85)' : 'rgba(22,163,74,0.9)';
		const textColor = isDark ? '#9ca3af' : '#6b7280';
		const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

		// Find peak hour
		const peakIdx = counts.indexOf(maxCount);
		const bgColors = counts.map((_, i) =>
			i === peakIdx && maxCount > 0 ? (isDark ? 'rgba(250,204,21,0.7)' : 'rgba(202,138,4,0.7)') : barColor
		);

		const speciesBreakdownByHour = hourlyData.species_buckets.map((species) => ({
			comName: species.com_name,
			counts: species.counts,
		}));

		sparkChart = new ChartJS(sparkCanvas, {
			type: 'bar',
			data: {
				labels,
				datasets: [{
					data: counts,
					backgroundColor: bgColors,
					hoverBackgroundColor: barHover,
					borderRadius: 3,
					borderSkipped: false,
				}],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				animation: { duration: prefersReducedMotion ? 0 : 120, easing: 'linear' },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: isDark ? '#1f2937' : '#fff',
						titleColor: textColor,
						bodyColor: isDark ? '#d1d5db' : '#374151',
						borderColor: gridColor,
						borderWidth: 1,
						padding: 8,
						cornerRadius: 6,
							displayColors: false,
							callbacks: {
								title: (items) => items[0]?.label || '',
								label: (ctx) => `Total: ${ctx.parsed.y} detection${ctx.parsed.y !== 1 ? 's' : ''}`,
								afterLabel: (ctx) => {
									const bucketIdx = ctx.dataIndex;
									const breakdown = speciesBreakdownByHour
										.map((entry) => ({ comName: entry.comName, count: entry.counts[bucketIdx] || 0 }))
										.filter((entry) => entry.count > 0)
										.sort((a, b) => b.count - a.count);

									if (breakdown.length === 0) return ['No species'];

									const top = breakdown.slice(0, 4).map((entry) => `${entry.comName}: ${entry.count}`);
									const otherCount = breakdown.slice(4).reduce((sum, entry) => sum + entry.count, 0);
									return otherCount > 0 ? [...top, `Other: ${otherCount}`] : top;
								},
							},
						},
					},
				scales: {
					x: {
						grid: { display: false },
						ticks: {
							color: textColor,
							font: { size: 10 },
							maxRotation: 0,
							callback: function(_value, index) {
								return index % 6 === 0 ? labels[index] : '';
							},
						},
					},
					y: {
						display: false,
						beginAtZero: true,
					},
				},
			},
			});
	}

	function clearLiveAudio() {
		liveAudioVisible = false;
		liveAudioUrl = '';
		liveAudioExpiresAt = '';
		if (liveAudioElement) {
			liveAudioElement.pause();
			liveAudioElement.load();
		}
	}

	async function requestLiveAudioUrl(): Promise<boolean> {
		liveAudioLoading = true;
		try {
			const stream = await systemApi.liveStreamUrl(auth.getCredentials());
			liveAudioUrl = stream.url;
			liveAudioExpiresAt = stream.expires_at;
			liveAudioVisible = true;
			return true;
		} catch (error: any) {
			if (error?.status === 401) {
				auth.logout();
				showLiveAudioLoginModal = true;
				toasts.show('Authentication required for live audio', 'warning');
			} else {
				console.error('Failed to prepare live audio:', error);
				toasts.show('Live audio is unavailable', 'error');
			}
			return false;
		} finally {
			liveAudioLoading = false;
		}
	}

	async function openLiveAudio() {
		if (!$auth.isAuthenticated) {
			showLiveAudioLoginModal = true;
			return;
		}

		await requestLiveAudioUrl();
	}

	async function handleLiveAudioLogin() {
		if (!liveAudioPassword.trim()) return;

		auth.login(liveAudioPassword);
		const ready = await requestLiveAudioUrl();
		if (ready) {
			showLiveAudioLoginModal = false;
			liveAudioPassword = '';
			toasts.show('Authenticated for live audio', 'success');
		} else {
			auth.logout();
		}
	}

	let themeObserver: MutationObserver;
	let visibilityHandler: (() => void) | undefined;

	onMount(async () => {
		const module = await import('chart.js/auto');
		ChartJS = module.default;
		prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

		void loadData();
		refreshInterval = setInterval(() => {
			if (document.hidden) return;
			void loadData();
		}, 60000);

		visibilityHandler = () => {
			if (!document.hidden) void loadData();
		};
		document.addEventListener('visibilitychange', visibilityHandler);

		themeObserver = new MutationObserver(() => {
			if (hourlyData) renderSparkline();
		});
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class'],
		});
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
		if (sparkChart) sparkChart.destroy();
		if (themeObserver) themeObserver.disconnect();
		if (visibilityHandler) document.removeEventListener('visibilitychange', visibilityHandler);
		if (liveAudioElement) {
			liveAudioElement.pause();
		}
	});
</script>

<svelte:head>
	<title>{siteName} - Dashboard</title>
</svelte:head>

<div class="container mx-auto px-4 py-6 overflow-x-hidden">
	<!-- Header -->
	<div class="mb-8">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
				{siteName}
			</h1>
			<a href="/detections" class="btn-primary">Review Detections</a>
		</div>
		<p class="text-gray-600 dark:text-gray-400 mt-1">
			What's happening now
		</p>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Stats Grid -->
		<div class="grid grid-cols-3 md:grid-cols-6 gap-3 mb-8">
			<StatsCard
				value={stats?.total_count || 0}
				label="Total"
				icon="total"
				href={insightsHref('total')}
				compact={true}
			/>
			<StatsCard
				value={stats?.todays_count || 0}
				label="Today"
				icon="today"
				href={insightsHref('today')}
				compact={true}
			/>
			<StatsCard
				value={stats?.hour_count || 0}
				label="Last Hour"
				icon="hour"
				href={insightsHref('hour')}
				compact={true}
			/>
			<StatsCard
				value={stats?.new_species_today || 0}
				label="New Species"
				icon="new"
				href={insightsHref('new_species_today')}
				compact={true}
			/>
			<StatsCard
				value={stats?.todays_species_tally || 0}
				label="Species Today"
				icon="species"
				href={insightsHref('species_today')}
				compact={true}
			/>
			<StatsCard
				value={stats?.species_tally || 0}
				label="All Species"
				icon="species"
				href={insightsHref('all_species')}
				compact={true}
			/>
		</div>

		{#if newSpeciesTodayDetections.length > 0}
			<div class="card mb-6 border-l-4 border-emerald-500">
				<div class="card-header flex items-center justify-between">
					<h3 class="font-semibold text-gray-900 dark:text-gray-100">New Species Today</h3>
					<span class="badge-primary">{newSpeciesTodayDetections.length}</span>
				</div>
				<div class="card-body">
					<div class="grid gap-3 md:grid-cols-2">
						{#each newSpeciesTodayDetections as detection (detection.Sci_Name)}
							<div class="flex items-center justify-between gap-3 rounded-lg border border-gray-200 dark:border-dark-border p-3">
								<div class="min-w-0">
									<a href="/species/{encodeURIComponent(detection.Sci_Name)}" class="font-medium text-gray-900 dark:text-gray-100 hover:underline truncate block">
										{detection.Com_Name}
									</a>
									<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate">{detection.Sci_Name}</p>
								</div>
								<a href={detectionsHref(detection, { newOnDate: true })} class="text-xs text-primary-600 dark:text-primary-400 hover:underline whitespace-nowrap">
									Open Review →
								</a>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		<!-- Live indicator -->
		<div class="flex items-center gap-2 mb-4">
			<span class="w-3 h-3 bg-green-500 rounded-full pulse-live"></span>
			<span class="text-sm text-gray-600 dark:text-gray-400">
				Live - Refreshes every 60 seconds while this tab is visible
			</span>
		</div>

		<!-- Today's Activity Chart -->
		<div class="card mb-8">
			<div class="card-header flex items-center justify-between">
				<div>
					<h3 class="font-semibold text-gray-900 dark:text-gray-100">Today's Activity</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Detections by hour</p>
				</div>
				<a href={insightsHref('today')} class="text-primary-600 dark:text-primary-400 hover:underline text-sm">
					Open Insights →
				</a>
			</div>
			<div class="card-body">
				{#if hourlyData && hourlyData.total_detections > 0}
					<div class="h-32">
						<canvas bind:this={sparkCanvas}></canvas>
					</div>
				{:else}
					<div class="h-32 flex items-center justify-center">
						<p class="text-sm text-gray-400 dark:text-gray-500">No activity recorded today yet</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Top Species -->
		<div class="card mb-8">
				<div class="card-header flex items-center justify-between">
					<div class="flex items-center gap-3">
						<h3 class="font-semibold text-gray-900 dark:text-gray-100">Top Species</h3>
						<div class="inline-flex rounded-lg border border-gray-200 dark:border-dark-border overflow-hidden text-xs">
							<button
								type="button"
								class="px-3 py-1 {topSpeciesMode === 'today' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300'}"
								on:click={() => setTopSpeciesMode('today')}
							>
								Today
							</button>
							<button
								type="button"
								class="px-3 py-1 {topSpeciesMode === 'all' ? 'bg-primary-600 text-white' : 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300'}"
								on:click={() => setTopSpeciesMode('all')}
							>
								All time
							</button>
						</div>
					</div>
					<div class="flex items-center gap-3">
						{#if canExpandTopSpecies}
							<button
								type="button"
								class="text-primary-600 dark:text-primary-400 hover:underline text-sm"
								on:click={() => (topSpeciesExpanded = !topSpeciesExpanded)}
							>
								{topSpeciesExpanded ? 'Show less' : `Show all ${displayedTopSpecies.length}`}
							</button>
						{/if}
						<a href={speciesViewAllHref} class="text-primary-600 dark:text-primary-400 hover:underline text-sm">
							{topSpeciesMode === 'today' ? 'Species today →' : 'View all →'}
						</a>
					</div>
				</div>
				{#if displayedTopSpecies.length === 0}
					<div class="card-body text-center py-8">
						<svg class="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<p class="text-gray-500 dark:text-gray-400">
							{topSpeciesMode === 'today' ? 'No species detected today yet' : 'No species detected yet'}
						</p>
						<p class="text-sm text-gray-400 dark:text-gray-500 mt-1">
							{topSpeciesMode === 'today' ? 'Check back after more detections today' : 'Species will appear here as they are identified'}
						</p>
					</div>
				{:else}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 divide-y sm:divide-y-0 divide-gray-200 dark:divide-dark-border">
						{#each visibleTopSpecies as sp (sp.Sci_Name)}
							<div class="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 dark:hover:bg-dark-border transition-colors">
								<div class="flex-shrink-0 rounded-full overflow-hidden">
									<SpeciesImage sciName={sp.Sci_Name} size="xs" />
								</div>
								<div class="flex-1 min-w-0">
									<a href="/species/{encodeURIComponent(sp.Sci_Name)}" class="block">
										<p class="font-medium text-gray-900 dark:text-gray-100 truncate hover:underline">{sp.Com_Name}</p>
										<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate">{sp.Sci_Name}</p>
									</a>
									<div class="mt-1">
										<ExternalLinks sciName={sp.Sci_Name} comName={sp.Com_Name} compact={true} />
									</div>
								</div>
								<div class="flex-shrink-0 text-right">
									<span class="text-lg font-semibold text-primary-600 dark:text-primary-400">{sp.Count}</span>
									<p class="text-xs text-gray-500 dark:text-gray-400">{sp.Count === 1 ? 'detection' : 'detections'}</p>
								</div>
							</div>
						{/each}
					</div>
				{/if}
		</div>

		<!-- Latest Detections -->
		<div class="mb-8">
			<div class="flex items-center justify-between mb-2">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
					Latest Detections
				</h2>
				<a href="/detections" class="text-primary-600 dark:text-primary-400 hover:underline text-sm">
					Open Review →
				</a>
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
				Group view by species to reduce duplicate-card clutter. New species are pinned first.
			</p>

			{#if groupedDetections.length === 0}
				<div class="card p-8 text-center">
					<svg class="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
					</svg>
					<p class="text-gray-600 dark:text-gray-400">No detections today yet</p>
					<p class="text-sm text-gray-500 dark:text-gray-500 mt-1">
						Detections will appear here as birds are identified
					</p>
				</div>
			{:else}
				<div class="grid gap-4 md:grid-cols-2">
					{#each groupedDetections as group (group.sciName)}
						<DetectionCard
							detection={group.latest}
							showDate={false}
							href={detectionsHref(group.latest, { newOnDate: isPinnedNewSpecies(group.sciName) })}
							allowSpectrogramExpand={false}
							tagLabel={isPinnedNewSpecies(group.sciName) ? 'New species today' : null}
							groupedCount={group.count}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<div class="card p-4 space-y-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div>
					<p class="text-sm font-medium text-gray-900 dark:text-gray-100">Explore more</p>
					<p class="text-xs text-gray-500 dark:text-gray-400">Open historical files, trend analysis, or listen live</p>
				</div>
				<div class="flex flex-wrap items-center gap-2">
					<a href="/recordings" class="btn-secondary btn-sm">Open Library</a>
					<a href="/history" class="btn-secondary btn-sm">Open Insights</a>
					<button class="btn-secondary btn-sm" on:click={openLiveAudio} disabled={liveAudioLoading}>
						{#if liveAudioLoading}
							<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
						{/if}
						Listen Live
					</button>
				</div>
			</div>
			{#if liveAudioVisible && liveAudioUrl}
				<div class="rounded-lg border border-gray-200 dark:border-dark-border p-3">
					<div class="flex flex-wrap items-center justify-between gap-3 mb-2">
						<div>
							<p class="text-sm font-medium text-gray-900 dark:text-gray-100">Live Audio</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">
								Access expires at {new Date(liveAudioExpiresAt).toLocaleTimeString()}
							</p>
						</div>
						<button class="btn-secondary btn-sm" on:click={clearLiveAudio}>Hide</button>
					</div>
					<audio bind:this={liveAudioElement} class="w-full" controls preload="none" src={liveAudioUrl}></audio>
				</div>
			{/if}
		</div>
	{/if}
</div>

<Modal bind:open={showLiveAudioLoginModal} title="Live Audio Authentication">
	<form on:submit|preventDefault={handleLiveAudioLogin} class="space-y-4">
		<div>
			<label for="liveAudioPassword" class="label">Password</label>
			<input
				id="liveAudioPassword"
				type="password"
				bind:value={liveAudioPassword}
				class="input"
				placeholder="Enter password"
			/>
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLiveAudioLoginModal = false)} class="btn-secondary">
				Cancel
			</button>
			<button type="submit" class="btn-primary" disabled={liveAudioLoading}>
				{#if liveAudioLoading}
					<span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2"></span>
				{/if}
				Authenticate
			</button>
		</div>
	</form>
</Modal>
