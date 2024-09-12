<script>
	/**
	 * @typedef {Object} OverlayProps
	 * @property {import('svelte').Snippet} [topLeft]
	 * @property {import('svelte').Snippet} [topRight]
	 * @property {import('svelte').Snippet} [bottomLeft]
	 * @property {string} [class]
	 */

	/** @type {OverlayProps} */
	let { topLeft, topRight, bottomLeft, ...props } = $props();
</script>

<div class="overlay">
	{#if topLeft}
		<div class="top-left">
			{@render topLeft()}
		</div>
	{/if}
	{#if topRight}
		<div class="top-right">
			{@render topRight()}
		</div>
	{/if}
	{#if bottomLeft}
		<div class="bottom-left">
			{@render bottomLeft()}
		</div>
	{/if}
</div>

<style>
	.overlay {
		color: white;
		height: 100%;
		left: 0;
		opacity: 0;
		pointer-events: none;
		position: absolute;
		top: 0;
		transition: opacity 0.3s;
		width: 100%;
		z-index: 100;

		& > div {
			background-color: rgba(0, 0, 0, 0.5);
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
			font-size: 1.3rem;
			padding: 10px;
			pointer-events: all;
			position: absolute;
		}

		.top-left {
			left: 0;
			top: 0;
		}

		.top-right {
			right: 0;
			top: 0;
		}

		.bottom-left {
			left: 0;
			bottom: 0;
		}

		& :global(button) {
			background: none;
			border: none;
			color: white;
			cursor: pointer;
			font-size: 12px;
			transform-origin: center;
			transition: scale 0.1s;
		}

		& :global(button:hover) {
			scale: 1.3;
		}
	}
</style>
