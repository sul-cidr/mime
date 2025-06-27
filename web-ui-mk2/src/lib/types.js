/**
 * @typedef {[
 *   number, number, number, number, number, number, number, number,
 *   number, number, number, number, number, number, number, number,
 *   number, number, number, number, number, number, number, number,
 *   number, number
 * ]} Coco13SkeletonNoConfidence 13 x,y coordinates for 26 array elements
 */

/**
 * @typedef {[
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number
 * ]} Coco13SkeletonWithConfidence 13 x,y,confidence coordinates for 39 array elements
 */

/**
 * @typedef {[
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number, number,
 *    number, number, number, number, number, number, number
 * ]} Coco13Skeleton3d 13 x,y,z coordinates (structurally but not logically equivalent to the above)
 */

/** @typedef {Array<{x: number, y: number, z?: number}>} Coco13Pose */

/** @typedef {Array<number>} BoundingBox */

/**
 * @typedef {Object} MinimalPose
 * @property {Coco13SkeletonNoConfidence} keypoints
 * @property {Array<number>} bbox [x0, y0, width, height]
 * @property {Coco13SkeletonNoConfidence} norm
 * @property {Coco13Skeleton3d} global3d_coco13
 */

/**
 * @typedef {Object} PoseDbFields
 * @property {string} video_id
 * @property {string} video_name
 * @property {number} frame
 * @property {number} pose_idx
 * @property {number} [distance]
 * @property {Array<number>} [rh_keypoints2d] 42-keypoints representing the right hand
 * @property {Array<number>} [rh_global_orient] 9-element array representing a transform for the right hand
 * @property {Array<number>} [lh_keypoints2d] 42-keypoints representing the left hand
 * @property {Array<number>} [lh_global_orient] 9-element array representing a transform for the left hand
 */

/**
 * @typedef {Object} ArchetypeMetadata
 * @property {string} provenance
 * @property {string} description
 * @property {string} image_filename

/**
 * @typedef {MinimalPose & PoseDbFields} PoseRecord
 */

/**
 * @typedef {MinimalPose & PoseDbFields & ArchetypeMetadata & ArchetypeMetadata} PoseArchetype
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
 * @property {number} hand_ct
 */

/**
 * @typedef {Object} HandForSearching
 * @property {boolean} is_right
 * @property {Array<number>} keypoints
 * @property {Array<number>} global_orient
 * @property {Array<number>} class_weights
 * @property {Array<number>} joint_angles3d
 * @property {Array<number>} global3d
 * @property {string} [video_id]
 * @property {number} [frame]
 * @property {number} [pose_idx]
 */

/**
 * @typedef {Object} HandForDrawing
 * @property {boolean} is_right
 * @property {Array<number>} [rh_keypoints2d]
 * @property {Array<number>} [rh_global_orient]
 * @property {Array<number>} [lh_keypoints2d]
 * @property {Array<number>} [lh_global_orient]
 * @property {Array<number>} [bbox]
 */
