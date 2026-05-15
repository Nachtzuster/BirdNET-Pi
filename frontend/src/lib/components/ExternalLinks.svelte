<script context="module" lang="ts">
	import type { SpeciesExternalLinks as CachedSpeciesExternalLinks } from '$lib/api';
	const linkCache = new Map<string, CachedSpeciesExternalLinks | null>();
	const linkRequests = new Map<string, Promise<CachedSpeciesExternalLinks | null>>();
</script>

<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { integrations, type SpeciesExternalLinks } from '$lib/api';

	export let links: SpeciesExternalLinks | null = null;
	export let compact: boolean = true;
	export let sciName: string | null = null;
	export let comName: string | null = null;

	let resolvedLinks: SpeciesExternalLinks | null = links;
	let container: HTMLSpanElement | HTMLDivElement | null = null;
	let observer: IntersectionObserver | undefined;

	$: resolvedLinks = links ?? resolvedLinks;

	function cacheKey(): string | null {
		return sciName ? `${sciName}|${comName ?? ''}` : null;
	}

	async function loadLinks() {
		if (resolvedLinks || !sciName) return;

		const key = cacheKey();
		if (!key) return;

		if (linkCache.has(key)) {
			resolvedLinks = linkCache.get(key) ?? null;
			return;
		}

		let request = linkRequests.get(key);
		if (!request) {
			request = integrations
				.speciesLinks(sciName, comName || undefined)
				.then((result) => {
					linkCache.set(key, result);
					linkRequests.delete(key);
					return result;
				})
				.catch(() => {
					linkCache.set(key, null);
					linkRequests.delete(key);
					return null;
				});
			linkRequests.set(key, request);
		}

		resolvedLinks = await request;
	}

	onMount(() => {
		if (resolvedLinks || !sciName || !container) return;

		if (typeof IntersectionObserver === 'undefined') {
			void loadLinks();
			return;
		}

		observer = new IntersectionObserver((entries) => {
			for (const entry of entries) {
				if (!entry.isIntersecting) continue;
				void loadLinks();
				observer?.disconnect();
				observer = undefined;
				break;
			}
		}, { rootMargin: '120px' });

		observer.observe(container);
	});

	onDestroy(() => {
		observer?.disconnect();
	});
</script>

{#if compact}
	<span bind:this={container} class="inline-flex items-center gap-1" data-no-card-link>
		{#if resolvedLinks}
			{#if resolvedLinks.ebird.url}
				<a
					href={resolvedLinks.ebird.url}
					target="_blank"
					rel="noopener noreferrer"
					title="Open on eBird"
					aria-label="Open on eBird"
					class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-white/90 dark:bg-dark-card border border-gray-300 dark:border-dark-border hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=ebird.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
				</a>
			{/if}
			{#if resolvedLinks.allaboutbirds.url}
				<a
					href={resolvedLinks.allaboutbirds.url}
					target="_blank"
					rel="noopener noreferrer"
					title="Open on All About Birds"
					aria-label="Open on All About Birds"
					class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-white/90 dark:bg-dark-card border border-gray-300 dark:border-dark-border hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=allaboutbirds.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
				</a>
			{/if}
		{/if}
	</span>
{:else}
	<div bind:this={container} class="mt-4 flex flex-wrap gap-2">
		{#if resolvedLinks}
			{#if resolvedLinks.ebird.url}
				<a
					href={resolvedLinks.ebird.url}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-dark-border px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=ebird.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
					<span>eBird</span>
				</a>
			{/if}
			{#if resolvedLinks.allaboutbirds.url}
				<a
					href={resolvedLinks.allaboutbirds.url}
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-dark-border px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-hover"
				>
					<img src="https://www.google.com/s2/favicons?domain=allaboutbirds.org&sz=32" alt="" class="h-4 w-4" loading="lazy" />
					<span>All About Birds</span>
				</a>
			{/if}
		{/if}
	</div>
{/if}
