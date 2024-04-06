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

export const getPoseExtent = (coco13Pose: any[]) => {
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

  return {x: xmin, y: ymin, z: zmin, w: poseWidth, h: poseHeight, d: poseDepth};
}

export const shiftNormalizeRescalePoseCoords = (projCoco13Pose: any[], videoId: number, xmin: number, ymin: number, poseWidth:number, poseHeight:number) => {
  // Expects an array of 13 2D coordinate pairs in the image domain
  // [[x, y], ...]
  // Returns a PoseRecord object with the normalized coords filled in.

  const scaleFactor = POSE_MAX_DIM / Math.max(poseWidth, poseHeight);

  let xRecenter = 0;
  let yRecenter = 0;

  if (poseWidth >= poseHeight) {
    yRecenter = Math.round((POSE_MAX_DIM - (scaleFactor * poseHeight)) / 2);
  } else {
    xRecenter = Math.round((POSE_MAX_DIM - (scaleFactor * poseWidth)) / 2);
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
    //pose_interest: number | 0; // this is actually the avg for all poses in the frame :-/
    from_webcam: true,
  };

  return searchPose;

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

  let min_x = Math.min(...x_values);
  let max_x = Math.max(...x_values);
  let min_y = Math.min(...y_values);
  let max_y = Math.max(...y_values);

  let width = max_x - min_x;
  let height = max_y - min_y;

  return [min_x, min_y, width, height];
};
