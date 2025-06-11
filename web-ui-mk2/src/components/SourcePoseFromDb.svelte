<script>
	import PoseCard from './PoseCard.svelte';
	import { getKeypointsBounds } from '$lib/pose-utils';

	/**
	 * @typedef {Object} SourcePoseFromDbProps
	 * @property {PoseRecord} poseRecord Pose to be used as the source pose
	 */

	/** @type {SourcePoseFromDbProps} */
	let { poseRecord } = $props();

	let showPose = $state(true);
	let showHands = $state(true);
</script>

<section>
	<div>
		<label>
			Show Pose:
			<input type="checkbox" bind:checked={showPose} />
		</label>
		<label>
			Show Hands:
			<input type="checkbox" bind:checked={showHands} />
		</label>
	</div>
	<PoseCard sourcePose={poseRecord} {showPose} {showHands} />
</section>

<style>
	section {
		align-items: center;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-block: 1rem;
	}
</style>
