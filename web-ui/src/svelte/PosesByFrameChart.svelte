<script lang="ts">
  import { LayerCake, Svg, Html, groupLonger, flatten } from "layercake";
  import { scaleOrdinal } from "d3-scale";

  import AxisX from "@layercake/AxisX.svelte";
  import AxisY from "@layercake/AxisY.svelte";
  import Brush from "@layercake/Brush.html.svelte";
  import Key from "@layercake/Key.html.svelte";
  import MultiLine from "@layercake/MultiLine.svelte";
  import ProgressLine from "@layercake/ProgressLine.svelte";
  import SharedTooltip from "@layercake/SharedTooltip.html.svelte";

  import { currentFrame, currentVideo, currentPose, currentMovelet, seriesNames, similarMoveletFrames, similarPoseFrames } from "@svelte/stores";

  export let data: Array<FrameRecord>;

  const seriesColors = ["#0fba81", "#4f46e5", "magenta", "#f9e07688", "white", "gray", "black", "#FFA50088", "brown",];
  const formatTickXAsTime = (d: number) => { return new Date(d / $currentVideo.fps * 1000).toISOString().slice(12,19).replace(/^0:/,"");
  }
  const formatTickX = (d: unknown) => d;
  const formatTickY = (d: unknown) => d;

  $seriesNames = Object.keys(data[0]!).filter((d) => d !== "frame");

  let hiddenSeries: Array<string> = [];

  let groupedData: Array<Object>;
  let xTicks: Array<number>;

  let brushExtents: Array<number | null> = [null, null];
  let groupedBrushedData: Array<Object>;

  let brushFaded = true;

  let maxValue:number = 0;

  // This is a pretty silly way to get a bar that always extends to the top
  // of the chart, but short of implementing multiple Y axes for the MultiLine
  // component, it may be the best option -- assuming we want to add such
  // maxed-out lines to the chart, which is debatable, although it's a fairly
  // effective way of indicating where similar poses occur on the timeline.
  const getMaxValue = (data:Array<FrameRecord>) => {
    let maxSoFar = 0;
    for (const item of data) {
      for (const [key, value] of Object.entries(item)) {
        if (!hiddenSeries.concat(['frame']).includes(key)) {
          if (value !== undefined && +value > maxSoFar) {
            maxSoFar = +value;
          }
        }
      }
    }
    return maxSoFar;
  }

  const fillEmptyFrames = (
    data: Array<FrameRecord>,
    similarPoseFrames: {[frameno: number]: number},
    similarMoveletFrames: {[frameno: number]: number},
    startFrame = 1,
    endFrame = $currentVideo.frame_count,
  ): Array<FrameRecord> => {
    // fill with zero values for unrepresented frames
    const framesInRange = data.filter(
      (frame: FrameRecord) =>
        frame.frame >= startFrame && frame.frame <= endFrame,
    ).sort((aFrame: FrameRecord, bFrame: FrameRecord) => aFrame.frame <= bFrame.frame ? -1 : 1);
    const timeSeries = [];
    let i = startFrame;
    framesInRange.forEach((frame: FrameRecord) => {
      while (i < frame.frame) {
        timeSeries.push({ frame: i, avgScore: 0, poseCt: 0, faceCt: 0, trackCt: 0, localShot: 0, globalShot: 0, isShot: 0, sim_pose: 0, sim_move: 0 });
        i++;
      }
      let frameWithSimilarMatches = frame;
      // XXX Using maxValue in this way leads to nonsensical "Similar:" values
      // in the tooltips for frames with matching poses. Either the tooltip
      // code should be customized to hide these, or we shouldn't use this
      // method at all for highlighting matching frames.
      frameWithSimilarMatches['sim_pose'] = (i in similarPoseFrames) ? maxValue : 0;
      frameWithSimilarMatches['sim_move'] = (i in similarMoveletFrames) ? maxValue : 0;
      timeSeries.push(frameWithSimilarMatches);
      i++;
    });
    while (i < endFrame) {
      timeSeries.push({ frame: i, avgScore: 0, poseCt: 0, faceCt: 0, trackCt: 0, localShot: 0, globalShot: 0, isShot: 0, sim_pose: 0, sim_move: 0 });
      i++;
    }
    return timeSeries;
  };

  const formatTitle = (d: string) => `Frame ${d}`;

  $: if ($currentPose) {
    if (Object.keys($similarPoseFrames).length && !$seriesNames.includes("sim_pose")) {
      $seriesNames.push("sim_pose");
    } else if (!Object.keys($similarPoseFrames).length && $seriesNames.includes("sim_pose")) {
      $seriesNames.splice($seriesNames.indexOf("sim_pose"), 1);
    }
  }

  $: if ($currentMovelet) {
    if (Object.keys($similarMoveletFrames).length && !$seriesNames.includes("sim_move")) {
      $seriesNames.push("sim_move");
    } else if (!Object.keys($similarMoveletFrames).length && $seriesNames.includes("sim_move")) {
      $seriesNames.splice($seriesNames.indexOf("sim_move", 1));
    }
  }

  $: {
    if (maxValue != 0) {
      groupedData = groupLonger(fillEmptyFrames(data, $similarPoseFrames, $similarMoveletFrames), $seriesNames, {
        groupTo: "series",
        valueTo: "value",
      });
      xTicks = Array.from(
        { length: Math.ceil($currentVideo.frame_count / 10000) },
        (_, i) => i * 10000,
      );
    }
  }

  $: {
    if (maxValue != 0) {
      const startFrame = Math.max(
        1,
        Math.ceil($currentVideo.frame_count * (brushExtents[0] || 0)),
      );
      const endFrame = Math.min(
        $currentVideo.frame_count,
        Math.ceil($currentVideo.frame_count * (brushExtents[1] || 1)),
      );
      if (startFrame !== endFrame) {
        groupedBrushedData = groupLonger(
          fillEmptyFrames(data, $similarPoseFrames, $similarMoveletFrames, startFrame, endFrame),
          $seriesNames,
          {
            groupTo: "series",
            valueTo: "value",
          },
        );
      }
    }
    maxValue = getMaxValue(data);
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
      <ProgressLine frameno={$currentFrame || 0} yDomain={[0, maxValue]} />
    </Svg>

    <Html>
      <SharedTooltip {formatTitle} dataset={data} hiddenKeys={["sim_pose", "sim_move"]} />
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
      <ProgressLine frameno={$currentFrame || 0} />
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
