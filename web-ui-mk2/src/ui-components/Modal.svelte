<script>
	/**
	 * @typedef {Object} ModalProps
	 * @property {boolean} showModal
	 * @property {import('svelte').Snippet} [header]
	 * @property {import('svelte').Snippet} body
	 * @property {string} [class]
	 */

	/** @type {ModalProps} */
	let { showModal = $bindable(false), header, body, ...props } = $props();

	let /** @type {HTMLDialogElement} */ dialog;

	export const show = () => {
		dialog.showModal();
	};

	export const close = () => {
		dialog.close();
	};

	$effect(() => {
		if (dialog && showModal) show();
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog bind:this={dialog} onclose={() => (showModal = false)} {...props}>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	{#if header}
		{@render header()}
		<hr />
	{/if}
	{@render body()}
	<hr />
	<button onclick={() => dialog.close()}>close modal</button>
</dialog>

<style>
	dialog {
		max-width: 32em;
		border-radius: 0.2em;
		border: none;
		padding: 0;
	}

	dialog::backdrop {
		background: rgba(0, 0, 0, 0.3);
	}

	dialog[open] {
		animation: zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	@keyframes zoom {
		from {
			transform: scale(0.95);
		}
		to {
			transform: scale(1);
		}
	}

	dialog[open]::backdrop {
		animation: fade 0.2s ease-out;
	}

	@keyframes fade {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	button {
		display: block;
	}
</style>
