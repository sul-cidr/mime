<!--
	@component
	Generates a vertical SVG line of unit length at the given X (frame) position.
 -->
 <script>
	import { getContext } from 'svelte';

  export let frameno = 0;

	const { data, xGet, yGet } = getContext('LayerCake');

  $: path = (frameno) => {
      return 'M' + $xGet({'frame': frameno}) + ',' + $yGet({'value': 0}) + ' v-' + $yGet({'value': 1});
  };
</script>

<path class='progress-line' d={path(frameno)}></path>

<style>
	.progress-line {
		stroke: rgb(246, 57, 57);
		stroke-linecap: square;
		stroke-width: 2;
	}
</style>