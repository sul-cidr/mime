<script>
	import { getContext } from 'svelte';
	import { scaleCanvas } from 'layercake';
	import { drawHandOnCanvas } from '$lib/pose-utils';

	/**
	 * @typedef {Object} PoseProps
	 * @property {Array<number>} handData Pose data to be drawn
	 * @property {boolean} isRight Whether the hand is the right hand
	 * @property {number} [scaleFactor] Scale factor to be applied to the pose
	 * @property {BoundingBox} [bbox] Bounding box of the figure -- if supplied, the pose will be drawn with respect to the bbox
	 * @property {boolean} [prepCanvas=true] Whether to prep the canvas before drawing
	 * @returns {void}
	 */

	/** @type {PoseProps} */
	let { handData, isRight, scaleFactor, bbox, prepCanvas = true } = $props();
	const { width, height } = getContext('LayerCake');
	const { ctx } = getContext('canvas');

	// port (left) wine is red, starboard is green
	const color = isRight ? 'green' : 'red';

	$effect(() => {
		if ($ctx) {
			if (prepCanvas) {
				// "Scale your canvas size to retina screens."
				// (see https://layercake.graphics/guide#scalecanvas)
				scaleCanvas($ctx, $width, $height);
				$ctx.clearRect(0, 0, $width, $height);
			}
			drawHandOnCanvas($ctx, handData, color, bbox, scaleFactor);
		}
	});
</script>
