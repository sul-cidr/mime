type FixedLengthArray<
  T,
  N extends number,
  R extends readonly T[] = [],
> = R["length"] extends N ? R : Tuple<T, N, readonly [T, ...R]>;

type CocoSkeletonWithConfidence = FixedLengthArray<number, 51>;
type CocoSkeletonNoConfidence = FixedLengthArray<number, 34>;
type SmplSkeletonWithConfidence = FixedLengthArray<number, 135>;
type SmplSkeletonNoConfidence = FixedLengthArray<number, 90>;
type FaceLandmarks = FixedLengthArray<number, 10>;
type FaceEmbedding = FixedLengthArray<number, 4096>;

type VideoRecord = {
  id: string; // TODO UUID
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
  pose_ct: number;
  poses_per_frame: number;
  face_ct: number;
  track_ct: number;
  shot_ct: number;
};

type PoseRecord = {
  video_id: number;
  frame: number;
  pose_idx: number;
  keypoints: CocoSkeletonWithConfidence;
  bbox: FixedLengthArray<number, 4>; // bbox format for PifPaf is x0, y0, width, height
  score: number;
  track_id: number | null;
  norm: CocoSkeletonNoConfidence;
  face_bbox: FixedLengthArray<number, 4> | undefined; // copied from FaceRecord
  face_landmarks: FaceLandmarks | undefined; // if match is found
  keypoints4dh: SmplSkeletonWithConfidence;
  norm4dh: SmplSkeletonNoConfidence;
  hidden: boolean | undefined;
  distance?: number;
  shot: number | 0;
};

interface MoveletPoseRecord extends PoseRecord {
  track_id: number;
}

type FaceRecord = {
  video_id: number;
  frame: number;
  pose_idx: number;
  bbox: FixedLengthArray<number, 4>;
  confidence: number;
  landmarks: FaceLandmarks;
  embedding: FaceEmbedding;
  track_id: number;
  cluster_id: number;
  time: string | undefined;
};

type FrameRecord = {
  frame: number;
  avgScore: number;
  poseCt: number;
  trackCt: number;
  isShot: number | undefined;
  movement: number | undefined;
  sim_pose: number | undefined;
  sim_move: number | undefined;
  time: string | undefined;
  shot: number | 0;
};

type ShotRecord = {
  frame: number;
  isShot: number | undefined;
  shot: number | 0;
};

type MoveletRecord = {
  video_id: number;
  track_id: number;
  start_frame: number;
  end_frame: number;
  pose_idx: number;
  prev_norm: CocoSkeletonNoConfidence;
  norm: CocoSkeletonNoConfidence;
  hidden: boolean | undefined;
  distance?: number;
  cluster_id: number;
  time: string | undefined;
};
