<script>
	import { page } from '$app/state';
	import { Loading } from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';
	import localStorageState from '$lib/localstorage.svelte';
	import PoseCard from '$components/PoseCard.svelte';

	/**
	 * @typedef {Object} HandSearchResultsProps
	 * @property {HandForSearching} sourceHand Source hand to be searched
	 */

	/** @type {HandSearchResultsProps} */
	let { sourceHand } = $props();

	/** @type {{value: 'joint_angles3d'|'embedding'|'global3d'}} */
	let searchType = localStorageState('hand-search-type', 'global3d');

	let limit = localStorageState('search-limit', 21);
	let excludeWithinFrames = localStorageState('exclude-within-frames', 3000);

	/** @type {{value: string[]}} */
	let selectedVideoIds = localStorageState('search-video-ids', []);

	let showHands = localStorageState('search-show-hands', false);

	/** @param {PoseRecord[]} poses */
	const excludeSourceHand = (poses) => {
		return poses.filter(
			(/** @type {PoseRecord} */ pose) =>
				!(
					pose.video_id === /** @type {HandForSearching} */ (sourceHand).video_id &&
					pose.frame === /** @type {HandForSearching} */ (sourceHand).frame &&
					pose.pose_idx === /** @type {HandForSearching} */ (sourceHand).pose_idx
				)
		);
	};

	async function getPoseData() {
		const queryParams = new URLSearchParams();
		let embedding;
		if (searchType.value === 'embedding') {
			embedding = sourceHand.class_weights;
		} else if (searchType.value === 'joint_angles3d') {
			embedding = sourceHand.joint_angles3d;
		} else if (searchType.value === 'global3d') {
			embedding = sourceHand.global3d;
		}

		queryParams.append('embedding', JSON.stringify(embedding));
		queryParams.append('search_type', searchType.value);
		if (selectedVideoIds.value.length)
			selectedVideoIds.value.forEach((v) => queryParams.append('videos', v));
		queryParams.append('exclude_within_frames', Math.max(excludeWithinFrames.value, 1).toString());
		// if sourcePose has a frame property then it's from the db -- add one to the limit so we
		//  can exclude the source pose from the results and still end up with the requested number
		queryParams.append('limit', (limit.value + +sourceHand.hasOwnProperty('frame')).toString());

		const query = `${page.data.apiBase}/hand-search/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	}
</script>

<div class="controls">
	<label>
		Show Hands:
		<input type="checkbox" bind:checked={showHands.value} />
	</label>
	<label>
		Performances:
		{#await getVideoData() then videos}
			<select multiple bind:value={selectedVideoIds.value}>
				{#each videos as video}
					<option value={video.id}>{video.video_name}</option>
				{/each}
			</select>
		{/await}
	</label>
	<label>
		Search Type:
		<select bind:value={searchType.value}>
			<option value="joint_angles3d">Joint Angles</option>
			<option value="embedding">Embedding</option>
			<option value="global3d">Global 3D</option>
		</select>
	</label>
	<label>
		Exclude within Frames:
		<input type="number" bind:value={excludeWithinFrames.value} />
	</label>
	<label>
		# Results:
		<input type="number" bind:value={limit.value} min="1" />
	</label>
</div>

{#if sourceHand}
	<div class="results">
		{#await getPoseData()}
			<div class="loading">
				Searching...
				<Loading withOverlay={false} />
			</div>
		{:then data}
			{#each excludeSourceHand(data) as pose}
				<PoseCard sourcePose={pose} showHands={showHands.value} />
			{/each}
		{:catch error}
			<p style="color: red">{error.message}</p>
		{/await}
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
