<script>
	import { page } from '$app/stores';
	import { getVideoData } from '$lib/data-fetching';
	import PoseCard from '$components/PoseCard.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose|PoseRecord} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	/** @type {'cosine'|'euclidean'|'view_invariant'|'3d'} */
	let searchType = $state('cosine');

	let limit = $state(14);
	let excludeWithinFrames = $state(30);

	/** @type {string[]}*/
	let selectedVideoIds = $state([]);

	let showPose = $state(false);

	/** @param {PoseRecord[]} poses */
	const excludeSourcePose = (poses) => {
		return poses.filter(
			(/** @type {PoseRecord} */ pose) =>
				!(
					pose.video_id === /** @type {PoseRecord} */ (sourcePose).video_id &&
					pose.frame === /** @type {PoseRecord} */ (sourcePose).frame &&
					pose.pose_idx === /** @type {PoseRecord} */ (sourcePose).pose_idx
				)
		);
	};

	async function getPoseData() {
		const queryParams = new URLSearchParams();
		queryParams.append('pose', JSON.stringify(sourcePose.norm));
		queryParams.append('search_type', searchType);
		if (selectedVideoIds.length) selectedVideoIds.forEach((v) => queryParams.append('videos', v));
		queryParams.append('exclude_within_frames', Math.max(excludeWithinFrames, 1).toString());
		// if sourcePose has a frame property then it's from the db -- add one to the limit so we
		//  can exclude the source pose from the results and still end up with the requested number
		queryParams.append('limit', (limit + +sourcePose.hasOwnProperty('frame')).toString());

		const query = `${$page.data.apiBase}/pose-search/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	}
</script>

<div>
	<label>
		Show Pose:
		<input type="checkbox" bind:checked={showPose} />
	</label>
	<label>
		Videos:
		{#await getVideoData() then videos}
			<select multiple bind:value={selectedVideoIds}>
				{#each videos as video}
					<option value={video.id}>{video.video_name}</option>
				{/each}
			</select>
		{/await}
	</label>
	<label>
		Search Type:
		<select bind:value={searchType}>
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
		<input type="number" bind:value={excludeWithinFrames} />
	</label>
	<label>
		# Results:
		<input type="number" bind:value={limit} min="1" />
	</label>
</div>

{#if sourcePose}
	<div class="results">
		{#await getPoseData()}
			Searching...
		{:then data}
			{#each excludeSourcePose(data) as pose}
				<PoseCard sourcePose={pose} {showPose} />
			{/each}
		{:catch error}
			<p style="color: red">{error.message}</p>
		{/await}
	</div>
{/if}

<style>
	div {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		justify-content: center;
		padding: 1rem;
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
