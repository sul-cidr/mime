import { Writable, writable } from "svelte/store";

export const currentVideo: Writable<Object> = writable();
export const currentFrame: Writable<Number> = writable();
