<script lang="ts">
	import { get } from 'svelte/store';
	import { onMount } from 'svelte';
	import { verifyPasswordLogin } from '$lib/auth';
	import { fileManager, type FileEntry, type FileListingResponse, type FileRoot } from '$lib/api';
	import { Modal } from '$lib/components';
	import { auth, toasts } from '$lib/stores';

	let roots: FileRoot[] = [];
	let selectedRoot = '';
	let listing: FileListingResponse | null = null;
	let loading = false;
	let deletingPaths = new Set<string>();
	let showLoginModal = false;
	let passwordInput = '';
	let initialRoot = '';
	let initialPath = '';

	function isUnauthorized(error: unknown): error is { status: number } {
		return typeof error === 'object' && error !== null && 'status' in error && (error as { status: number }).status === 401;
	}

	function formatSize(bytes: number | null): string {
		if (bytes === null) return 'Unknown';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
		return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
	}

	function formatTimestamp(value: string): string {
		return new Date(value).toLocaleString();
	}

	function syncUrl(path = listing?.current_path ?? '') {
		const url = new URL(window.location.href);
		if (selectedRoot) {
			url.searchParams.set('root', selectedRoot);
		} else {
			url.searchParams.delete('root');
		}

		if (path) {
			url.searchParams.set('path', path);
		} else {
			url.searchParams.delete('path');
		}

		window.history.replaceState({}, '', `${url.pathname}${url.search}`);
	}

	function formatEntryDetails(entry: FileEntry): string {
		if (entry.entry_type === 'file') return 'File';
		if (!entry.file_count) return 'Empty folder';
		return `${entry.file_count} file${entry.file_count === 1 ? '' : 's'}`;
	}

	function cancelLogin() {
		passwordInput = '';
		showLoginModal = false;
		if (!get(auth).isAuthenticated) {
			window.location.href = '/recordings';
		}
	}

	async function loadRoots() {
		loading = true;
		try {
			const result = await fileManager.roots(auth.getCredentials());
			roots = result.roots.filter((root) => root.available);

			if (roots.length === 0) {
				selectedRoot = '';
				listing = null;
				return;
			}

			const preferredRoot = initialRoot && roots.some((root) => root.id === initialRoot)
				? initialRoot
				: selectedRoot && roots.some((root) => root.id === selectedRoot)
					? selectedRoot
					: roots[0].id;

			selectedRoot = preferredRoot;
			await loadListing(initialPath, false);
			initialRoot = '';
			initialPath = '';
		} catch (error) {
			if (isUnauthorized(error)) {
				auth.logout();
				showLoginModal = true;
				return;
			}

			console.error('Failed to load file roots:', error);
			toasts.show('Failed to load file manager roots', 'error');
		} finally {
			loading = false;
		}
	}

	async function loadListing(path = '', updateUrl = true) {
		if (!selectedRoot) return;

		loading = true;
		try {
			listing = await fileManager.list(selectedRoot, path, auth.getCredentials());
			if (updateUrl) syncUrl(listing.current_path);
		} catch (error) {
			if (isUnauthorized(error)) {
				auth.logout();
				showLoginModal = true;
				return;
			}

			console.error('Failed to load file listing:', error);
			toasts.show('Failed to load file listing', 'error');
		} finally {
			loading = false;
		}
	}

	async function handleRootChange(rootId: string) {
		if (rootId === selectedRoot) return;
		selectedRoot = rootId;
		await loadListing('');
	}

	async function openEntry(entry: FileEntry) {
		if (entry.entry_type === 'directory') {
			await loadListing(entry.path);
			return;
		}

		await downloadEntry(entry);
	}

	async function downloadEntry(entry: FileEntry) {
		try {
			const { blob, filename } = await fileManager.download(selectedRoot, entry.path, auth.getCredentials());
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = url;
			anchor.download = filename || entry.name;
			document.body.appendChild(anchor);
			anchor.click();
			anchor.remove();
			URL.revokeObjectURL(url);
		} catch (error) {
			if (isUnauthorized(error)) {
				auth.logout();
				showLoginModal = true;
				return;
			}

			console.error('Failed to download file:', error);
			toasts.show('Failed to download file', 'error');
		}
	}

	async function deleteEntry(entry: FileEntry) {
		const noun = entry.entry_type === 'directory' ? 'folder' : 'file';
		if (!confirm(`Delete ${noun} ${entry.name}? Empty folders only can be removed.`)) return;

		deletingPaths = new Set(deletingPaths).add(entry.path);
		try {
			await fileManager.delete(selectedRoot, entry.path, auth.getCredentials());
			await loadListing(listing?.current_path ?? '');
			toasts.show(`${entry.entry_type === 'directory' ? 'Folder' : 'File'} deleted`, 'success');
		} catch (error) {
			if (isUnauthorized(error)) {
				auth.logout();
				showLoginModal = true;
				return;
			}

			console.error('Failed to delete entry:', error);
			toasts.show('Failed to delete entry', 'error');
		} finally {
			const next = new Set(deletingPaths);
			next.delete(entry.path);
			deletingPaths = next;
		}
	}

	async function handleLogin() {
		const result = await verifyPasswordLogin(passwordInput);
		if (!result.ok) {
			toasts.show(result.message || 'Failed to authenticate', 'error');
			return;
		}

		passwordInput = '';
		showLoginModal = false;
		toasts.show('Authenticated', 'success');
		await loadRoots();
	}

	onMount(() => {
		const query = new URLSearchParams(window.location.search);
		initialRoot = query.get('root') || '';
		initialPath = query.get('path') || '';

		if (get(auth).isAuthenticated) {
			void loadRoots();
		} else {
			showLoginModal = true;
		}
	});
</script>

<svelte:head>
	<title>File Manager - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">File Manager</h1>
			<p class="mt-1 text-gray-600 dark:text-gray-400">
				Admin-only access to BirdNET recording and generated media directories.
			</p>
		</div>
		<a href="/recordings" class="btn-secondary">Back to Library</a>
	</div>

	<div class="card mb-6 p-4">
		<div class="mb-3 flex items-center justify-between gap-3">
			<div>
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Logical Roots</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Only BirdNET-owned directories are exposed here. This is not a general server browser.
				</p>
			</div>
		</div>

		{#if roots.length === 0 && !loading}
			<p class="text-sm text-gray-600 dark:text-gray-400">No configured file-manager roots are currently available.</p>
		{:else}
			<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
				{#each roots as root}
					<button
						type="button"
						class={`rounded-xl border p-4 text-left transition-colors ${
							selectedRoot === root.id
								? 'border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-950/30'
								: 'border-gray-200 bg-white hover:border-primary-300 dark:border-dark-border dark:bg-dark-card dark:hover:border-primary-600'
						}`}
						on:click={() => handleRootChange(root.id)}
					>
						<div class="font-semibold text-gray-900 dark:text-gray-100">{root.label}</div>
						<div class="mt-1 text-sm text-gray-600 dark:text-gray-400">{root.description}</div>
						<div class="mt-3 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
							<span>{root.file_count ?? 0} files</span>
							<span>{formatSize(root.total_size ?? 0)}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<div class="card p-4">
		<div class="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
			<div>
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					{listing?.root_label || 'Files'}
				</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Current path: <span class="font-mono">{listing?.current_path || '/'}</span>
				</p>
			</div>
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="btn-secondary btn-sm"
					on:click={() => loadListing(listing?.parent_path || '')}
					disabled={!listing?.parent_path && listing?.parent_path !== ''}
				>
					Up
				</button>
				<button type="button" class="btn-secondary btn-sm" on:click={() => loadListing(listing?.current_path || '')}>
					Refresh
				</button>
			</div>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent"></div>
			</div>
		{:else if !listing}
			<div class="rounded-lg bg-gray-50 p-6 text-sm text-gray-600 dark:bg-dark-card dark:text-gray-400">
				Log in to browse file-manager roots.
			</div>
		{:else if listing.entries.length === 0}
			<div class="rounded-lg bg-gray-50 p-6 text-sm text-gray-600 dark:bg-dark-card dark:text-gray-400">
				This directory is empty.
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-gray-200 dark:divide-dark-border">
					<thead>
						<tr class="text-left text-sm text-gray-500 dark:text-gray-400">
							<th class="py-3 pr-4 font-medium">Name</th>
							<th class="py-3 pr-4 font-medium">Contents</th>
							<th class="py-3 pr-4 font-medium">Size</th>
							<th class="py-3 pr-4 font-medium">Modified</th>
							<th class="py-3 font-medium text-right">Actions</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-100 dark:divide-dark-border">
						{#each listing.entries as entry}
							<tr class="text-sm text-gray-700 dark:text-gray-200">
								<td class="py-3 pr-4">
									<button
										type="button"
										class="flex items-center gap-2 text-left hover:text-primary-600 dark:hover:text-primary-400"
										on:click={() => openEntry(entry)}
									>
										<span class="text-lg">{entry.entry_type === 'directory' ? '▸' : '•'}</span>
										<span class="font-medium">{entry.name}</span>
									</button>
								</td>
								<td class="py-3 pr-4">{formatEntryDetails(entry)}</td>
								<td class="py-3 pr-4">{formatSize(entry.total_size ?? entry.size ?? 0)}</td>
								<td class="py-3 pr-4">{formatTimestamp(entry.modified_at)}</td>
								<td class="py-3 text-right">
									<div class="flex justify-end gap-2">
										{#if entry.entry_type === 'file'}
											<button type="button" class="btn-secondary btn-sm" on:click={() => downloadEntry(entry)}>
												Download
											</button>
										{/if}
										<button
											type="button"
											class="inline-flex h-8 items-center rounded-lg bg-red-600 px-3 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
											on:click={() => deleteEntry(entry)}
											disabled={deletingPaths.has(entry.path)}
										>
											{deletingPaths.has(entry.path) ? 'Deleting…' : 'Delete'}
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>

<Modal bind:open={showLoginModal} title="Authentication Required">
	<form on:submit|preventDefault={handleLogin} class="space-y-4">
		<div>
			<label for="filesPassword" class="label">Password</label>
			<input id="filesPassword" type="password" bind:value={passwordInput} class="input" placeholder="Enter password" />
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={cancelLogin} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
