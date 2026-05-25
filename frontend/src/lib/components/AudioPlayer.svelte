<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { currentlyPlaying } from '$lib/stores';

	export let src: string;
	export let filename: string = '';
	export let compact: boolean = false;
	export let temporalZoomProminent: boolean = false;

	type PitchPreservingAudio = HTMLAudioElement & {
		preservesPitch?: boolean;
		mozPreservesPitch?: boolean;
		webkitPreservesPitch?: boolean;
	};

	const temporalZoomOptions = [
		{ label: 'Human', rate: 1, detail: '1.0x' },
		{ label: 'Field', rate: 0.85, detail: '0.85x' },
		{ label: 'Bird detail', rate: 0.7, detail: '0.7x' },
		{ label: 'Fast bird', rate: 0.6, detail: '0.6x' },
		{ label: 'Fine', rate: 0.5, detail: '0.5x' },
	];

	let audio: HTMLAudioElement;
	let isPlaying = false;
	let currentTime = 0;
	let duration = 0;
	let lowPassHz = 12000;
	let highPassHz = 500;
	let gain = 1.85;
	let volume = 1;
	let showControls = false;
	let playbackRate = 1;

	let audioContext: AudioContext | null = null;
	let sourceNode: MediaElementAudioSourceNode | null = null;
	let highPassNode: BiquadFilterNode | null = null;
	let lowPassNode: BiquadFilterNode | null = null;
	let gainNode: GainNode | null = null;
	let volumeNode: GainNode | null = null;

	$: isCurrentlyPlaying = $currentlyPlaying === src;
	$: if (lowPassNode) {
		lowPassNode.frequency.value = lowPassHz;
	}
	$: if (highPassNode) {
		highPassNode.frequency.value = highPassHz;
	}
	$: if (gainNode) {
		gainNode.gain.value = gain;
	}
	$: if (volumeNode) {
		volumeNode.gain.value = volume;
	}
	$: if (audio) {
		applyPlaybackSettings();
	}

	onMount(() => {
		audio.volume = 1;
		applyPlaybackSettings();
	});

	onDestroy(() => {
		if (sourceNode) sourceNode.disconnect();
		if (highPassNode) highPassNode.disconnect();
		if (lowPassNode) lowPassNode.disconnect();
		if (gainNode) gainNode.disconnect();
		if (volumeNode) volumeNode.disconnect();
		if (audioContext) {
			void audioContext.close();
		}
	});

	function applyPlaybackSettings() {
		if (!audio) return;
		audio.playbackRate = playbackRate;

		const pitchAudio = audio as PitchPreservingAudio;
		if ('preservesPitch' in pitchAudio) pitchAudio.preservesPitch = true;
		if ('mozPreservesPitch' in pitchAudio) pitchAudio.mozPreservesPitch = true;
		if ('webkitPreservesPitch' in pitchAudio) pitchAudio.webkitPreservesPitch = true;
	}

	function setupAudioGraph() {
		if (typeof window === 'undefined' || !audio) return;
		const AudioCtx = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
		if (!AudioCtx) return;
		if (audioContext) return;

		audioContext = new AudioCtx();
		sourceNode = audioContext.createMediaElementSource(audio);

		highPassNode = audioContext.createBiquadFilter();
		highPassNode.type = 'highpass';
		highPassNode.frequency.value = highPassHz;

		lowPassNode = audioContext.createBiquadFilter();
		lowPassNode.type = 'lowpass';
		lowPassNode.frequency.value = lowPassHz;

		gainNode = audioContext.createGain();
		gainNode.gain.value = gain;

		volumeNode = audioContext.createGain();
		volumeNode.gain.value = volume;

		sourceNode.connect(highPassNode);
		highPassNode.connect(lowPassNode);
		lowPassNode.connect(gainNode);
		gainNode.connect(volumeNode);
		volumeNode.connect(audioContext.destination);
	}

	async function ensureAudioContextRunning() {
		if (!audioContext) {
			setupAudioGraph();
		}
		if (audioContext && audioContext.state === 'suspended') {
			await audioContext.resume();
		}
	}

	async function togglePlay() {
		if (isPlaying) {
			audio.pause();
			currentlyPlaying.set(null);
		} else {
			try {
				await ensureAudioContextRunning();

				// Stop any other playing audio
				if ($currentlyPlaying && $currentlyPlaying !== src) {
					const otherAudio = document.querySelector(`audio[src="${$currentlyPlaying}"]`) as HTMLAudioElement;
					if (otherAudio) otherAudio.pause();
				}

				await audio.play();
				currentlyPlaying.set(src);
			} catch (error) {
				console.error('Unable to play audio:', error);
			}
		}
	}

	function handleTimeUpdate() {
		currentTime = audio.currentTime;
	}

	function handleLoadedMetadata() {
		duration = audio.duration;
		applyPlaybackSettings();
	}

	function handleEnded() {
		isPlaying = false;
		currentlyPlaying.set(null);
	}

	function handlePlay() {
		isPlaying = true;
	}

	function handlePause() {
		isPlaying = false;
	}

	function seek(e: MouseEvent) {
		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		const percent = (e.clientX - rect.left) / rect.width;
		audio.currentTime = percent * duration;
	}

	function formatTime(seconds: number): string {
		if (!isFinite(seconds)) return '0:00';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function selectPlaybackRate(rate: number) {
		playbackRate = rate;
		applyPlaybackSettings();
	}

	function temporalZoomButtonClass(rate: number, compactButton = false): string {
		const size = compactButton ? 'px-1.5 py-1 text-[11px]' : 'px-2 py-1.5 text-xs';
		const state =
			playbackRate === rate
				? 'border-primary-500 bg-primary-100 text-primary-800 dark:border-primary-500 dark:bg-primary-900/40 dark:text-primary-100'
				: 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 dark:border-dark-border dark:bg-dark-card dark:text-gray-300 dark:hover:bg-dark-hover';
		return `rounded-md border ${size} font-medium transition-colors ${state}`;
	}
</script>

<audio
	bind:this={audio}
	{src}
	on:timeupdate={handleTimeUpdate}
	on:loadedmetadata={handleLoadedMetadata}
	on:ended={handleEnded}
	on:play={handlePlay}
	on:pause={handlePause}
	preload="metadata"></audio>

{#if compact}
	<div class="space-y-2">
		<div class="flex items-center gap-2">
			<button
				on:click={togglePlay}
				class="p-2 rounded-full bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors"
				aria-label={isPlaying ? 'Pause' : 'Play'}
			>
				{#if isPlaying}
					<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
						<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
					</svg>
				{:else}
					<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{/if}
			</button>
			<button
				on:click={() => (showControls = !showControls)}
				class="text-xs px-2 py-1 rounded bg-gray-200 dark:bg-dark-border text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-dark-hover"
				aria-expanded={showControls}
			>
				{showControls ? 'Hide audio controls' : 'Show audio controls'}
			</button>
		</div>
		{#if temporalZoomProminent && !showControls}
			<div class="rounded-lg border border-primary-100 bg-primary-50/70 p-2 text-xs dark:border-primary-900/50 dark:bg-primary-900/15">
				<div class="mb-2 flex items-center justify-between gap-2">
					<p class="font-medium text-primary-800 dark:text-primary-100">Temporal Zoom</p>
					<p class="text-primary-700 dark:text-primary-200">{playbackRate.toFixed(2)}x</p>
				</div>
				<div class="grid grid-cols-5 gap-1">
					{#each temporalZoomOptions as option}
						<button
							type="button"
							class={temporalZoomButtonClass(option.rate, true)}
							on:click={() => selectPlaybackRate(option.rate)}
							aria-pressed={playbackRate === option.rate}
							title={`${option.label}: ${option.detail}`}
						>
							{option.detail}
						</button>
					{/each}
				</div>
				<p class="mt-2 leading-snug text-primary-700/80 dark:text-primary-100/80">
					Give your ears more room to catch fast notes and tiny gaps. Pitch stays put.
				</p>
			</div>
		{/if}
		{#if showControls}
			<div class="grid grid-cols-2 gap-2 text-xs">
				<div class="col-span-2 rounded-lg border border-gray-200 bg-white/80 p-2 dark:border-dark-border dark:bg-dark-nav/60">
					<div class="mb-2 flex items-center justify-between gap-2">
						<p class="font-medium text-gray-700 dark:text-gray-200">Temporal Zoom</p>
						<p class="text-gray-500 dark:text-gray-400">{playbackRate.toFixed(2)}x</p>
					</div>
					<div class="grid grid-cols-5 gap-1">
						{#each temporalZoomOptions as option}
							<button
								type="button"
								class={temporalZoomButtonClass(option.rate, true)}
								on:click={() => selectPlaybackRate(option.rate)}
								aria-pressed={playbackRate === option.rate}
								title={`${option.label}: ${option.detail}`}
							>
								{option.detail}
							</button>
						{/each}
					</div>
					<p class="mt-2 leading-snug text-gray-500 dark:text-gray-400">
						Temporal zoom slows playback with pitch preservation so human listeners can notice fast notes, gaps, trills, and subtle differences. Labels are inspired by visual temporal-resolution studies, not simulations of animal hearing.
					</p>
				</div>
				<label class="text-gray-600 dark:text-gray-400">
					Volume
					<input class="w-full" type="range" min="0" max="1" step="0.01" bind:value={volume} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					Gain
					<input class="w-full" type="range" min="0" max="3" step="0.01" bind:value={gain} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					High-pass
					<input class="w-full" type="range" min="20" max="5000" step="10" bind:value={highPassHz} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					Low-pass
					<input class="w-full" type="range" min="500" max="20000" step="50" bind:value={lowPassHz} />
				</label>
			</div>
		{/if}
	</div>
{:else}
	<div class="space-y-3 p-3 bg-gray-100 dark:bg-dark-card rounded-lg">
		<div class="flex items-center gap-3">
			<button
				on:click={togglePlay}
				class="p-2 rounded-full bg-primary-600 text-white hover:bg-primary-700 transition-colors flex-shrink-0"
				aria-label={isPlaying ? 'Pause' : 'Play'}
			>
				{#if isPlaying}
					<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
						<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
					</svg>
				{:else}
					<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{/if}
			</button>

			<div class="flex-1 min-w-0">
				{#if filename}
					<p class="text-sm text-gray-700 dark:text-gray-300 truncate">{filename}</p>
				{/if}
				<div class="flex items-center gap-2">
					<span class="text-xs text-gray-500 dark:text-gray-400 w-10">{formatTime(currentTime)}</span>
					<button
						class="flex-1 h-2 bg-gray-300 dark:bg-dark-border rounded-full overflow-hidden cursor-pointer"
						on:click={seek}
						aria-label="Seek"
					>
						<div
							class="h-full bg-primary-500 transition-all"
							style="width: {duration ? (currentTime / duration) * 100 : 0}%"></div>
					</button>
					<span class="text-xs text-gray-500 dark:text-gray-400 w-10 text-right">{formatTime(duration)}</span>
				</div>
			</div>
		</div>

		{#if temporalZoomProminent && !showControls}
			<div class="rounded-lg border border-primary-100 bg-primary-50/70 p-3 text-xs dark:border-primary-900/50 dark:bg-primary-900/15">
				<div class="mb-2 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
					<div>
						<p class="font-medium text-primary-800 dark:text-primary-100">Temporal Zoom</p>
						<p class="text-primary-700/80 dark:text-primary-100/80">
							Give your ears more room to catch fast notes, tiny gaps, and quick differences. Pitch stays put.
						</p>
					</div>
					<p class="font-medium text-primary-700 dark:text-primary-200">{playbackRate.toFixed(2)}x</p>
				</div>
				<div class="grid grid-cols-2 gap-1.5 sm:grid-cols-5">
					{#each temporalZoomOptions as option}
						<button
							type="button"
							class={temporalZoomButtonClass(option.rate)}
							on:click={() => selectPlaybackRate(option.rate)}
							aria-pressed={playbackRate === option.rate}
							title={`${option.label}: ${option.detail}`}
						>
							<span class="block">{option.label}</span>
							<span class="block text-[11px] opacity-80">{option.detail}</span>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<div>
			<button
				on:click={() => (showControls = !showControls)}
				class="text-xs px-2 py-1 rounded bg-gray-200 dark:bg-dark-border text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-dark-hover"
				aria-expanded={showControls}
			>
				{showControls ? 'Hide audio controls' : 'Show audio controls'}
			</button>
		</div>

		{#if showControls}
			<div class="grid sm:grid-cols-2 gap-2 text-xs">
				<div class="sm:col-span-2 rounded-lg border border-gray-200 bg-white/80 p-3 dark:border-dark-border dark:bg-dark-nav/60">
					<div class="mb-2 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
						<div>
							<p class="font-medium text-gray-800 dark:text-gray-100">Temporal Zoom</p>
							<p class="text-gray-500 dark:text-gray-400">
								Give your ears more room to catch fast notes, tiny gaps, trills, and quick differences. Pitch stays put.
							</p>
						</div>
						<p class="font-medium text-gray-600 dark:text-gray-300">{playbackRate.toFixed(2)}x</p>
					</div>
					<div class="grid grid-cols-2 gap-1.5 sm:grid-cols-5">
						{#each temporalZoomOptions as option}
							<button
								type="button"
								class={temporalZoomButtonClass(option.rate)}
								on:click={() => selectPlaybackRate(option.rate)}
								aria-pressed={playbackRate === option.rate}
								title={`${option.label}: ${option.detail}`}
							>
								<span class="block">{option.label}</span>
								<span class="block text-[11px] opacity-80">{option.detail}</span>
							</button>
						{/each}
					</div>
					<p class="mt-2 leading-snug text-gray-500 dark:text-gray-400">
						Reference labels are inspired by visual temporal-resolution studies; they are not simulations of another animal's hearing.
					</p>
				</div>
				<label class="text-gray-600 dark:text-gray-400">
					Volume ({Math.round(volume * 100)}%)
					<input class="w-full" type="range" min="0" max="1" step="0.01" bind:value={volume} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					Gain ({gain.toFixed(2)}x)
					<input class="w-full" type="range" min="0" max="3" step="0.01" bind:value={gain} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					High-pass ({Math.round(highPassHz)} Hz)
					<input class="w-full" type="range" min="20" max="5000" step="10" bind:value={highPassHz} />
				</label>
				<label class="text-gray-600 dark:text-gray-400">
					Low-pass ({Math.round(lowPassHz)} Hz)
					<input class="w-full" type="range" min="500" max="20000" step="50" bind:value={lowPassHz} />
				</label>
			</div>
		{/if}
	</div>
{/if}
