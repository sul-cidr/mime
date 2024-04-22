import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<VideoRecord> = writable();
export const currentFrame: Writable<number | null> = writable();
export const seriesNames: Writable<string[]> = writable([]);
export const currentPose: Writable<PoseRecord | null> = writable();

export const webcamImage: Writable<string> = writable();

export const similarPoseFrames: Writable<{ [frameno: number]: number }> =
  writable({});
export const currentMovelet: Writable<MoveletRecord | null> = writable();
export const currentMoveletPose: Writable<PoseRecord | null> =
  writable();
export const similarMoveletFrames: Writable<{ [frameno: number]: number }> =
  writable({});
export const videoTableData: Writable<JSON> = writable();

export const searchAllVideos: Writable<boolean> = writable(false);

export const searchThresholds: Writable<{ [metric: string]: number }> =
  writable({
    cosine: 0.05,
    euclidean: 37,
    view_invariant: 0.1,
    global: 0.1,
    total_results: 500,
  });
