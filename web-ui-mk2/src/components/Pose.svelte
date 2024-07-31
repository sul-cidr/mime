<script>
	import { getContext } from 'svelte';
	import { scaleCanvas } from 'layercake';
	import { drawPoseOnCanvas } from '$lib/pose-utils';

	/**
	 * @typedef {Object} PoseProps
	 * @property {Coco13SkeletonNoConfidence} poseData Pose data to be drawn
	 * @property {number} [scaleFactor=1] Scale factor to be applied to the pose
	 * @property {boolean} [normalizedPose=false] Whether the pose is normalized
	 * @property {Number[]} [bbox] Bounding box of the figure
	 * @returns {void}
	 */

	/** @type {PoseProps} */
	let { poseData, scaleFactor = 1, normalizedPose = false, fitToCanvas = true, bbox } = $props();

	const { width, height } = getContext('LayerCake');
	const { ctx } = getContext('canvas');

	$effect(() => {
		if ($ctx) {
			// "Scale your canvas size to retina screens."
			// (see https://layercake.graphics/guide#scalecanvas)
			scaleCanvas($ctx, $width, $height);
			$ctx.clearRect(0, 0, $width, $height);
			drawPoseOnCanvas($ctx, poseData, fitToCanvas, scaleFactor, bbox);
		}
	});
</script>
