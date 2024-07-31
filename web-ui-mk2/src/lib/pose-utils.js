export const COCO_13_SKELETON = [
	[12, 10],
	[10, 8],
	[13, 11],
	[11, 9],
	[8, 9],
	[2, 8],
	[3, 9],
	[2, 3],
	[2, 4],
	[3, 5],
	[4, 6],
	[5, 7],
	[1, 2],
	[1, 3]
];

export const COCO_COLORS = [
	'orangered',
	'orange',
	'blue',
	'lightblue',
	'darkgreen',
	'red',
	'lightgreen',
	'pink',
	'plum',
	'purple',
	'brown',
	'saddlebrown',
	'mediumorchid',
	'gray',
	'salmon',
	'chartreuse',
	'lightgray',
	'darkturquoise',
	'goldenrod'
];

export const BLAZE_33_TO_COCO_13 = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];

/**
 * Segments an array into an array of arrays of a specified length.
 *
 * @param {Array<number>} arr - The keypoints array to be segmented.
 * @param {number} [l=3] - The length of each segment. Defaults to 3.
 * @return {Array<Array<number>>} - An array of arrays of length l.
 */
export const segmentKeypoints = (arr, l = 3) => {
	const _arr = [...arr];
	return [...Array(Math.ceil(arr.length / l))].map(() => _arr.splice(0, l));
};

/**
 * Calculates the bounds of a COCO 13 pose.
 *
 * @param {Coco13Pose} coco13Pose
 * @return {PoseBoundsObject}
 */
export const getPoseBounds = (coco13Pose) => {
	const xMin = Math.min(...coco13Pose.map(({ x }) => x));
	const xMax = Math.max(...coco13Pose.map(({ x }) => x));
	const yMin = Math.min(...coco13Pose.map(({ y }) => y));
	const yMax = Math.max(...coco13Pose.map(({ y }) => y));
	const zMin = Math.min(...coco13Pose.map(({ z }) => z ?? 0));
	const zMax = Math.max(...coco13Pose.map(({ z }) => z ?? 0));

	return {
		x: xMin,
		y: yMin,
		z: zMin,
		w: xMax - xMin,
		h: yMax - yMin,
		d: zMax - zMin
	};
};

// This value should be the same in the Python and JS code, so ideally it would
// be set somewhere that is accessible to both
export const POSE_MAX_DIM = 100;

/**
 * Shifts, normalizes, and rescales keypoints.
 *
 * @param {Array<number>} keypoints - An array of keypoints.
 * @return {Array<number>} An array of normalized and rescaled keypoints.
 */
export const shiftNormalizeRescaleKeypoints = (keypoints) => {
	const [xMin, yMin, w, h] = getKeypointsBounds(keypoints, false);
	const scaleFactor = POSE_MAX_DIM / Math.max(w, h);

	let xOffset = 0;
	let yOffset = 0;

	if (w >= h) {
		yOffset = (POSE_MAX_DIM - scaleFactor * h) / 2;
	} else {
		xOffset = (POSE_MAX_DIM - scaleFactor * w) / 2;
	}

	return keypoints
		.map((c, i) =>
			i % 2 ? (c - yMin) * scaleFactor + yOffset : (c - xMin) * scaleFactor + xOffset
		)
		.flat();
};

/**
 * @param {CanvasRenderingContext2D} context
 * @param {Array<number>} poseData
 * @param {boolean} fitToCanvas
 * @returns {void}
 */
export const drawPoseOnCanvas = (context, poseData, fitToCanvas) => {
	let scaleFactor = 1;
	const segments = segmentKeypoints(poseData, poseData.length / (COCO_13_SKELETON.length - 1));
	let xAdjust = 0;
	let yAdjust = 0;

	if (fitToCanvas) {
		const [xMin, yMin, width, height] = getKeypointsBounds(poseData, /* hasConfidence= */ false);
		const xMid = (xMin * 2 + width) / 2;
		const yMid = (yMin * 2 + height) / 2;

		if (width > height) {
			scaleFactor = context.canvas.width / width;
			yAdjust = ((yMin - yMid) * scaleFactor) / 2;
		} else {
			scaleFactor = context.canvas.height / height;
			xAdjust = ((xMin - xMid) * scaleFactor) / 2;
		}
	}

	COCO_13_SKELETON.forEach(([from, to], i) => {
		let [fromX, fromY, fromConfidence = null] = segments[from - 1];
		let [toX, toY, toConfidence = null] = segments[to - 1];

		if (fromConfidence === 0 || toConfidence === 0) return;
		if ([fromX, fromY, toX, toY].some((x) => x === -1)) return;

		context.lineWidth = 3;
		context.strokeStyle = COCO_COLORS[i];
		context.beginPath();
		context.moveTo(fromX * scaleFactor + xAdjust, fromY * scaleFactor + yAdjust);
		context.lineTo(toX * scaleFactor + xAdjust, toY * scaleFactor + yAdjust);
		context.stroke();
	});
};

/**
 * Calculates the bounding box of a set of keypoints.  Keypoints with confidence == 0 are excluded.
 *
 * @param {Array<number>} keypoints - An array of keypoints.
 * @param {boolean} hasConfidence - Whether the keypoints array contains confidence values.
 * @return {Array<number>} [minX, minY, width, height].
 */
export const getKeypointsBounds = (keypoints, hasConfidence = true) => {
	const segments = hasConfidence
		? segmentKeypoints(keypoints).filter(([, , confidence]) => confidence > 0)
		: segmentKeypoints(keypoints, 2);
	const xValues = segments.map(([x]) => x);
	const yValues = segments.map(([, y]) => y);

	const minX = Math.min(...xValues);
	const maxX = Math.max(...xValues);
	const minY = Math.min(...yValues);
	const maxY = Math.max(...yValues);

	const width = maxX - minX;
	const height = maxY - minY;

	return [minX, minY, width, height];
};
