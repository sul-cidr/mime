<script lang="ts">
  import { LayerCake, Svg, Html, groupLonger, flatten } from "layercake";
  import { scaleOrdinal } from "d3-scale";

  import AxisX from "@layercake/AxisX.svelte";
  import AxisY from "@layercake/AxisY.svelte";
  import Labels from "@layercake/GroupLabels.html.svelte";
  import MultiLine from "@layercake/MultiLine.svelte";
  import SharedTooltip from "@layercake/SharedTooltip.html.svelte";

  export let data;

  const seriesColors = ["#0fba81", "#4f46e5", "green", "orange"];
  const formatTickX = (d: unknown) => d;
  const formatTickY = (d: unknown) => d;

  const seriesNames = Object.keys(data[0]).filter((d) => d !== "frame");

  let groupedData;
  let xTicks;

  $: {
    groupedData = groupLonger(data, seriesNames, {
      groupTo: "series",
      valueTo: "value",
    });
    xTicks = Array.from(
      { length: Math.ceil(data.at(-1).frame / 10000) },
      (_, i) => i * 10000,
    );
  }
</script>

<div class="chart-container">
  <LayerCake
    padding={{ top: 7, right: 10, bottom: 20, left: 25 }}
    x={"frame"}
    y={"value"}
    z={"series"}
    yDomain={[0, null]}
    zScale={scaleOrdinal()}
    zRange={seriesColors}
    flatData={flatten(groupedData, "values")}
    data={groupedData}
  >
    <Svg>
      <AxisX
        gridlines={false}
        ticks={xTicks}
        formatTick={formatTickX}
        snapTicks={true}
        tickMarks={true}
      />
      <AxisY ticks={5} formatTick={formatTickY} />
      <MultiLine />
    </Svg>

    <Html>
      <Labels />
      <SharedTooltip formatTitle={(d) => `Frame ${d}`} dataset={data} />
    </Html>
  </LayerCake>
</div>

<style>
  .chart-container {
    width: 100%;
    height: 450px;
  }
</style>
