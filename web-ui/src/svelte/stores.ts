import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<VideoRecord> = writable();
export const currentFrame: Writable<number | undefined> = writable();
export const seriesNames: Writable<string[]> = writable([]);
export const currentPose: Writable<PoseRecord> = writable();
export const similarPoseFrames: Writable<{ [frameno: number]: number }> =
  writable({});
export const currentMovelet: Writable<MoveletRecord> = writable();
export const currentMoveletPose: Writable<MoveletPoseRecord> = writable();
export const similarMoveletFrames: Writable<{ [frameno: number]: number }> =
  writable({});
export const videoTableData: Writable<JSON> = writable();
export const maxDistances: Writable<{ [metric: string]: number }> =
  writable({"cosine": .05, "euclidean": 37, "view_invariant": .1});
