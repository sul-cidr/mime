import { Writable, writable } from "svelte/store";

export const videoId: Writable<Number> = writable();
export const videoTitle: Writable<String> = writable();
