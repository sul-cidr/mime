type VideoRecord = {
  id: number;
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
};

type PoseData = {
  video_id: number;
  frame: number;
  pose_idx: number;
  keypoints: Array<number>;
  bbox: Array<number>;
  score: number;
  norm: Array<number>;
  hidden: boolean | undefined;
};
