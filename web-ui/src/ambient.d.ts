type FixedLengthArray<
  T,
  N extends number,
  R extends readonly T[] = [],
> = R["length"] extends N ? R : Tuple<T, N, readonly [T, ...R]>;

type Coco13SkeletonWithConfidence = FixedLengthArray<number, 39>;
type Coco13SkeletonNoConfidence = FixedLengthArray<number, 26>;
type Coco17SkeletonWithConfidence = FixedLengthArray<number, 51>;
type Coco17SkeletonNoConfidence = FixedLengthArray<number, 34>;
type SmplSkeletonWithConfidence = FixedLengthArray<number, 135>;
type SmplSkeletonNoConfidence = FixedLengthArray<number, 90>;
type CocoSkeletonWithConfidence =
  | Coco13SkeletonWithConfidence
  | Coco17SkeletonWithConfidence;
type CocoSkeletonNoConfidence =
  | Coco13SkeletonNoConfidence
  | Coco17SkeletonNoConfidence;
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
  keypoints: Coco13SkeletonNoConfidence;
  keypointsopp: Coco17SkeletonWithConfidence | undefined;
  bbox: FixedLengthArray<number, 4>; // bbox format for PifPaf is x0, y0, width, height
  score: number;
  track_id: number | null;
  norm: Coco13SkeletonNoConfidence;
  face_bbox: FixedLengthArray<number, 4> | undefined; // copied from FaceRecord
  face_landmarks: FaceLandmarks | undefined; // if match is found
  keypoints4dh: SmplSkeletonWithConfidence | undefined;
  norm4dh: SmplSkeletonNoConfidence | undefined;
  hidden: boolean | undefined;
  distance?: number;
  shot: number | 0;
  face_cluster_id: number | null;
  pose_interest: number | 0; // this is actually the avg for all poses in the frame :-/
  from_webcam: boolean | false;
};

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
  interest: number | undefined;
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
  prev_norm: Coco13SkeletonNoConfidence;
  norm: Coco13SkeletonNoConfidence;
  hidden: boolean | undefined;
  distance?: number;
  cluster_id: number;
  face_cluster_id: number | null;
  time: string | undefined;
};
