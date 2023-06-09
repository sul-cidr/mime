type FixedLengthArray<
  T,
  N extends number,
  R extends readonly T[] = [],
> = R["length"] extends N ? R : Tuple<T, N, readonly [T, ...R]>;

type CocoSkeletonWithConfidence = FixedLengthArray<number, 51>;
type CocoSkeletonNoConfidence = FixedLengthArray<number, 34>;

type VideoRecord = {
  id: string; // TODO UUID
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
  pose_ct: number;
  poses_per_frame: number;
};

type PoseRecord = {
  video_id: number;
  frame: number;
  pose_idx: number;
  keypoints: CocoSkeletonWithConfidence;
  bbox: FixedLengthArray<number, 4>; // bbox format for PifPaf is x0, y0, width, height
  score: number;
  norm: CocoSkeletonNoConfidence;
  hidden: boolean | undefined;
  distance?: number;
};

type FrameRecord = {
  frame: number;
  avgScore: number;
  poseCt: number;
};
