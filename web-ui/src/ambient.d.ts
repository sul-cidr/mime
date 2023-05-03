type FixedLengthArray<
  T,
  N extends number,
  R extends readonly T[] = [],
> = R["length"] extends N ? R : Tuple<T, N, readonly [T, ...R]>;

type CocoSkeletonWithConfidence = FixedLengthArray<number, 51>;
type CocoSkeletonNoConfidence = FixedLengthArray<number, 34>;

type VideoRecord = {
  id: number;
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
};

type PoseRecord = {
  video_id: number;
  frame: number;
  pose_idx: number;
  keypoints: CocoSkeletonWithConfidence;
  bbox: FixedLengthArray<number, 4>;
  score: number;
  norm: CocoSkeletonNoConfidence;
  hidden: boolean | undefined;
};
