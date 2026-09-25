import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig(() => {

    const allowedHostsArray = process.env.ALLOWED_HOSTS ? process.env.ALLOWED_HOSTS.split(',') : []

    return {
	plugins: [sveltekit()],
	ssr: {
		noExternal: process.env.NODE_ENV === 'production' ? ['@carbon/charts'] : []
	},
	server: {
		fs: {
			strict: false
		},
		allowedHosts: allowedHostsArray
	}
    }
});
