<script lang="ts">
import { goto } from '$app/navigation';
	import { createEventDispatcher } from 'svelte';
	import type { Detection, SpeciesExternalLinks } from '$lib/api';
	import { media } from '$lib/api';
	import AudioPlayer from './AudioPlayer.svelte';
	import ExternalLinks from './ExternalLinks.svelte';
	import SpeciesImage from './SpeciesImage.svelte';

	export let detection: Detection;
	export let showDate: boolean = true;
	export let showImage: boolean = true;
	export let href: string | null = null;
	export let allowDelete: boolean = false;
	export let deleting: boolean = false;
	export let speciesLinks: SpeciesExternalLinks | null = null;

	const dispatch = createEventDispatcher<{ delete: Detection }>();

	$: audioUrl = media.audioUrl(detection.Date, detection.Sci_Name, detection.File_Name);
	$: spectrogramUrl = media.spectrogramUrl(detection.Date, detection.Sci_Name, detection.File_Name);

	function formatTime(time: string): string {
		return time.slice(0, 5); // HH:MM
	}

	function formatConfidence(confidence: number): string {
		return `${(confidence * 100).toFixed(0)}%`;
	}

	function shouldIgnoreCardNav(target: HTMLElement): boolean {
		return Boolean(
			target.closest('button, a, audio, input, select, textarea, summary, [data-no-card-link]')
		);
	}

	function handleCardClick(event: MouseEvent) {
		if (!href) return;
		const target = event.target as HTMLElement;
		if (shouldIgnoreCardNav(target)) return;
		void goto(href);
	}

	function handleCardKeydown(event: KeyboardEvent) {
		if (!href) return;
		if (event.key !== 'Enter' && event.key !== ' ') return;
		const target = event.target as HTMLElement;
		if (shouldIgnoreCardNav(target)) return;
		event.preventDefault();
		void goto(href);
	}

	function handleDeleteClick(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		dispatch('delete', detection);
	}
</script>

<div
	class="card w-full max-w-full p-4 fade-in {href ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}"
	role={href ? 'link' : undefined}
	on:click={handleCardClick}
	on:keydown={handleCardKeydown}
>
	<div class="flex gap-4">
		<!-- Bird Image -->
		{#if showImage}
			<div class="w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-gray-200 dark:bg-dark-border">
				<SpeciesImage sciName={detection.Sci_Name} size="sm" />
			</div>
		{/if}

		<!-- Detection Info -->
		<div class="flex-1 min-w-0">
			<div class="flex items-start justify-between gap-2">
				<div>
					<h3 class="font-semibold text-gray-900 dark:text-gray-100 truncate">
						{detection.Com_Name}
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate">
						{detection.Sci_Name}
					</p>
				</div>
				<div class="flex items-center gap-2 flex-shrink-0" data-no-card-link>
					<ExternalLinks links={speciesLinks} compact={true} />
					<span class="badge-primary">
						{formatConfidence(detection.Confidence)}
					</span>
					{#if allowDelete}
						<button
							class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
							data-no-card-link
							on:click={handleDeleteClick}
							disabled={deleting}
							title="Delete detection and recording"
							aria-label="Delete detection and recording"
						>
							{#if deleting}
								<span class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
							{:else}
								<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M8 6V4h8v2m-9 0 1 14h8l1-14" />
								</svg>
							{/if}
						</button>
					{/if}
				</div>
			</div>

			<div class="mt-2 flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
				{#if showDate}
					<span>{detection.Date}</span>
				{/if}
				<span>{formatTime(detection.Time)}</span>
			</div>
		</div>
	</div>

	<!-- Spectrogram -->
	<div class="mt-3">
		<img
			src={spectrogramUrl}
			alt="Spectrogram for {detection.Com_Name}"
			class="w-full h-24 object-cover rounded-lg bg-gray-200 dark:bg-dark-border"
			loading="lazy"
		/>
	</div>

	<!-- Audio Player -->
	<div class="mt-3">
		<AudioPlayer src={audioUrl} filename={detection.File_Name} />
	</div>
</div>
