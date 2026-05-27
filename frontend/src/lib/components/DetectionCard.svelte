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
	export let tagLabel: string | null = null;
	export let allowDelete: boolean = false;
	export let deleting: boolean = false;
	export let speciesLinks: SpeciesExternalLinks | null = null;
	export let allowSpectrogramExpand: boolean = true;
	export let spectrogramExpandedHeightClass: string = 'h-[68vh] md:h-[72vh]';
	/** When > 1, shows how many additional detections are grouped into this card. */
	export let groupedCount: number | null = null;
	export let groupedCountContext = 'in recent activity';
	let spectrogramExpanded = false;

	$: additionalDetectionCount =
		groupedCount != null && groupedCount > 1 ? groupedCount - 1 : 0;

	const dispatch = createEventDispatcher<{ delete: Detection }>();

	$: audioUrl = media.audioUrl(detection.Date, detection.Sci_Name, detection.File_Name);
	$: spectrogramUrl = media.spectrogramUrl(detection.Date, detection.Sci_Name, detection.File_Name);
	$: temporalZoomUrls = {
		'0.85': media.temporalZoomAudioUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.85),
		'0.7': media.temporalZoomAudioUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.7),
		'0.6': media.temporalZoomAudioUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.6),
		'0.5': media.temporalZoomAudioUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.5),
	};
	$: temporalZoomPrepareUrls = {
		'0.85': media.temporalZoomPrepareUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.85),
		'0.7': media.temporalZoomPrepareUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.7),
		'0.6': media.temporalZoomPrepareUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.6),
		'0.5': media.temporalZoomPrepareUrl(detection.Date, detection.Sci_Name, detection.File_Name, 0.5),
	};

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

	function handleDeleteClick(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		dispatch('delete', detection);
	}

	function toggleSpectrogram(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		spectrogramExpanded = !spectrogramExpanded;
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="card w-full max-w-full p-4 fade-in {href ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}"
	on:click={handleCardClick}
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
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0 flex-1">
					{#if tagLabel}
						<div class="mb-2">
							<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
								{tagLabel}
							</span>
						</div>
					{/if}
					{#if href}
						<a
							href={href}
							class="block truncate font-semibold text-gray-900 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-gray-100 dark:focus-visible:ring-offset-dark-card"
						>
							{detection.Com_Name}
						</a>
					{:else}
						<h3 class="font-semibold text-gray-900 dark:text-gray-100 truncate">
							{detection.Com_Name}
						</h3>
						{/if}
						<div class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 min-w-0" data-no-card-link>
							<p class="text-sm text-gray-500 dark:text-gray-400 italic truncate max-w-full">
								{detection.Sci_Name}
							</p>
							<ExternalLinks
								links={speciesLinks}
								sciName={detection.Sci_Name}
								comName={detection.Com_Name}
								compact={true}
							/>
						</div>
					</div>
				<div class="flex items-center gap-2 flex-shrink-0" data-no-card-link>
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
	<div class="mt-3 relative" data-no-card-link>
		{#if allowSpectrogramExpand}
			<button
				type="button"
				class="group block w-full rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-dark-card"
				on:click={toggleSpectrogram}
				aria-expanded={spectrogramExpanded}
				aria-label={spectrogramExpanded ? `Collapse spectrogram for ${detection.Com_Name}` : `Expand spectrogram for ${detection.Com_Name}`}
				title={spectrogramExpanded ? 'Collapse spectrogram' : 'Expand spectrogram'}
			>
				<img
					src={spectrogramUrl}
					alt="Spectrogram for {detection.Com_Name}"
					class="block w-full rounded-lg transition-[height] duration-200 ease-out {spectrogramExpanded ? `${spectrogramExpandedHeightClass} bg-gray-100 dark:bg-dark-border p-1 object-contain cursor-zoom-out` : 'h-24 object-cover bg-gray-200 dark:bg-dark-border cursor-zoom-in'}"
					loading="lazy"
				/>
				<span class="absolute right-2 top-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-gray-700 shadow-sm ring-1 ring-gray-200 backdrop-blur transition-colors group-hover:bg-white dark:bg-gray-900/85 dark:text-gray-200 dark:ring-gray-700 dark:group-hover:bg-gray-900">
					{#if spectrogramExpanded}
						<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
							<path fill-rule="evenodd" d="M14.78 12.53a.75.75 0 0 1-1.06 0L10 8.81l-3.72 3.72a.75.75 0 0 1-1.06-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06Z" clip-rule="evenodd" />
						</svg>
					{:else}
						<svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
							<path fill-rule="evenodd" d="M5.22 7.47a.75.75 0 0 1 1.06 0L10 11.19l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 8.53a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
						</svg>
					{/if}
				</span>
			</button>
		{:else}
			<img
				src={spectrogramUrl}
				alt="Spectrogram for {detection.Com_Name}"
				class="block w-full h-24 rounded-lg bg-gray-200 dark:bg-dark-border object-cover"
				loading="lazy"
			/>
		{/if}
	</div>

	<!-- Audio Player -->
	<div class="mt-3">
		<AudioPlayer
			src={audioUrl}
			filename={detection.File_Name}
			temporalZoomProminent={spectrogramExpanded}
			{temporalZoomUrls}
			{temporalZoomPrepareUrls}
		/>
	</div>

	{#if additionalDetectionCount > 0}
		<p class="mt-3 border-t border-gray-200 pt-3 text-xs text-gray-600 dark:border-dark-border dark:text-gray-400">
			+{additionalDetectionCount} more {detection.Com_Name}
			{additionalDetectionCount === 1 ? 'detection' : 'detections'}
			{groupedCountContext}
		</p>
	{/if}
</div>
