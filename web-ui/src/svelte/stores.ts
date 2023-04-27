import { Writable, writable } from "svelte/store";

export type VideoRecord = {
  id: number;
  video_name: string;
  width: number;
  height: number;
  frame_count: number;
  fps: number;
};

export const currentVideo: Writable<VideoRecord> = writable();
export const currentFrame: Writable<number | undefined> = writable();
