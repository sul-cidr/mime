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

export const HAND_21_KEYPOINTS = [
	'ulnar_palm',
	'radial_palm',
	'thumb_metacarpal',
	'thumb_proximal',
	'thumb_distal',
	'index_metacarpal',
	'index_proximal',
	'index_middle',
	'index_distal',
	'middle_metacarpal',
	'middle_proximal',
	'middle_middle',
	'middle_distal',
	'ring_metacarpal',
	'ring_proximal',
	'ring_middle',
	'ring_distal',
	'pinkie_metacarpal',
	'pinkie_proximal',
	'pinkie_middle',
	'pinkie_distal'
];

export const HAND_21_SKELETON = [
	[1, 2],
	[1, 18],
	[2, 3],
	[3, 4],
	[3, 6],
	[4, 5],
	[6, 10],
	[6, 7],
	[7, 8],
	[8, 9],
	[10, 14],
	[10, 11],
	[11, 12],
	[12, 13],
	[14, 18],
	[14, 15],
	[15, 16],
	[16, 17],
	[18, 19],
	[19, 20],
	[20, 21]
];

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
export const shiftNormalizeRescaleKeypoints = (keypoints, invertY=false) => {
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
 * @param {number} canvasWidth
 * @param {number} canvasHeight
 * @param {BoundingBox} [bbox]
 * @param {number} [scaleFactor=1]
 * @returns {void}
 */
export const drawPoseOnCanvas = (
	context,
	poseData,
	canvasWidth,
	canvasHeight,
	bbox,
	scaleFactor = 1
) => {
	let xAdjust = 0;
	let yAdjust = 0;

	if (bbox) {
		poseData = poseData
			.filter((_, i) => (i + 1) % 3 !== 0) // filter out confidence
			.map((v, i) => (i % 2 ? v - bbox[1] : v - bbox[0])); // shift with respect to bbox

		// calculate scale factor and x/y adjustment based on whether the bbox is wide or tall
		const [, , width, height] = bbox;
		if (width > height) {
			scaleFactor = canvasWidth / width;
			yAdjust = (canvasHeight - height * scaleFactor) / 2;
		} else {
			scaleFactor = canvasHeight / height;
			xAdjust = (canvasWidth - width * scaleFactor) / 2;
		}
	}

	const segments = segmentKeypoints(poseData, poseData.length / (COCO_13_SKELETON.length - 1));

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

/**
 * Inverts a set of 2D keypoints that are expected to be normed (where x and y
 * are always beteween 0 and 100) within the bounding box of the keypoints,
 * flipping the pose around its Y axis midpoint. This is needed when e.g., the
 * camera software produces coordinats with y=0 at the top, while the drawing/
 * rendering tools assume y=0 is at the bottom.
 *
 * @param {Number[]} keypoints
 * @return {Number[]}
 */
export const invertNormedKeypoints = (keypoints) => {
	const segments = segmentKeypoints(keypoints, 2);
	const yValues = segments.map(([, y]) => y);

	const minY = Math.min(...yValues);
	const maxY = Math.max(...yValues);
	const midY = (maxY - minY) / 2;

	return keypoints.map((val, i) => {
		if ((i + 1) % 2 === 0) {
			if (val > midY) {
				return midY - (val - midY) 
			} else {
				return midY + (midY - val)
			}
		} else {
			return val;
		}
	})
}

/**
 * Draws a hand skeleton on a canvas.
 *
 * @param {CanvasRenderingContext2D} ctx - Canvas context to draw on.
 * @param {Array<number>} handPoints - The 2D keypoints of the hand, as an array of x, y pairs.
 * @param {number} canvasWidth
 * @param {number} canvasHeight
 * @param {BoundingBox} [bbox]
 * @param {number} [scaleFactor=1] - The scale factor to apply to the keypoints.
 * @param {string} [color='red'] - The color to draw the hand in. Defaults to red.
 */
export const drawHandOnCanvas = (
	ctx,
	handPoints,
	canvasWidth,
	canvasHeight,
	bbox,
	scaleFactor = 1,
	color = 'red'
) => {
	if (handPoints === undefined || handPoints === null) return;

	let xAdjust = 0;
	let yAdjust = 0;

	if (bbox) {
		handPoints = handPoints.map((v, i) => (i % 2 ? v - bbox[1] : v - bbox[0])); // shift with respect to bbox

		const [, , width, height] = bbox;
		if (width > height) {
			scaleFactor = canvasWidth / width;
			yAdjust = (canvasHeight - height * scaleFactor) / 2;
		} else {
			scaleFactor = canvasHeight / height;
			xAdjust = (canvasWidth - width * scaleFactor) / 2;
		}
	}

	const segments = segmentKeypoints(handPoints, 2);

	HAND_21_SKELETON.forEach(([from, to]) => {
		let fromX, fromY, toX, toY;
		[fromX, fromY] = segments[from - 1];
		[toX, toY] = segments[to - 1];

		ctx.lineWidth = scaleFactor > 0.8 ? 3 : 2;
		ctx.strokeStyle = color;

		ctx.beginPath();
		ctx.moveTo(fromX * scaleFactor + xAdjust, fromY * scaleFactor + yAdjust);
		ctx.lineTo(toX * scaleFactor + xAdjust, toY * scaleFactor + yAdjust);
		ctx.stroke();
	});
};
