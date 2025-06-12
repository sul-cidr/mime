import { onMount } from 'svelte';

/**
 * Creates a Svelte store that is persisted to the local storage.
 *
 * @param {string} key - The key to store the value under in the local storage.
 * @param {any} initialValue - The initial value of the store.
 * @return {{value: any}} A store with a single `value` property.
 */
export const localStorageState = (key, initialValue) => {
	let value = $state(initialValue);

	onMount(() => {
		const currentValue = localStorage.getItem(key);
		if (currentValue) value = JSON.parse(currentValue);
	});

	const save = () => {
		if (value) {
			localStorage.setItem(key, JSON.stringify(value));
		} else {
			localStorage.removeItem(key);
		}
	};

	return {
		get value() {
			return value;
		},
		set value(v) {
			value = v;
			save();
		}
	};
};

export default localStorageState;
