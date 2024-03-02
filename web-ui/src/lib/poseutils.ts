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

export const getPoseExtent = (projCoco13Pose: any[]) => {
  let xmin = null;
  let xmax = null;
  let ymin = null;
  let ymax = null;

  projCoco13Pose.forEach((c) => {
    xmin = xmin === null ? c[0] : Math.min(xmin, c[0]);
    xmax = xmax === null ? c[0] : Math.max(xmax, c[0]);
    ymin = ymin === null ? c[1] : Math.min(ymin, c[1]);
    ymax = ymax === null ? c[1] : Math.max(ymax, c[1]);
  });
  const poseWidth = xmax - xmin;
  const poseHeight = ymax - ymin;

  return [xmin, ymin, poseWidth, poseHeight];
}

export const shiftNormalizeRescalePoseCoords = (projCoco13Pose: any[], videoId: number) => {
  // Expects an array of 13 2D coordinate pairs in the image domain
  // [[x, y], ...]
  // Returns a PoseRecord object with the normalized coords filled in.

  let [xmin, ymin, poseWidth, poseHeight] = getPoseExtent(projCoco13Pose);

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
    normCoco13Pose.push(Math.round((c[0] - xmin) * scaleFactor + xRecenter));
    normCoco13Pose.push(Math.round((c[1] - ymin) * scaleFactor + yRecenter));
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
