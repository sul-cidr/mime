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
 * @param {Array<number>} arr - The array to be segmented.
 * @param {number} [l=3] - The length of each segment. Defaults to 3.
 * @return {Array<Array<number>>} - An array of arrays of length l.
 */
export const segmentPose = (arr, l = 3) =>
	[...Array(Math.ceil(arr.length / l))].map(() => arr.splice(0, l));

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

export const getNormDims = (keypoints) => {
	let x_values = [];
	let y_values = [];
	for (let i = 0; i < keypoints.length; i++) {
		if (keypoints[i] >= 0) {
			if (i % 2 == 0) {
				x_values.push(keypoints[i]);
			} else {
				y_values.push(keypoints[i]);
			}
		}
	}

	let min_x = Math.min(...x_values);
	let max_x = Math.max(...x_values);
	let min_y = Math.min(...y_values);
	let max_y = Math.max(...y_values);

	let width = max_x - min_x;
	let height = max_y - min_y;

	return [width, height];
};

export const getExtent = (keypoints) => {
	let x_values = [];
	let y_values = [];
	for (let i = 0; i < keypoints.length; i++) {
		if (i % 3 == 0 && keypoints[i + 2] > 0) {
			x_values.push(keypoints[i]);
		} else if ((i - 1) % 3 == 0 && keypoints[i + 1] > 0) {
			y_values.push(keypoints[i]);
		}
	}

	let min_x = Math.min(...x_values);
	let max_x = Math.max(...x_values);
	let min_y = Math.min(...y_values);
	let max_y = Math.max(...y_values);

	let width = max_x - min_x;
	let height = max_y - min_y;

	return [min_x, min_y, width, height];
};
