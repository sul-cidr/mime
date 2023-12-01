<!--
	@component
	Generates a vertical SVG line of unit length at the given X (frame) position.
 -->
<script>
  import { getContext } from 'svelte';

  export let frameno = 0;

  export let xKey = "frame";
  export let yKey = "value";
  export let yDomain = [0, 1];
  export let lineType = "progress-line";

  const { data, xGet, yGet } = getContext('LayerCake');

  $: path = (frameno) => {
    return 'M' + $xGet({[xKey]: frameno}) + ',' + $yGet({[yKey]: yDomain[0]}) + ' v-' + ($yGet({[yKey]: yDomain[0]}) - $yGet({[yKey]: yDomain[1]}));
  };
</script>

<path class={lineType} d={path(frameno)}></path>

<style>
	.progress-line {
		stroke: rgb(246, 57, 57);
		stroke-linecap: square;
		stroke-width: 2;
	}
	.shot-line {
		stroke: rgb(200, 200, 200);
		stroke-linecap: square;
		stroke-width: 1;
	}
</style>