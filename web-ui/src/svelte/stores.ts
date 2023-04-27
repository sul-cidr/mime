import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<{
  id: number;
  video_name: string;
  width: number;
  height: number;
}> = writable();
export const currentFrame: Writable<number | undefined> = writable();
