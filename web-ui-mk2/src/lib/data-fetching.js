import { get } from 'svelte/store';
import { page } from '$app/stores';

/**
 * Fetches pose data from the API for a given video and frame.
 *
 * @param {string} videoId - The ID of the video to fetch.
 * @param {number} frame - The frame number to fetch.
 * @return {Promise<PoseRecord[]>} A Promise that resolves to the pose data.
 */
export const getPoseData = async (videoId, frame) => {
	const response = await fetch(`${get(page).data.apiBase}/poses/${videoId}/${frame}/`);
	return await response.json();
};
