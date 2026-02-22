<script lang="ts">
	import { onMount } from 'svelte';
	import { system as systemApi } from '$lib/api';
	import { page } from '$app/stores';
	import { isMobileMenuOpen } from '$lib/stores';
	import ThemeToggle from './ThemeToggle.svelte';

	const navItems = [
		{ href: '/', label: 'Dashboard', icon: 'home' },
		{ href: '/detections', label: 'Review', icon: 'list' },
		{ href: '/recordings', label: 'Library', icon: 'mic' },
		{ href: '/history', label: 'Insights', icon: 'calendar' },
		{ href: '/species', label: 'Species', icon: 'bird' },
	];

	let statusState: 'online' | 'degraded' | 'offline' = 'online';
	let statusText = 'Checking';
	let statusTimer: ReturnType<typeof setInterval> | undefined;

	function toggleMobileMenu() {
		isMobileMenuOpen.update((open) => !open);
	}

	function closeMobileMenu() {
		isMobileMenuOpen.set(false);
	}

	$: currentPath = $page.url.pathname;

	async function refreshStatus() {
		try {
			const status = await systemApi.publicStatus();
			statusState = status.status === 'degraded' ? 'degraded' : 'online';
			statusText = statusState === 'degraded' ? 'Degraded' : 'Online';
		} catch {
			statusState = 'offline';
			statusText = 'Offline';
		}
	}

	onMount(() => {
		void refreshStatus();
		statusTimer = setInterval(() => {
			void refreshStatus();
		}, 30000);

		return () => {
			if (statusTimer) clearInterval(statusTimer);
		};
	});
</script>

<!-- Desktop Navigation -->
<nav class="hidden md:flex fixed top-0 left-0 right-0 h-16 shadow-lg z-30 overflow-hidden">
	<div class="absolute inset-0 bg-gradient-to-r from-primary-700 via-primary-700 to-primary-900 dark:from-dark-nav dark:via-dark-nav dark:to-black pointer-events-none"></div>
	<img
		src="/bnp.png"
		alt=""
		aria-hidden="true"
		class="hidden lg:block absolute top-0 right-0 h-full w-80 object-cover object-left opacity-15 pointer-events-none select-none"
	/>
	<div class="relative container mx-auto px-4 flex items-center justify-between">
		<!-- Logo -->
		<a href="/" class="flex items-center gap-3 text-white">
			<img src="/bird.png" alt="BirdNET-Pi logo" class="w-8 h-8 rounded-md object-cover ring-1 ring-white/30" />
			<span class="text-xl font-bold">BirdNET-Pi</span>
		</a>

		<!-- Navigation Links -->
		<div class="flex items-center gap-1">
			{#each navItems as item}
				<a
					href={item.href}
					class="px-4 py-2 rounded-lg transition-colors {currentPath === item.href
						? 'bg-white/20 text-white'
						: 'text-white/90 hover:text-white hover:bg-white/10'}"
				>
					{item.label}
				</a>
			{/each}

			<a
				href="/status"
				class="px-4 py-2 rounded-lg transition-colors flex items-center gap-2 {currentPath === '/status'
					? 'bg-white/20 text-white'
					: 'text-white/90 hover:text-white hover:bg-white/10'}"
				aria-label="Server status"
				title={`Server status: ${statusText}`}
			>
				<span
					class="w-2.5 h-2.5 rounded-full"
					class:bg-green-400={statusState === 'online'}
					class:bg-amber-400={statusState === 'degraded'}
					class:bg-red-400={statusState === 'offline'}></span>
				<span>Status</span>
			</a>

			<!-- Theme Toggle -->
			<ThemeToggle />
		</div>
	</div>
</nav>

<!-- Mobile Navigation -->
<nav class="md:hidden fixed top-0 left-0 right-0 h-14 bg-primary-700 dark:bg-dark-nav shadow-lg z-30 overflow-hidden">
	<img
		src="/bnp.png"
		alt=""
		aria-hidden="true"
		class="absolute top-0 right-0 h-full w-36 object-cover object-left opacity-20 pointer-events-none select-none"
	/>
	<div class="relative h-full px-4 flex items-center justify-between">
		<a href="/" class="flex items-center gap-2 text-white">
			<img src="/bird.png" alt="BirdNET-Pi logo" class="w-7 h-7 rounded-md object-cover ring-1 ring-white/30" />
			<span class="text-lg font-bold">BirdNET-Pi</span>
		</a>

		<div class="flex items-center gap-2">
			<ThemeToggle />
			<button
				on:click={toggleMobileMenu}
				class="p-2 text-white hover:bg-white/10 rounded-lg"
				aria-label="Toggle menu"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					{#if $isMobileMenuOpen}
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					{:else}
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
					{/if}
				</svg>
			</button>
		</div>
	</div>
</nav>

<!-- Mobile Menu Overlay -->
{#if $isMobileMenuOpen}
	<div
		class="md:hidden fixed inset-0 bg-black/50 z-40"
		on:click={closeMobileMenu}
		on:keydown={(e) => e.key === 'Escape' && closeMobileMenu()}
		role="button"
		tabindex="0"
	></div>

	<div class="md:hidden fixed top-14 left-0 right-0 bottom-0 bg-white dark:bg-dark-body z-40 overflow-y-auto">
		<div class="p-4 space-y-2">
			{#each navItems as item}
				<a
					href={item.href}
					on:click={closeMobileMenu}
					class="block px-4 py-3 rounded-lg {currentPath === item.href
						? 'bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200'
						: 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-card'}"
				>
					{item.label}
				</a>
			{/each}

			<div class="border-t border-gray-200 dark:border-dark-border my-4"></div>

			<a
				href="/status"
				on:click={closeMobileMenu}
				class="flex items-center gap-2 px-4 py-3 rounded-lg {currentPath === '/status'
					? 'bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200'
					: 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-card'}"
			>
				<span
					class="w-2.5 h-2.5 rounded-full"
					class:bg-green-500={statusState === 'online'}
					class:bg-amber-500={statusState === 'degraded'}
					class:bg-red-500={statusState === 'offline'}></span>
				<span>Status ({statusText})</span>
			</a>
		</div>
	</div>
{/if}

<!-- Mobile Bottom Navigation -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-white dark:bg-dark-nav border-t border-gray-200 dark:border-dark-border z-30">
	<div class="h-full grid grid-cols-5">
		{#each navItems as item}
			<a
				href={item.href}
				class="flex flex-col items-center justify-center {currentPath === item.href
					? 'text-primary-600 dark:text-primary-400'
					: 'text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400'}"
			>
				{#if item.icon === 'home'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
					</svg>
				{:else if item.icon === 'list'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
					</svg>
				{:else if item.icon === 'mic'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
					</svg>
				{:else if item.icon === 'calendar'}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
					</svg>
				{:else if item.icon === 'bird'}
					<svg class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 2C7.58 2 4 5.58 4 10c0 3.31 2.69 6 6 6h1v4l3-3 3 3v-4h1c3.31 0 6-2.69 6-6 0-4.42-3.58-8-8-8zm-2 9a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm4 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
					</svg>
				{/if}
				<span class="text-xs mt-1">{item.label}</span>
			</a>
		{/each}
	</div>
</nav>
