import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<VideoRecord> = writable();
export const currentFrame: Writable<number | undefined> = writable();
export const seriesNames: Writable<string[]> = writable([]);
export const currentPose: Writable<PoseRecord> = writable();
export const similarPoseFrames: Writable<{[frameno: number]: number}> = writable({});
export const currentMovelet: Writable<MoveletRecord> = writable();
export const currentMoveletPose: Writable<PoseRecord> = writable();
export const similarMoveletFrames: Writable<{[frameno: number]: number}> = writable({});
export const videoTableData: Writable<JSON> = writable();
