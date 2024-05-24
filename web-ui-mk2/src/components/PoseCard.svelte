<script>
	import { LayerCake, Canvas } from 'layercake';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose} sourcePose Pose to be presented
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();
</script>

<div>
	<LayerCake>
		<Canvas zIndex={1}>
			<Pose poseData={sourcePose.norm} normalizedPose={true} />
		</Canvas>
	</LayerCake>
</div>

<style>
	div {
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;
	}
</style>
