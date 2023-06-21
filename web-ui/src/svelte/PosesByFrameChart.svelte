<script lang="ts">
  import { LayerCake, Svg, Html, groupLonger, flatten } from "layercake";
  import { scaleOrdinal } from "d3-scale";

  import AxisX from "@layercake/AxisX.svelte";
  import AxisY from "@layercake/AxisY.svelte";
  import Brush from "@layercake/Brush.html.svelte";
  import Key from "@layercake/Key.html.svelte";
  import MultiLine from "@layercake/MultiLine.svelte";
  import SharedTooltip from "@layercake/SharedTooltip.html.svelte";

  import { currentVideo } from "@svelte/stores";

  export let data: Array<FrameRecord>;

  const seriesColors = ["#0fba81", "#4f46e5", "magenta", "green", "orange"];
  const formatTickXAsTime = (d: number) => { return new Date(d / $currentVideo.fps * 1000).toISOString().slice(12,19).replace(/^0:/,"");
  }
  const formatTickX = (d: unknown) => d;
  const formatTickY = (d: unknown) => d;

  const seriesNames = Object.keys(data[0]!).filter((d) => d !== "frame");

  let hiddenSeries: Array<string> = [];

  let groupedData: Array<Object>;
  let xTicks: Array<number>;

  let brushExtents: Array<number | null> = [null, null];
  let groupedBrushedData: Array<Object>;

  let brushFaded = true;

  const fillEmptyFrames = (
    data: Array<FrameRecord>,
    startFrame = 1,
    endFrame = $currentVideo.frame_count,
  ): Array<FrameRecord> => {
    // fill with zero values for unrepresented frames
    const framesInRange = data.filter(
      (frame: FrameRecord) =>
        frame.frame >= startFrame && frame.frame <= endFrame,
    );
    const timeSeries = [];
    let i = startFrame;
    framesInRange.forEach((frame: FrameRecord) => {
      while (i < frame.frame) {
        timeSeries.push({ frame: i, avgScore: 0, poseCt: 0, trackCt: 0 });
        i++;
      }
      timeSeries.push(frame);
      i++;
    });
    while (i < endFrame) {
      timeSeries.push({ frame: i, avgScore: 0, poseCt: 0, trackCt: 0 });
      i++;
    }
    return timeSeries;
  };

  const formatTitle = (d: string) => `Frame ${d}`;

  $: {
    groupedData = groupLonger(fillEmptyFrames(data), seriesNames, {
      groupTo: "series",
      valueTo: "value",
    });
    xTicks = Array.from(
      { length: Math.ceil($currentVideo.frame_count / 10000) },
      (_, i) => i * 10000,
    );
  }

  $: {
    const startFrame = Math.max(
      1,
      Math.ceil($currentVideo.frame_count * (brushExtents[0] || 0)),
    );
    const endFrame = Math.min(
      $currentVideo.frame_count,
      Math.ceil($currentVideo.frame_count * (brushExtents[1] || 1)),
    );
    groupedBrushedData = groupLonger(
      fillEmptyFrames(data, startFrame, endFrame),
      seriesNames,
      {
        groupTo: "series",
        valueTo: "value",
      },
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
    flatData={flatten(groupedBrushedData, "values")}
    data={groupedBrushedData}
  >
    <Svg>
      <AxisX
        gridlines={false}
        ticks={xTicks}
        formatTick={formatTickXAsTime}
        snapTicks={true}
        tickMarks={true}
      />
      <AxisY ticks={5} formatTick={formatTickY} />
      <MultiLine {hiddenSeries} />
    </Svg>

    <Html>
      <SharedTooltip {formatTitle} dataset={data} />
      <Key align="end" bind:hiddenSeries />
    </Html>
  </LayerCake>
</div>

<!-- svelte-ignore a11y-mouse-events-have-key-events -->
<div
  class="brush-container variant-ringed-primary select-none pt-2"
  on:mouseover={() => (brushFaded = false)}
  on:mouseout={() => (brushFaded = true)}
>
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
    <Svg pointerEvents={false}>
      <AxisX
        gridlines={false}
        ticks={xTicks}
        formatTick={formatTickX}
        snapTicks={true}
        tickMarks={true}
      />
      <MultiLine faded={brushFaded} />
    </Svg>
    <Html>
      <Brush bind:min={brushExtents[0]} bind:max={brushExtents[1]} />
    </Html>
  </LayerCake>
</div>

<style>
  .chart-container {
    width: 100%;
    height: 450px;
  }

  .brush-container {
    width: 100%;
    height: 100px;
  }
</style>
