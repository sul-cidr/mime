export const COCO_17_SKELETON = [
  [16, 14],
  [14, 12],
  [17, 15],
  [15, 13],
  [12, 13],
  [6, 12],
  [7, 13],
  [6, 7],
  [6, 8],
  [7, 9],
  [8, 10],
  [9, 11],
  [2, 3],
  [1, 2],
  [1, 3],
  [2, 4],
  [3, 5],
  [4, 6],
  [5, 7],
];

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
  [1, 3],
];

export const COCO_13_KEYPOINTS = [
  "nose",  // 0
  "left_shoulder",  // 1
  "right_shoulder",  // 2
  "left_elbow",  // 3
  "right_elbow",  // 4
  "left_wrist",  // 5
  "right_wrist",  // 6
  "left_hip",  // 7
  "right_hip",  // 8
  "left_knee",  // 9
  "right_knee",  // 10
  "left_ankle",  // 11
  "right_ankle",  // 12
]

export const HAND_21_KEYPOINTS = [
  "ulnar_palm",
  "radial_palm",
  "thumb_metacarpal",
  "thumb_proximal",
  "thumb_distal",
  "index_metacarpal",
  "index_proximal",
  "index_middle",
  "index_distal",
  "middle_metacarpal",
  "middle_proximal",
  "middle_middle",
  "middle_distal",
  "ring_metacarpal",
  "ring_proximal",
  "ring_middle",
  "ring_distal",
  "pinkie_metacarpal",
  "pinkie_proximal",
  "pinkie_middle",
  "pinkie_distal",
]

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
  [20, 21],
]

export const COCO_COLORS = [
  "orangered",
  "orange",
  "blue",
  "lightblue",
  "darkgreen",
  "red",
  "lightgreen",
  "pink",
  "plum",
  "purple",
  "brown",
  "saddlebrown",
  "mediumorchid",
  "gray",
  "salmon",
  "chartreuse",
  "lightgray",
  "darkturquoise",
  "goldenrod",
];

export const COCO_13_DEFAULT = [
  [0, 50, 0],
  [11, 35, 0],
  [-11, 35, 0],
  [14, 15, 0],
  [-14, 15, 0],
  [15, -4, 0],
  [-15, -4, 0],
  [7, 0, 0],
  [-7, 0, 0],
  [7, -25, 0],
  [-7, -25, 0],
  [7, -50, -0],
  [-7, -50, -0],
];

// Not currently used, but worth keeping around for a bit
// const shiftToOrigin = (
//   keypoints: CocoSkeletonWithConfidence,
//   bbox: FixedLengthArray<number, 4>,
// ) => {
//   let newKeypoints: CocoSkeletonWithConfidence = [...keypoints];

//   for (let x: number = 0; x < keypoints.length; x += 3) {
//     newKeypoints[x] -= bbox[0];
//   }
//   for (let y: number = 1; y < keypoints.length; y += 3) {
//     newKeypoints[y] -= bbox[1];
//   }
//   return newKeypoints;
// };

// This value should be the same in the Python and JS code, so ideally it would
// be set somewhere that is accessible to both
export const POSE_MAX_DIM = 100;

export const blaze33ToCoco17Coords = [
  0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
];
export const blaze33ToCoco13Coords = [
  0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
];

export const getPoseExtent = (
  coco13Pose: Array<{ x: number; y: number; z: number }>,
) => {
  let xmin = null;
  let xmax = null;
  let ymin = null;
  let ymax = null;
  let zmin = null;
  let zmax = null;

  coco13Pose.forEach((c) => {
    xmin = xmin === null ? c.x : Math.min(xmin, c.x);
    xmax = xmax === null ? c.x : Math.max(xmax, c.x);
    ymin = ymin === null ? c.y : Math.min(ymin, c.y);
    ymax = ymax === null ? c.y : Math.max(ymax, c.y);
    zmin = zmin === null ? c.z : Math.min(zmin, c.z);
    zmax = zmax === null ? c.z : Math.max(zmax, c.z);
  });
  const poseWidth = xmax - xmin;
  const poseHeight = ymax - ymin;
  const poseDepth = zmax - zmin;

  return {
    x: xmin,
    y: ymin,
    z: zmin,
    w: poseWidth,
    h: poseHeight,
    d: poseDepth,
  };
};

export const getPoseVectorExtent = (poseVector: [], dims: number = 3) => {
  let posePoints: Array<{ x: number; y: number; z: number }> = [];
  for (let p = 0; p < poseVector.length; p += dims) {
    posePoints.push({
      x: poseVector[p],
      y: poseVector[p + 1],
      z: poseVector[p + 2],
    });
  }
  return getPoseExtent(posePoints);
};

export const shiftNormalizeRescalePoseCoords = (
  projCoco13Pose: any[],
  videoId: string,
  xmin: number,
  ymin: number,
  poseWidth: number,
  poseHeight: number,
) => {
  // Expects an array of 13 2D coordinate pairs in the image domain
  // [[x, y], ...]
  // Returns a PoseRecord object with the normalized coords filled in.

  const scaleFactor = POSE_MAX_DIM / Math.max(poseWidth, poseHeight);

  let xRecenter = 0;
  let yRecenter = 0;

  if (poseWidth >= poseHeight) {
    yRecenter = Math.round((POSE_MAX_DIM - scaleFactor * poseHeight) / 2);
  } else {
    xRecenter = Math.round((POSE_MAX_DIM - scaleFactor * poseWidth) / 2);
  }

  let normCoco13Pose = [];

  projCoco13Pose.forEach((c) => {
    normCoco13Pose.push(Math.round((c.x - xmin) * scaleFactor + xRecenter));
    normCoco13Pose.push(Math.round((c.y - ymin) * scaleFactor + yRecenter));
  });

  const searchPose: PoseRecord = {
    video_id: videoId,
    frame: 0,
    pose_idx: 0,
    keypoints: normCoco13Pose,
    //keypointsopp: Coco17SkeletonWithConfidence;
    bbox: [xmin, ymin, poseWidth, poseHeight],
    score: 1.0,
    track_id: 0,
    norm: normCoco13Pose,
    //face_bbox: FixedLengthArray<number, 4> | undefined; // copied from FaceRecord
    //face_landmarks: FaceLandmarks | undefined; // if match is found
    //keypoints4dh: SmplSkeletonWithConfidence | undefined;
    //norm4dh: SmplSkeletonNoConfidence | undefined;
    hidden: false,
    //distance?: number;
    //shot: number | 0;
    //face_cluster_id: number | null;
    //pose_interest: number | 0;
    //action_interest: number | 0;
    from_webcam: true,
  };

  return searchPose;
};

const getXywh = (x_values: Array<number>, y_values: Array<number>) => {
  let min_x = Math.min(...x_values);
  let max_x = Math.max(...x_values);
  let min_y = Math.min(...y_values);
  let max_y = Math.max(...y_values);

  let width = max_x - min_x;
  let height = max_y - min_y;

  return [min_x, min_y, width, height];
}

export const getNormDims = (keypoints: CocoSkeletonNoConfidence) => {
  let x_values: Array<number> = [];
  let y_values: Array<number> = [];
  for (let i: number = 0; i < keypoints.length; i++) {
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

export const getExtent = (keypoints: CocoSkeletonWithConfidence) => {
  let x_values: Array<number> = [];
  let y_values: Array<number> = [];
  for (let i: number = 0; i < keypoints.length; i++) {
    if (i % 3 == 0 && keypoints[i + 2] > 0) {
      x_values.push(keypoints[i]);
    } else if ((i - 1) % 3 == 0 && keypoints[i + 1] > 0) {
      y_values.push(keypoints[i]);
    }
  }
  return getXywh(x_values, y_values);
};

export const getExtentFlat = (keypoints: Array<number> = []) => {
  let x_values: Array<number> = [];
  let y_values: Array<number> = [];
  for (let i: number = 0; i < keypoints.length; i++) {
    if (i % 2 == 0) {
      x_values.push(keypoints[i]);
    } else {
      y_values.push(keypoints[i]);
    }
  }
  return getXywh(x_values, y_values);
};

export const get3DPoseExtent = (
  poses: Array<number>[] = [],
  minsSoFar = [null, null, null],
  maxsSoFar = [null, null, null],
) => {
  const poseMin = poses.reduce(
    (poseMins, coords) => [
      poseMins[0] === null ? coords[0] : Math.min(poseMins[0], coords[0]),
      poseMins[1] === null ? coords[1] : Math.min(poseMins[1], coords[1]),
      poseMins[2] === null ? coords[2] : Math.min(poseMins[2], coords[2]),
    ],
    minsSoFar,
  );
  const poseMax = poses.reduce(
    (poseMaxs, coords) => [
      poseMaxs[0] === null ? coords[0] : Math.max(poseMaxs[0], coords[0]),
      poseMaxs[1] === null ? coords[1] : Math.max(poseMaxs[1], coords[1]),
      poseMaxs[2] === null ? coords[2] : Math.max(poseMaxs[2], coords[2]),
    ],
    maxsSoFar,
  );
  return [poseMin, poseMax];
};