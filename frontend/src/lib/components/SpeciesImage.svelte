<script lang="ts">
	import { onMount } from 'svelte';
	import { integrations, type BirdImage } from '$lib/api';

	export let sciName: string;
	export let size: 'xs' | 'sm' | 'md' | 'lg' = 'md';

	let imageData: BirdImage | null = null;
	let loading = true;
	let error = false;

	const sizeClasses = {
		xs: 'w-10 h-10',
		sm: 'w-20 h-20',
		md: 'w-32 h-32',
		lg: 'w-48 h-48',
	};

	onMount(async () => {
		try {
			imageData = await integrations.image(sciName);
		} catch (e) {
			error = true;
		} finally {
			loading = false;
		}
	});
</script>

<div class="{sizeClasses[size]} bg-gray-200 dark:bg-dark-card rounded-lg overflow-hidden">
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
