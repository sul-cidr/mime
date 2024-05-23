import { env } from '$env/dynamic/public';
const apiBase = env.PUBLIC_API_BASE;

/** @type {import('./$types').LayoutLoad} */
export function load() {
	return {
		apiBase
	};
}
