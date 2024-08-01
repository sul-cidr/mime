export const getLocalStorage = (key, defaultValue = null) => {
	return JSON.parse(localStorage.getItem(key) || JSON.stringify(defaultValue));
};

export const setLocalStorage = (key, value) => {
	localStorage.setItem(key, JSON.stringify(value));
};
