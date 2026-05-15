<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { currentlyPlaying } from '$lib/stores';

	export let src: string;
	export let filename: string = '';
	export let compact: boolean = false;

	let audio: HTMLAudioElement;
	let isPlaying = false;
	let currentTime = 0;
	let duration = 0;
	let lowPassHz = 20000;
	let highPassHz = 20;
	let gain = 1;
	let volume = 1;
	let showControls = false;

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

	onMount(() => {
		audio.volume = 1;
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
		{#if showControls}
			<div class="grid grid-cols-2 gap-2 text-xs">
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
