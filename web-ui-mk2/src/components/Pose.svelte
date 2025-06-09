<script>
	import { getContext } from 'svelte';
	import { drawPoseOnCanvas } from '$lib/pose-utils';

	/**
	 * @typedef {Object} PoseProps
	 * @property {Coco13SkeletonNoConfidence} poseData Pose data to be drawn
	 * @property {number} [scaleFactor] Scale factor to be applied to the pose
	 * @property {BoundingBox} [bbox] Bounding box of the figure -- if supplied, the pose will be drawn with respect to the bbox
	 * @returns {void}
	 */

	/** @type {PoseProps} */
	let { poseData, scaleFactor, bbox } = $props();
	const { ctx } = getContext('canvas');

	$effect(() => {
		// Ugly hack to ensure the canvas has been scaled and cleared *before* the pose is drawn
		//  (only an issue when the pose is derived from a fixture; the db/network latency means its
		//   not a problem when poses are fetched from the server)
		setTimeout(() => {
			if ($ctx) drawPoseOnCanvas($ctx, poseData, scaleFactor, bbox);
		}, 0);
	});
</script>
