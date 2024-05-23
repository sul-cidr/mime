/** @typedef {Array<number>} Coco13SkeletonNoConfidence */
/** @typedef {Array<{x: number, y: number, z?: number}>} Coco13Pose */

/**
 * @typedef {Object} MinimalPose
 * @property {Coco13SkeletonNoConfidence} keypoints
 * @property {Array<number>} bbox [x0, y0, width, height]
 * @property {Coco13SkeletonNoConfidence} norm
 */

/**
 * @typedef {Object} PoseBoundsObject
 * @property {number} x start x
 * @property {number} y start y
 * @property {number} z start z
 * @property {number} w width
 * @property {number} h height
 * @property {number} d depth
 */
