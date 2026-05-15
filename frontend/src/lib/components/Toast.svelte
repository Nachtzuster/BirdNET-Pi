<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let toast: {
		id: string;
		message: string;
		type: 'success' | 'error' | 'info' | 'warning';
	};

	const dispatch = createEventDispatcher();

	const typeStyles = {
		success: 'bg-green-500 text-white',
		error: 'bg-red-500 text-white',
		warning: 'bg-yellow-500 text-white',
		info: 'bg-blue-500 text-white',
	};

	const icons = {
		success: 'M5 13l4 4L19 7',
		error: 'M6 18L18 6M6 6l12 12',
		warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
		info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
	};
</script>

<div
	class="flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg {typeStyles[toast.type]} fade-in"
	role="alert"
>
	<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons[toast.type]} />
	</svg>
	<span class="flex-1">{toast.message}</span>
	<button
		on:click={() => dispatch('dismiss')}
		class="p-1 hover:bg-white/20 rounded"
		aria-label="Dismiss"
	>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
		</svg>
	</button>
</div>
