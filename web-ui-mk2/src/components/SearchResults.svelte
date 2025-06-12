<script>
	import { page } from '$app/state';
	import { Loading } from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';
	import localStorageState from '$lib/localstorage.svelte';
	import PoseCard from '$components/PoseCard.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose|PoseRecord} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	/** @type {{value: 'cosine'|'euclidean'|'view_invariant'|'3d'}}} */
	let searchType = localStorageState('pose-search-type', 'view_invariant');

	let limit = localStorageState('search-limit', 21);
	let excludeWithinFrames = localStorageState('exclude-within-frames', 3000);

	/** @type {{value: string[]}} */
	let selectedVideoIds = localStorageState('search-video-ids', []);

	let showPose = localStorageState('search-show-pose', false);
	let showHands = localStorageState('search-show-hands', false);

	/** @param {PoseRecord[]} poses */
	const excludeSourcePose = (poses) => {
		return poses
			.filter(
				(/** @type {PoseRecord} */ pose) =>
					!(
						pose.video_id === /** @type {PoseRecord} */ (sourcePose).video_id &&
						pose.frame === /** @type {PoseRecord} */ (sourcePose).frame &&
						pose.pose_idx === /** @type {PoseRecord} */ (sourcePose).pose_idx
					)
			)
			.slice(0, limit.value);
	};

	async function getPoseData() {
		const queryParams = new URLSearchParams();
		queryParams.append('pose', JSON.stringify(sourcePose.norm));
		queryParams.append('search_type', searchType.value);
		if (selectedVideoIds.value.length)
			selectedVideoIds.value.forEach((v) => queryParams.append('videos', v));
		queryParams.append('exclude_within_frames', Math.max(excludeWithinFrames.value, 1).toString());
		// if sourcePose has a frame property then it's from the db -- add one to the limit so we
		//  can exclude the source pose from the results and still end up with the requested number
		queryParams.append('limit', (limit.value + +sourcePose.hasOwnProperty('frame')).toString());

		const query = `${page.data.apiBase}/pose-search/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	}
</script>

<div class="controls">
	<div>
		<label>
			Show Pose:
			<input type="checkbox" bind:checked={showPose.value} />
		</label>
		<label>
			Show Hands:
			<input type="checkbox" bind:checked={showHands.value} />
		</label>
	</div>
	<label>
		Videos:
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
			<option value="cosine">Cosine</option>
			<option value="euclidean">Euclidean</option>
			<option value="view_invariant">View Invariant</option>
			<!--
			<option value="3d">3D</option>
			-->
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

{#if sourcePose}
	<div class="results">
		{#await getPoseData()}
			<div class="loading">
				Searching...
				<Loading withOverlay={false} />
			</div>
		{:then data}
			{#each excludeSourcePose(data) as pose}
				<PoseCard sourcePose={pose} showPose={showPose.value} showHands={showHands.value} />
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
