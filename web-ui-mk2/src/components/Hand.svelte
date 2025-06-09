<script>
	import { getContext } from 'svelte';
	import { drawHandOnCanvas } from '$lib/pose-utils';

	/**
	 * @typedef {Object} PoseProps
	 * @property {Array<number>} handData Pose data to be drawn
	 * @property {boolean} isRight Whether the hand is the right hand
	 * @property {number} [scaleFactor] Scale factor to be applied to the pose
	 * @property {BoundingBox} [bbox] Bounding box of the figure -- if supplied, the pose will be drawn with respect to the bbox
	 * @returns {void}
	 */

	/** @type {PoseProps} */
	let { handData, isRight, scaleFactor, bbox } = $props();

	// port (left) wine is red, starboard is green
	const color = isRight ? 'green' : 'red';
	const { ctx } = getContext('canvas');

	$effect(() => {
		if ($ctx) drawHandOnCanvas($ctx, handData, color, bbox, scaleFactor);
	});
</script>
