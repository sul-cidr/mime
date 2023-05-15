<!--
  @component
  Generates an SVG multi-series line chart. It expects your data to be an array of objects, each with a `values` key that is an array of data objects.
  Adapted from https://layercake.graphics/examples/MultiLine
-->
<script>
  import { getContext } from "svelte";
  import { currentVideo } from "@svelte/stores";

  export let hiddenSeries = [];

  const { data, xGet, yGet, zGet } = getContext("LayerCake");

  $: path = (values) => {
    // fill with zero values for unrepresented frames, so that the series lines
    //  actually go down to zero on the y axis where appropriate.
    const out = [];
    let i = 1;
    values.forEach((d) => {
      while (i < d.frame) {
        out.push($xGet({ frame: i }) + "," + $yGet({ value: 0 }));
        i++;
      }
      out.push($xGet(d) + "," + $yGet(d));
      i++;
    });
    while (i < $currentVideo.frame_count) {
      out.push($xGet({ frame: i }) + "," + $yGet({ value: 0 }));
      i++;
    }
    return "M" + out.join("L");
    // return "M" + values.map((d) => $xGet(d) + "," + $yGet(d)).join("L");
  };
</script>

<g class="line-group">
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
