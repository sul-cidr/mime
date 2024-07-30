/** @typedef {Array<number>} Coco13SkeletonNoConfidence */
/** @typedef {Array<number>} Coco13SkeletonWithConfidence */
/** @typedef {Array<{x: number, y: number, z?: number}>} Coco13Pose */

/**
 * @typedef {Object} MinimalPose
 * @property {Coco13SkeletonNoConfidence} keypoints
 * @property {Array<number>} bbox [x0, y0, width, height]
 * @property {Coco13SkeletonNoConfidence} norm
 */

/**
 * @typedef {Object} PoseDbFields
 * @property {string} video_id
 * @property {string} video_name
 * @property {number} frame
 * @property {number} pose_idx
 * @property {number} [distance]
 * @typedef {MinimalPose & PoseDbFields} PoseRecord
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

/**
 * @typedef {Object} VideoRecord
 * @property {string} id
 * @property {string} video_name
 * @property {number} frame_count
 * @property {number} fps
 * @property {number} width
 * @property {number} height
 * @property {string} created_on
 * @property {number} pose_ct
 * @property {number} track_ct
 * @property {number} shot_ct
 * @property {number} poses_per_frame
 * @property {number} face_ct
 */
