import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<VideoRecord> = writable();
export const currentFrame: Writable<number | undefined> = writable();
export const currentPose: Writable<PoseData> = writable();
