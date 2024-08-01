/**
 * Formats the given number of seconds into a string with the format "yyyy years, dd days, hh hours, mm minutes, ss seconds".
 *
 * @param {number} seconds - The number of seconds to format.
 * @return {string} The formatted string.
 */
export const formatSeconds = (seconds) => {
	return [
		[Math.floor(seconds / 31536000), 'y'],
		[Math.floor((seconds % 31536000) / 86400), 'd'],
		[Math.floor(((seconds % 31536000) % 86400) / 3600), 'h'],
		[Math.floor((((seconds % 31536000) % 86400) % 3600) / 60), 'm'],
		[Math.round((((seconds % 31536000) % 86400) % 3600) % 60), 's']
	]
		.map(([c, t]) => (c ? `${c}${t}` : ''))
		.join('');
};

/**
 * Clamps a number between a minimum and maximum value.
 *
 * @param {number} num - The number to clamp.
 * @param {number} min - The minimum value.
 * @param {number} max - The maximum value.
 * @return {number} The clamped number.
 */
export const clamp = (num, min, max) => (num < min ? min : num > max ? max : num);
