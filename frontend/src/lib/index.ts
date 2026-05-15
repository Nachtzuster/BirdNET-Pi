// Re-export from submodules for convenience
export * from './api';
export * from './stores';

/**
 * Format a bird name for display by replacing underscores with spaces.
 * Bird names may come from directory names which use underscores instead of spaces.
 */
export function formatBirdName(name: string): string {
	return name.replace(/_/g, ' ');
}
