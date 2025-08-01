<script>
	import { fade } from 'svelte/transition';
	import { Loading, MultiSelect } from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';
	import localStorageState from '$lib/localstorage.svelte';
	import PosePrevalence from './PosePrevalence.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose|PoseRecord} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	/** @type {{value: 'cosine'|'euclidean'|'view_invariant'|'3d'}}} */
	let searchType = localStorageState('pose-search-type', 'view_invariant');

	let selectedVideoIds = $state([]);

	let videoNameById = {};

	const formatVideoData = async () =>
		await getVideoData().then((data) =>
			data.map((/** @type {VideoRecord} */ video) => {
				videoNameById[video.id] = video.video_name;
				return {
					id: video.id,
					text: video.video_name
				};
			})
		);

	const formatSourcePose = (sourcePose) =>
		searchType.value === '3d' && !sourcePose.fromWebcam
			? sourcePose.global3d_coco13.toString()
			: sourcePose.norm.toString();
</script>

<div class="controls">
	<label>
		{#await formatVideoData()}
			<div class="loading"><Loading small withOverlay={false} />Loading performances...</div>
		{:then videos}
			<div class="selector" transition:fade>
				<MultiSelect
					titleText="Performances"
					label="Select performances..."
					hideLabel
					placeholder="Filter performances..."
					filterable
					items={videos}
					bind:selectedIds={selectedVideoIds}
				/>
			</div>
		{/await}
	</label>
	<label>
		Search Type:
		<select bind:value={searchType.value}>
			<option value="cosine">Cosine</option>
			<option value="euclidean">Euclidean</option>
			<option value="view_invariant">View Invariant</option>
			<option value="3d">Global 3D</option>
		</select>
	</label>
</div>

{#if sourcePose}
	<div class="results">
		{#each selectedVideoIds as videoId}
			<PosePrevalence
				{videoId}
				videoName={videoNameById[videoId]}
				sourcePose={formatSourcePose(sourcePose)}
				searchType={sourcePose.fromWebcam && searchType.value === '3d'
					? 'view_invariant'
					: searchType.value}
			/>
		{/each}
	</div>
{/if}

<style>
	.controls,
	.results {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		justify-content: center;
		padding: 1rem;
	}

	.loading {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		text-align: center;
	}

	.selector {
		width: 30rem;
	}

	label {
		align-items: flex-start;
		display: flex;
		gap: 0.5rem;
		line-height: 24px;
	}

	input[type='number'] {
		width: 5rem;
	}
</style>
