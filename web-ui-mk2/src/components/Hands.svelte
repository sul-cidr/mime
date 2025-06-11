<script>
	import { getContext } from 'svelte';
	import { scaleCanvas } from 'layercake';
	import { drawHandOnCanvas } from '$lib/pose-utils';

	/**
	 * @typedef {Object} PoseProps
	 * @property {{ rh_keypoints2d: number[]|undefined; lh_keypoints2d: number[]|undefined }} handData Pose data to be drawn
	 * @property {number} [scaleFactor] Scale factor to be applied to the pose
	 * @property {BoundingBox} [bbox] Bounding box of the figure -- if supplied, the pose will be drawn with respect to the bbox
	 * @returns {void}
	 */

	/** @type {PoseProps} */
	let { handData, scaleFactor, bbox } = $props();
	const { width, height } = getContext('LayerCake');
	const { ctx } = getContext('canvas');

	$effect(() => {
		if ($ctx && $width && $height) {
			// "Scale your canvas size to retina screens."
			// (see https://layercake.graphics/guide#scalecanvas)
			scaleCanvas($ctx, $width, $height);
			$ctx.clearRect(0, 0, $width, $height);
			if ('rh_keypoints2d' in handData && handData.rh_keypoints2d) {
				drawHandOnCanvas($ctx, handData.rh_keypoints2d, 'green', bbox, scaleFactor);
			}
			if ('lh_keypoints2d' in handData && handData.lh_keypoints2d) {
				drawHandOnCanvas($ctx, handData.lh_keypoints2d, 'red', bbox, scaleFactor);
			}
		}
	});
</script>
