<script lang="ts">
	export let value: number | string;
	export let label: string;
	export let icon: 'total' | 'today' | 'hour' | 'species' | 'new' = 'total';
	export let trend: 'up' | 'down' | 'none' = 'none';
	export let href: string | null = null;
	export let compact = false;

	const iconPaths = {
		total: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
		today: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
		hour: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
		species: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
		new: 'M12 3l2.5 5.5L20 10l-4 4.5.9 6L12 18l-4.9 2.5.9-6L4 10l5.5-1.5L12 3z',
	};
</script>

{#if href}
	<a href={href} class="stat-card {compact ? 'stat-card-compact' : ''} block hover:shadow-lg transition-shadow">
		<div class="flex items-start justify-between gap-2">
			<div>
				<p class="stat-value">{value}</p>
				<p class="stat-label">{label}</p>
			</div>
			<div class="flex-shrink-0 {compact ? 'p-1.5' : 'p-2'} bg-primary-100 dark:bg-primary-900 rounded-lg">
				<svg class="{compact ? 'w-5 h-5' : 'w-6 h-6'} text-primary-600 dark:text-primary-400 overflow-visible" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={iconPaths[icon]} />
				</svg>
			</div>
		</div>
		{#if trend !== 'none'}
			<div class="mt-2 flex items-center gap-1 text-sm {trend === 'up' ? 'text-green-600' : 'text-red-600'}">
				{#if trend === 'up'}
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
					</svg>
				{:else}
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
					</svg>
				{/if}
			</div>
		{/if}
	</a>
{:else}
	<div class="stat-card {compact ? 'stat-card-compact' : ''}">
		<div class="flex items-start justify-between gap-2">
			<div>
				<p class="stat-value">{value}</p>
				<p class="stat-label">{label}</p>
			</div>
			<div class="flex-shrink-0 {compact ? 'p-1.5' : 'p-2'} bg-primary-100 dark:bg-primary-900 rounded-lg">
				<svg class="{compact ? 'w-5 h-5' : 'w-6 h-6'} text-primary-600 dark:text-primary-400 overflow-visible" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={iconPaths[icon]} />
				</svg>
			</div>
		</div>
		{#if trend !== 'none'}
			<div class="mt-2 flex items-center gap-1 text-sm {trend === 'up' ? 'text-green-600' : 'text-red-600'}">
				{#if trend === 'up'}
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
					</svg>
				{:else}
					<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
					</svg>
				{/if}
			</div>
		{/if}
	</div>
{/if}
