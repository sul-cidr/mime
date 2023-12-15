// Not currently used, but worth keeping around for a bit
const shiftToOrigin = (
  keypoints: CocoSkeletonWithConfidence,
  bbox: FixedLengthArray<number, 4>,
) => {
  let newKeypoints: CocoSkeletonWithConfidence = [...keypoints];

  for (let x: number = 0; x < keypoints.length; x += 3) {
    newKeypoints[x] -= bbox[0];
  }
  for (let y: number = 1; y < keypoints.length; y += 3) {
    newKeypoints[y] -= bbox[1];
  }
  return newKeypoints;
};

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
