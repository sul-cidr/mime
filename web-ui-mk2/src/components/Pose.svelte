<script>
	import { getContext } from 'svelte';
	import { scaleCanvas } from 'layercake';
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

	const { width, height } = getContext('LayerCake');
	const { ctx } = getContext('canvas');

	$effect(() => {
		if ($ctx) {
			// "Scale your canvas size to retina screens."
			// (see https://layercake.graphics/guide#scalecanvas)
			scaleCanvas($ctx, $width, $height);
			$ctx.clearRect(0, 0, $width, $height);
			drawPoseOnCanvas($ctx, poseData, scaleFactor, bbox);
		}
	});
</script>
