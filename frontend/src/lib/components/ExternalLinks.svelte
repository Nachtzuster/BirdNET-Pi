<script lang="ts">
	import type { SpeciesExternalLinks } from '$lib/api';

	export let links: SpeciesExternalLinks | null = null;
	export let compact: boolean = true;
</script>

{#if links}
	{#if compact}
		<div class="inline-flex items-center gap-1" data-no-card-link>
			{#if links.ebird.url}
				<a
					href={links.ebird.url}
					target="_blank"
					rel="noopener noreferrer"
					title="Open on eBird"
					aria-label="Open on eBird"
					class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-white/90 dark:bg-dark-card border border-gray-300 dark:border-dark-border hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=ebird.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
				</a>
			{/if}
			{#if links.allaboutbirds.url}
				<a
					href={links.allaboutbirds.url}
					target="_blank"
					rel="noopener noreferrer"
					title="Open on All About Birds"
					aria-label="Open on All About Birds"
					class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-white/90 dark:bg-dark-card border border-gray-300 dark:border-dark-border hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=allaboutbirds.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
				</a>
			{/if}
		</div>
	{:else}
		<div class="mt-4 flex flex-wrap gap-2">
			{#if links.ebird.url}
				<a
					href={links.ebird.url}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-dark-border px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=ebird.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
					<span>eBird</span>
				</a>
			{/if}
			{#if links.allaboutbirds.url}
				<a
					href={links.allaboutbirds.url}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-dark-border px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=allaboutbirds.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
					<span>All About Birds</span>
				</a>
			{/if}
		</div>
	{/if}
{/if}
