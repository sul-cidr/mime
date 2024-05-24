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
 * Calculates the bounds of a COCO 13 pose.
 *
 * @param {Coco13Pose} projCoco13Pose
 * @return {MinimalPose} Minimal pose data with normalized coords and 2D bbox
 */
export const shiftNormalizeRescalePoseCoords = (projCoco13Pose) => {
	const { x: xMin, y: yMin, w: poseWidth, h: poseHeight } = getPoseBounds(projCoco13Pose);
	const scaleFactor = POSE_MAX_DIM / Math.max(poseWidth, poseHeight);

	let xOffset = 0;
	let yOffset = 0;

	if (poseWidth >= poseHeight) {
		yOffset = Math.round((POSE_MAX_DIM - scaleFactor * poseHeight) / 2);
	} else {
		xOffset = Math.round((POSE_MAX_DIM - scaleFactor * poseWidth) / 2);
	}

	/** @type {Coco13SkeletonNoConfidence} */
	let normCoco13Pose = [];

	projCoco13Pose.forEach((c) => {
		normCoco13Pose.push(Math.round((c.x - xMin) * scaleFactor + xOffset));
		normCoco13Pose.push(Math.round((c.y - yMin) * scaleFactor + yOffset));
	});

	const searchPose = {
		keypoints: normCoco13Pose,
		bbox: [xMin, yMin, poseWidth, poseHeight],
		norm: normCoco13Pose
	};

	return searchPose;
};

/**
 * @param {CanvasRenderingContext2D} context
 * @param {Array<Array<number>>} segments
 * @param {number} scaleFactor
 * @returns {void}
 */
export const drawPoseOnCanvas = (context, segments, scaleFactor) => {
	COCO_13_SKELETON.forEach(([from, to], i) => {
		let [fromX, fromY, fromConfidence = null] = segments[from - 1];
		let [toX, toY, toConfidence = null] = segments[to - 1];

		if (fromConfidence === 0 || toConfidence === 0) return;
		if ([fromX, fromY, toX, toY].some((x) => x === -1)) return;

		context.lineWidth = 3;
		context.strokeStyle = COCO_COLORS[i];
		context.beginPath();
		context.moveTo(fromX * scaleFactor, fromY * scaleFactor);
		context.lineTo(toX * scaleFactor, toY * scaleFactor);
		context.stroke();
	});
};

/**
 * Calculates the dimensions of a set of keypoints.  Keypoints with x or y >= 0 are excluded.
 *
 * @param {Array<number>} keypoints - An array of keypoints (without confidence values).
 * @return {Array<number>} [width, height].
 */
export const getKeypointsDimensions = (keypoints) => {
	const segments = segmentKeypoints(keypoints, 2);
	const xValues = segments.map(([x]) => x).filter((x) => x > 0);
	const yValues = segments.map(([, y]) => y).filter((y) => y > 0);

	return [Math.max(...xValues) - Math.min(...xValues), Math.max(...yValues) - Math.min(...yValues)];
};

/**
 * Calculates the bounding box of a set of keypoints.  Keypoints with confidence == 0 are excluded.
 *
 * @param {Array<number>} keypoints - An array of keypoints (with confidence values).
 * @return {Array<number>} [minX, minY, width, height].
 */
export const getKeypointsBounds = (keypoints) => {
	const segments = segmentKeypoints(keypoints).filter(([, , confidence]) => confidence > 0);
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
