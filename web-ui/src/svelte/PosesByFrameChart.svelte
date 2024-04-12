<svelte:options immutable={true} />

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

  import {
    currentFrame,
    currentVideo,
    currentPose,
    currentActionPose,
    seriesNames,
    similarActionFrames,
    similarPoseFrames,
  } from "@svelte/stores";

  export let timelineData: Array<FrameRecord>;

  const seriesColors = [
    "#0fba81", // green-blue
    "#4f46e5", // blue
    "lime",
    "#ff00ff88", // magenta
    "black",
    "gray",
    "orange",
    "#964B00BB", // brown
    "#fA8072BB", // salmon
    "fbceb1", // apricot
  ];
  const formatTickXAsTime = (d: number) => {
    return new Date((d / $currentVideo.fps) * 1000)
      .toISOString()
      .slice(12, 19)
      .replace(/^0:/, "");
  };
  const formatTickX = (d: unknown) => d;
  const formatTickY = (d: unknown) => d;

  $seriesNames = Object.keys(timelineData[0]!).filter(
    (d) => !["frame", "time"].includes(d),
  );

  let hiddenSeries: Array<string> = ["avgScore"];

  let groupedData: Array<any>;
  let xTicks: Array<number>;

  let brushMin: number;
  let brushMax: number;
  let groupedBrushedData: Array<any>;

  let brushFaded = true;

  let maxValue: number = 0;

  let framesArray: Array<any>;

  /* Series whose values are always normalized between 0 and 1 in the DB (e.g.,
   * movement and avg pose confidence score) can be scaled to between 0 and the
   * maximum of the integer-valued entries on the timeline (usually just pose
   * count, face count or track count).
   * XXX BUT if the module hot-reloads, the scaling is run twice due to Svelte
   * weirdness, and the values are artificially inflated (though still clamped
   * to the max integer value from the DB). Hopefully this won't happen on the
   * deployed production version.
   */
  const seriesToFit = ["movement", "avgScore", "interest"]; // always normalize between 0 and maxValue
  let normalizedSeriesAlreadyScaled = false;

  const scaleToFit = (thisValue: number) =>
    Math.min(maxValue, thisValue * maxValue);

  // This is a pretty silly way to get a bar that always extends to the top
  // of the chart, but short of implementing multiple Y axes for the MultiLine
  // component, it may be the best option -- assuming we want to add such
  // maxed-out lines to the chart, which is debatable, although it's a fairly
  // effective way of indicating where similar poses occur on the timeline.
  const getMaxValue = (timelineData: Array<FrameRecord>) => {
    let maxSoFar = 0;
    for (const item of timelineData) {
      for (const [key, value] of Object.entries(item)) {
        if (
          !hiddenSeries.concat(["frame"]).includes(key) &&
          !seriesToFit.includes(key)
        ) {
          if (value !== undefined && +value > maxSoFar) {
            maxSoFar = +value;
          }
        }
      }
    }
    return maxSoFar;
  };

  const fillEmptyFrames = (
    data: Array<FrameRecord>,
    similarPoseFrames: { [frameno: number]: number },
    similarActionFrames: { [frameno: number]: number },
    startFrame = 1,
    endFrame = $currentVideo.frame_count,
  ) => {
    // fill with zero values for unrepresented frames
    const framesInRange = data
      .filter(
        (frame: FrameRecord) =>
          frame.frame >= startFrame && frame.frame <= endFrame,
      )
      .sort((aFrame: FrameRecord, bFrame: FrameRecord) =>
        aFrame.frame <= bFrame.frame ? -1 : 1,
      );
    const timeSeries = [];
    let i = startFrame;
    framesInRange.forEach((frame: Record<string, any>) => {
      while (i < frame.frame) {
        timeSeries.push({
          frame: i,
          avgScore: 0,
          poseCt: 0,
          faceCt: 0,
          trackCt: 0,
          isShot: 0,
          movement: 0,
          interest: 0,
          sim_pose: 0,
          sim_action: 0,
        });
        i++;
      }
      let thisFrame: Record<string, any> = frame;
      // XXX Using maxValue in this way leads to nonsensical "Similar:" values
      // in the tooltips for frames with matching poses. Either the tooltip
      // code should be customized to hide these, or we shouldn't use this
      // method at all for highlighting matching frames.
      thisFrame["sim_pose"] = i in similarPoseFrames ? maxValue : 0;
      thisFrame["sim_action"] = i in similarActionFrames ? maxValue : 0;
      if (!normalizedSeriesAlreadyScaled) {
        seriesToFit.forEach((series) => {
          thisFrame[series] = scaleToFit(frame[series]);
        });
      }
      timeSeries.push(thisFrame);
      i++;
    });
    while (i < endFrame) {
      timeSeries.push({
        frame: i,
        avgScore: 0,
        poseCt: 0,
        faceCt: 0,
        trackCt: 0,
        isShot: 0,
        movement: 0,
        interest: 0,
        sim_pose: 0,
        sim_action: 0,
      });
      i++;
    }
    normalizedSeriesAlreadyScaled = true;
    return timeSeries;
  };

  const formatTitle = (d: string) => `Frame ${d}`;

  $: if ($currentPose) {
    if (
      Object.keys($similarPoseFrames).length &&
      !$seriesNames.includes("sim_pose")
    ) {
      $seriesNames.push("sim_pose");
    } else if (
      !Object.keys($similarPoseFrames).length &&
      $seriesNames.includes("sim_pose")
    ) {
      $seriesNames.splice($seriesNames.indexOf("sim_pose"), 1);
    }
  }

  $: if ($currentActionPose) {
    if (
      Object.keys($similarActionFrames).length &&
      !$seriesNames.includes("sim_action")
    ) {
      $seriesNames.push("sim_action");
    } else if (
      !Object.keys($similarActionFrames).length &&
      $seriesNames.includes("sim_action")
    ) {
      $seriesNames.splice($seriesNames.indexOf("sim_action", 1));
    }
  }

  $: maxValue = getMaxValue(timelineData);

  $: framesArray = fillEmptyFrames(
    timelineData,
    $similarPoseFrames,
    $similarActionFrames,
  );

  $: {
    groupedData = groupLonger(framesArray, $seriesNames, {
      groupTo: "series",
      valueTo: "value",
    });
    xTicks = Array.from(
      { length: Math.ceil($currentVideo.frame_count / 10000) },
      (_, i) => i * 10000,
    );
  }

  $: {
    const startFrame = Math.ceil($currentVideo.frame_count * (brushMin || 0));
    const endFrame = Math.ceil($currentVideo.frame_count * (brushMax || 1));
    if (startFrame !== endFrame) {
      groupedBrushedData = groupedData.map((o) => ({
        ...o,
        values: o.values.slice(startFrame, endFrame),
      }));
    }
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
      <SharedTooltip
        {formatTitle}
        dataset={timelineData}
        hiddenKeys={[
          "sim_pose",
          "sim_action",
          "isShot",
          "avgScore",
          "movement",
          "interest",
        ]}
      />
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
      <Brush bind:min={brushMin} bind:max={brushMax} />
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
