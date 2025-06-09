<script>
	import { getContext } from 'svelte';
	import { scaleCanvas } from 'layercake';

	/**
	 * @returns {void}
	 */

	const { width, height } = getContext('LayerCake');
	const { ctx } = getContext('canvas');

	$effect(() => {
		if ($ctx) {
			// "Scale your canvas size to retina screens."
			// (see https://layercake.graphics/guide#scalecanvas)
			scaleCanvas($ctx, $width, $height);
			$ctx.clearRect(0, 0, $width, $height);
		}
	});
</script>
