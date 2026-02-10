import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	ssr: {
		noExternal: process.env.NODE_ENV === 'production' ? ['@carbon/charts'] : []
	},
	server: {
		fs: {
			strict: false
		},
		allowedHosts: [
			"mime.pmbwell.org",
			"mime.stanford.edu"
		]
	}
});
