<script>
	import { page } from '$app/stores';
	import { Dropdown } from 'carbon-components-svelte';

	let currentVideoId = $state();

	const getVideoRecords = async () => {
		return await fetch(`${$page.data.apiBase}/videos/`)
			.then((data) => data.json())
			.then((data) =>
				data.videos.map((/** @type {VideoRecord} */ video) => ({
					text: video.video_name,
					...video
				}))
			);
	};
</script>

<h1>Analytics</h1>

{#await getVideoRecords() then videos}
	<Dropdown titleText="Video" items={videos} bind:selectedId={currentVideoId} />

	{#if currentVideoId}
		{@const currentVideo = videos.find((/** @type {VideoRecord} */ v) => v.id === currentVideoId)}
		<pre>{JSON.stringify(currentVideo, null, 2)}</pre>
	{/if}
{/await}

<style>
	h1 {
		margin: 2rem 0;
	}
	pre {
		margin: 2rem;
		padding: 1rem;
		font-family: monospace;
		font-size: 1rem;
		line-height: 1.5;
		background: #eee;
	}
</style>
