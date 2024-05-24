<script>
	import { page } from '$app/stores';
	import {
		COCO_13_SKELETON,
		COCO_COLORS,
		segmentPose,
		getNormDims,
		getExtent,
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
	// const width = 180;
	// const normalizationFactor = normalizedPose ? width / 100 : 1;

	/**
	 * @param {CanvasRenderingContext2D} context
	 * @param {Array<Array<number>>} segments
	 * @returns {void}
	 */
	const draw = (context, segments) => {
		const width = 360;
		const normalizationFactor = width / 100;
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

	<img
		class="object-contain h-full w-full"
		src={`${$page.data.apiBase}/frame/resize/${sourcePose.video_id}/${sourcePose.frame}/${getExtent(
			sourcePose.keypoints
		).join(',')}|${getNormDims(sourcePose.norm).join(',')}/`}
		alt={`Frame ${sourcePose.frame}, Pose: ${sourcePose.pose_idx + 1}`}
	/>
	<canvas bind:this={canvasElement}></canvas>
</div>

<style>
	div {
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
	}

	img,
	canvas {
		height: 100%;
		width: 100%;
		object-fit: contain;
		position: absolute;
		top: 0;
		left: 0;
	}
</style>
