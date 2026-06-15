<script context="module" lang="ts">
	import { integrations, type BirdImage } from '$lib/api';

	const imageCache = new Map<string, BirdImage | null>();
	const imageRequests = new Map<string, Promise<BirdImage | null>>();

	function imageCacheKey(sciName: string): string {
		return sciName.trim();
	}

	async function loadSpeciesImage(sciName: string): Promise<BirdImage | null> {
		const key = imageCacheKey(sciName);
		if (!key) return null;

		if (imageCache.has(key)) {
			return imageCache.get(key) ?? null;
		}

		let request = imageRequests.get(key);
		if (!request) {
			request = integrations
				.image(sciName)
				.then((result) => {
					const image = result ?? null;
					imageCache.set(key, image);
					imageRequests.delete(key);
					return image;
				})
				.catch((error) => {
					imageRequests.delete(key);
					throw error;
				});
			imageRequests.set(key, request);
		}

		return request;
	}
</script>

<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let sciName: string;
	export let size: 'xs' | 'sm' | 'md' | 'lg' = 'md';

	let imageData: BirdImage | null = null;
	let loading = true;
	let error = false;
	let container: HTMLDivElement | null = null;
	let observer: IntersectionObserver | undefined;
	let loadStarted = false;

	const sizeClasses = {
		xs: 'w-10 h-10',
		sm: 'w-20 h-20',
		md: 'w-32 h-32',
		lg: 'w-48 h-48',
	};

	async function loadImage() {
		if (loadStarted) return;
		loadStarted = true;

		try {
			imageData = await loadSpeciesImage(sciName);
		} catch (e) {
			error = true;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const key = imageCacheKey(sciName);
		if (!key) {
			loading = false;
			return;
		}

		if (imageCache.has(key)) {
			imageData = imageCache.get(key) ?? null;
			loading = false;
			return;
		}

		if (!container || typeof IntersectionObserver === 'undefined') {
			void loadImage();
			return;
		}

		observer = new IntersectionObserver((entries) => {
			for (const entry of entries) {
				if (!entry.isIntersecting) continue;
				void loadImage();
				observer?.disconnect();
				observer = undefined;
				break;
			}
		}, { rootMargin: '600px' });

		observer.observe(container);
	});

	onDestroy(() => {
		observer?.disconnect();
	});
</script>

<div bind:this={container} class="{sizeClasses[size]} bg-gray-200 dark:bg-dark-card rounded-lg overflow-hidden">
	{#if loading}
		<div class="w-full h-full flex items-center justify-center">
			<div class="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if imageData}
		<img
			src={imageData.url}
			alt={sciName}
			class="w-full h-full object-cover"
			loading="lazy"
		/>
	{:else}
		<div class="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-600">
			<svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
				<path d="M12 2C7.58 2 4 5.58 4 10c0 3.31 2.69 6 6 6h1v4l3-3 3 3v-4h1c3.31 0 6-2.69 6-6 0-4.42-3.58-8-8-8zm-2 9a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm4 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
			</svg>
		</div>
	{/if}
</div>
