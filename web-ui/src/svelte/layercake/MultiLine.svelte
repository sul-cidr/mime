<!--
  @component
  Generates an SVG multi-series line chart. It expects your data to be an array of objects, each with a `values` key that is an array of data objects.
  Adapted from https://layercake.graphics/examples/MultiLine
-->
<script>
  import { getContext } from "svelte";

  export let hiddenSeries = [];
  export let faded = false;

  const { data, xGet, yGet, zGet } = getContext("LayerCake");

  $: path = (values) => {
    return "M" + values.map((d) => $xGet(d) + "," + $yGet(d)).join("L");
  };
</script>

<g class="line-group transition-opacity" class:opacity-50={faded}>
  {#each $data as group}
    {#if !hiddenSeries.includes(group.series)}
      <path class="path-line" d={path(group.values)} stroke={$zGet(group)} />
    {/if}
  {/each}
</g>

<style>
  .path-line {
    fill: none;
    stroke-linejoin: round;
    stroke-linecap: round;
    stroke-width: 1px;
  }
</style>
