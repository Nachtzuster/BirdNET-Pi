<script lang="ts">
	import { onMount } from 'svelte';
	import { species as speciesApi, speciesLists, type SpeciesSummary } from '$lib/api';
	import { auth, toasts } from '$lib/stores';
	import { Modal } from '$lib/components';

	type ListType = 'include' | 'exclude' | 'whitelist' | 'confirmed';

	const listTypes: ListType[] = ['include', 'exclude', 'whitelist', 'confirmed'];
	const listLabels: Record<ListType, string> = {
		include: 'Include',
		exclude: 'Exclude',
		whitelist: 'Whitelist',
		confirmed: 'Confirmed',
	};

	let loading = true;
	let saving = false;
	let species: SpeciesSummary[] = [];
	let searchTerm = '';
	let showLoginModal = false;
	let passwordInput = '';

	let lists: Record<ListType, string[]> = {
		include: [],
		exclude: [],
		whitelist: [],
		confirmed: [],
	};

	let quickSpecies = '';
	let quickList: ListType = 'confirmed';
	let bulkSpecies = '';

	$: filteredSpecies = searchTerm
		? species.filter(
				(sp) =>
					sp.Com_Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
					sp.Sci_Name.toLowerCase().includes(searchTerm.toLowerCase())
			)
		: species;

	function isListed(listType: ListType, sciName: string): boolean {
		return lists[listType].includes(sciName);
	}

	async function requireAuth(): Promise<boolean> {
		if ($auth.isAuthenticated) return true;
		showLoginModal = true;
		return false;
	}

	async function loadData() {
		loading = true;
		try {
			const [speciesResult, includeRes, excludeRes, whitelistRes, confirmedRes] = await Promise.all([
				speciesApi.list({ sort: 'name' }),
				speciesLists.get('include'),
				speciesLists.get('exclude'),
				speciesLists.get('whitelist'),
				speciesLists.get('confirmed'),
			]);

			species = speciesResult.species;
			lists = {
				include: includeRes.species,
				exclude: excludeRes.species,
				whitelist: whitelistRes.species,
				confirmed: confirmedRes.species,
			};
		} catch (error) {
			console.error('Failed to load species management data:', error);
			toasts.show('Failed to load species management data', 'error');
		} finally {
			loading = false;
		}
	}

	async function setMembership(listType: ListType, sciName: string, targetEnabled: boolean) {
		if (!(await requireAuth())) return;

		saving = true;
		try {
			await speciesLists.update(
				listType,
				sciName,
				targetEnabled ? 'add' : 'remove',
				auth.getCredentials()
			);

			const next = targetEnabled
				? [...lists[listType], sciName]
				: lists[listType].filter((item) => item !== sciName);
			lists = { ...lists, [listType]: Array.from(new Set(next)).sort() };

			if (listType === 'exclude' && targetEnabled) {
				const shouldDelete = confirm(
					`"${sciName}" has been added to Exclude.\n\nDelete existing detections and recordings for this species now?`
				);
				if (shouldDelete) {
					await speciesApi.delete(sciName, auth.getCredentials());
					species = species.filter((sp) => sp.Sci_Name !== sciName);
					toasts.show('Excluded species data removed', 'success');
				}
			}
		} catch (error: any) {
			if (error?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error(`Failed to update ${listType}:`, error);
				toasts.show(`Failed to update ${listLabels[listType]} list`, 'error');
			}
		} finally {
			saving = false;
		}
	}

	async function handleQuickAdd() {
		const sciName = quickSpecies.trim();
		if (!sciName) return;
		await setMembership(quickList, sciName, true);
		quickSpecies = '';
	}

	async function handleBulkAdd() {
		if (!(await requireAuth())) return;
		const speciesToAdd = Array.from(
			new Set(
				bulkSpecies
					.split('\n')
					.map((line) => line.trim())
					.filter(Boolean)
			)
		);
		if (speciesToAdd.length === 0) return;

		saving = true;
		try {
			for (const sciName of speciesToAdd) {
				await speciesLists.update(quickList, sciName, 'add', auth.getCredentials());
			}
			toasts.show(`Added ${speciesToAdd.length} species to ${listLabels[quickList]}`, 'success');
			await loadData();
			bulkSpecies = '';
		} catch (error: any) {
			if (error?.status === 401) {
				auth.logout();
				showLoginModal = true;
			} else {
				console.error('Bulk add failed:', error);
				toasts.show('Bulk add failed', 'error');
			}
		} finally {
			saving = false;
		}
	}

	function handleLogin() {
		auth.login(passwordInput);
		passwordInput = '';
		showLoginModal = false;
	}

	onMount(loadData);
</script>

<svelte:head>
	<title>Manage Species Lists - BirdNET-Pi</title>
</svelte:head>

<div class="container mx-auto px-4 py-6">
	<div class="mb-6 flex items-center justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Manage Species Lists</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">Include, exclude, whitelist, and confirmed list controls</p>
		</div>
		<a href="/species" class="btn-secondary">Back to Species</a>
	</div>

	<div class="grid lg:grid-cols-3 gap-4 mb-6">
		<div class="card p-4 lg:col-span-2">
			<h2 class="font-semibold text-gray-900 dark:text-gray-100 mb-3">Quick Add</h2>
			<div class="grid md:grid-cols-3 gap-3">
				<input class="input md:col-span-2" bind:value={quickSpecies} placeholder="Scientific name (e.g. Turdus migratorius)" />
				<div class="flex gap-2">
					<select class="select" bind:value={quickList}>
						{#each listTypes as listType}
							<option value={listType}>{listLabels[listType]}</option>
						{/each}
					</select>
					<button class="btn-primary" on:click={handleQuickAdd} disabled={saving}>Add</button>
				</div>
			</div>
		</div>
		<div class="card p-4">
			<h2 class="font-semibold text-gray-900 dark:text-gray-100 mb-3">List Sizes</h2>
			<div class="space-y-1 text-sm">
				{#each listTypes as listType}
					<p class="text-gray-700 dark:text-gray-300">{listLabels[listType]}: {lists[listType].length}</p>
				{/each}
			</div>
		</div>
	</div>

	<div class="card p-4 mb-6">
		<h2 class="font-semibold text-gray-900 dark:text-gray-100 mb-3">Bulk Add</h2>
		<div class="grid md:grid-cols-4 gap-3">
			<textarea
				class="input md:col-span-3 min-h-[120px]"
				bind:value={bulkSpecies}
				placeholder="One scientific name per line"></textarea>
			<div class="space-y-2">
				<select class="select w-full" bind:value={quickList}>
					{#each listTypes as listType}
						<option value={listType}>{listLabels[listType]}</option>
					{/each}
				</select>
				<button class="btn-primary w-full" on:click={handleBulkAdd} disabled={saving}>Apply</button>
			</div>
		</div>
	</div>

	<div class="card p-4 mb-4">
		<label for="speciesSearch" class="label">Filter species</label>
		<input id="speciesSearch" class="input" bind:value={searchTerm} placeholder="Search by common/scientific name" />
	</div>

	<div class="card overflow-hidden">
		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
			</div>
		{:else}
			<div class="overflow-auto max-h-[70vh]">
				<table class="min-w-full text-sm">
					<thead class="bg-gray-100 dark:bg-dark-nav sticky top-0">
						<tr>
							<th class="px-4 py-3 text-left">Common Name</th>
							<th class="px-4 py-3 text-left">Scientific Name</th>
							{#each listTypes as listType}
								<th class="px-4 py-3 text-center">{listLabels[listType]}</th>
							{/each}
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-dark-border">
						{#each filteredSpecies as sp (sp.Sci_Name)}
							<tr>
								<td class="px-4 py-2 text-gray-900 dark:text-gray-100">{sp.Com_Name}</td>
								<td class="px-4 py-2 text-gray-600 dark:text-gray-300 italic">{sp.Sci_Name}</td>
								{#each listTypes as listType}
									<td class="px-4 py-2 text-center">
										<button
											class="px-2 py-1 rounded text-xs {isListed(listType, sp.Sci_Name)
												? 'bg-green-600 text-white'
												: 'bg-gray-200 dark:bg-dark-border text-gray-700 dark:text-gray-300'}"
											disabled={saving}
											on:click={() => setMembership(listType, sp.Sci_Name, !isListed(listType, sp.Sci_Name))}
										>
											{isListed(listType, sp.Sci_Name) ? 'On' : 'Off'}
										</button>
									</td>
								{/each}
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
			<label for="speciesManagePassword" class="label">Password</label>
			<input id="speciesManagePassword" type="password" bind:value={passwordInput} class="input" placeholder="Enter password" />
		</div>
		<div class="flex justify-end gap-2">
			<button type="button" on:click={() => (showLoginModal = false)} class="btn-secondary">Cancel</button>
			<button type="submit" class="btn-primary">Log in</button>
		</div>
	</form>
</Modal>
