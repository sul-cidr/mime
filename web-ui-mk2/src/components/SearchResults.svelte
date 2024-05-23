<script>
	import { page } from '$app/stores';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	/** @type {'cosine'|'euclidean'|'view_invariant'|'3d'|undefined} */
	let searchType = $state();

	async function getPoseData() {
		const queryParams = new URLSearchParams();
		queryParams.append('pose', JSON.stringify(sourcePose));
		queryParams.append('search_type', 'cosine');
		// queryParams.append('videos', );
		// queryParams.append('limit', "50");

		const query = `${$page.data.apiBase}/pose-search/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	}
</script>

<div>
	{#await getPoseData()}
		Searching...
	{:then data}
		{#each data as pose}
			<pre>{JSON.stringify(pose)}</pre>
		{/each}
	{:catch error}
		<p style="color: red">{error.message}</p>
	{/await}
</div>
