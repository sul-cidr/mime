/**
 * Retrieves the value associated with the given key from the local storage.
 * If the key does not exist in the local storage, the default value is returned.
 *
 * @param {string} key - The key to retrieve the value for.
 * @param {any} [defaultValue=null] - The default value to return if the key does not exist in the local storage.
 * @return {any} The value associated with the given key, or the default value if the key does not exist.
 */
export const getLocalStorage = (key, defaultValue = null) => {
	return JSON.parse(localStorage.getItem(key) || JSON.stringify(defaultValue));
};

/**
 * Stores the given value in the local storage, associated with the given key.
 * If the key already exists, it will be overwritten.
 *
 * @param {string} key - The key to store the value for.
 * @param {any} value - The value to store in the local storage.
 * @return {void} This function does not return anything.
 */
export const setLocalStorage = (key, value) => {
	localStorage.setItem(key, JSON.stringify(value));
};
