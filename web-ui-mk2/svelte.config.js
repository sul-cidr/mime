import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
		// See https://kit.svelte.dev/docs/adapters for more information about adapters.
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			precompress: false,
			strict: true,
			fallback: '404.html'
		}),
		paths: {
			base: '/mk2'
		},
		alias: {
			'@': './src',
			$components: './src/components'
		}
	}
};

export default config;
