<script>
	import {
		COCO_13_SKELETON,
		COCO_COLORS,
		segmentPose,
		shiftNormalizeRescalePoseCoords
	} from '$lib/pose-utils';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	let canvasElement = $state();

	const scaleFactor = 1;
	const normalizedPose = true;
	const width = 290;
	const normalizationFactor = normalizedPose ? width / 100 : 1;

	/**
	 * @param {CanvasRenderingContext2D} context
	 * @param {Array<Array<number>>} segments
	 * @returns {void}
	 */
	const draw = (context, segments) => {
		console.log(context, segments);
		COCO_13_SKELETON.forEach(([from, to], i) => {
			let fromX, fromY, toX, toY, fromConfidence, toConfidence;
			[fromX, fromY, fromConfidence = null] = segments[from - 1];
			[toX, toY, toConfidence = null] = segments[to - 1];
			if (fromConfidence === 0 || toConfidence === 0) return;
			if ([fromX, fromY, toX, toY].some((x) => x === -1)) return;

			context.lineWidth = scaleFactor > 0.8 ? 3 : 2;
			context.strokeStyle = COCO_COLORS[i];

			context.beginPath();
			context.moveTo(
				fromX * normalizationFactor * scaleFactor,
				fromY * normalizationFactor * scaleFactor
			);
			context.lineTo(
				toX * normalizationFactor * scaleFactor,
				toY * normalizationFactor * scaleFactor
			);
			context.stroke();
		});
	};

	const init = async () => {
		const canvasCtx = canvasElement.getContext('2d');
		const segments = segmentPose(sourcePose.norm, 2);
		draw(canvasCtx, segments);
	};
</script>

<div>
	{#await init()}
		Loading...
	{:then}
		<p></p>
	{/await}
	<canvas bind:this={canvasElement}></canvas>
</div>

<style>
</style>
