import { get } from 'svelte/store';
import { page } from '$app/stores';

/**
 * Fetches video data from the API.
 *
 * @return {Promise<VideoRecord[]>} A Promise that resolves to the video data.
 */
export const getVideoData = async () => {
	const response = await fetch(`${get(page).data.apiBase}/videos/`);
	return await response.json().then((data) => data.videos);
};

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
