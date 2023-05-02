type VideoRecord = {
  id: number;
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
};

type PoseData = {
  keypoints: Array<number>;
  bbox: Array<number>;
  score: number;
  hidden: boolean | undefined;
};
