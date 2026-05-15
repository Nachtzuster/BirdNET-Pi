import { system } from '$lib/api';
import { auth } from '$lib/stores';

export async function verifyPasswordLogin(password: string): Promise<{ ok: boolean; message?: string }> {
	const trimmedPassword = password.trim();
	if (!trimmedPassword) {
		return { ok: false, message: 'Enter password' };
	}

	auth.login(trimmedPassword);

	try {
		await system.info(auth.getCredentials());
		return { ok: true };
	} catch (error: any) {
		auth.logout();
		return {
			ok: false,
			message: error?.status === 401 ? 'Invalid password' : 'Failed to authenticate',
		};
	}
}
