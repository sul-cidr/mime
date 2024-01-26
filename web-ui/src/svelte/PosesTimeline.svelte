<script lang="ts">
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import { LayerCake, Svg, Html } from "layercake";
  import { API_BASE } from "@config";
  import { formatSeconds } from "@utils";

  import AxisX from "@layercake/AxisX.svelte";
  import AxisY from "@layercake/AxisY.svelte";
  import ProgressLine from "@layercake/ProgressLine.svelte";
  import ScatterSvg from "@layercake/ScatterSvg.svelte";
  import PoseTooltip from "@layercake/PoseTooltip.html.svelte";
  import { currentFrame, currentVideo } from "@svelte/stores";

  export let videoId: string;
  export let videoName: string;

  let posesData: Array<MoveletRecord> | undefined;
  let shotsData: Array<ShotRecord> | undefined;

  let maxCluster: number = 0;

  const xKey = "start_frame"; // Should cover the full set of frames eventually...
  const yKey = "cluster_id";

  const dotRadius = 4;
  const plotPadding = 2;

  const formatTickXAsTime = (d: number) => {
    return new Date((d / $currentVideo.fps) * 1000)
      .toISOString()
      .slice(12, 19)
      .replace(/^0:/, "");
  };
  let xTicks: Array<number>;
  let yTicks: Array<number>;

  // Unsuccessful attempt to display each cluster's "ambassador" pose image as
  // a y-axis tick to the left of the plot.
  const formatPoseTick = (d: number) => {
    const poseImage = new Image();
    poseImage.src = `${API_BASE}/pose_cluster_image/${videoName}/${d}`;
    poseImage.classList.add("ambassador-pose");
    return poseImage;
  };

  const updatePosesData = (data: Array<MoveletRecord>) => {
    if (data) {
      posesData = data;
      posesData.forEach((pose) => {
        maxCluster = Math.max(maxCluster, pose["cluster_id"]);
        pose[xKey] = +pose[xKey];
        pose[yKey] = +pose[yKey];
        pose.pose_idx = pose.pose_idx += 1;
        pose.time = formatSeconds(
          (pose.start_frame + pose.end_frame) / 2 / $currentVideo.fps,
        );
      });
      yTicks = [...Array(maxCluster + 1).keys()];
    }
  };

  const updateShotsData = (data: Array<ShotRecord>) => {
    if (data) {
      shotsData = data;
    }
  };

  const formatTitle = (d: string) => `Frame ${d}`;

  async function getClusteredPosesData(videoId: string) {
    const response = await fetch(`${API_BASE}/clustered_poses/${videoId}/`);
    return await response.json();
  }

  async function getShotBoundaries(videoId: string) {
    const response = await fetch(`${API_BASE}/shots/${videoId}/`);
    return await response.json();
  }

  $: {
    posesData = undefined;
    getClusteredPosesData(videoId).then((data) => updatePosesData(data));
  }

  $: {
    shotsData = undefined;
    getShotBoundaries(videoId).then((data) => updateShotsData(data));
  }

  $: {
    xTicks = Array.from(
      { length: Math.ceil($currentVideo.frame_count / 10000) },
      (_, i) => i * 10000,
    );
  }
</script>

{#if posesData}
  <div class="chart-container">
    <LayerCake
      padding={{ top: 0, right: 15, bottom: 20, left: 75 }}
      x={xKey}
      y={yKey}
      xDomain={[0, $currentVideo.frame_count]}
      yDomain={[0, maxCluster]}
      xPadding={[plotPadding, plotPadding]}
      data={posesData}
    >
      <Svg>
        <AxisX
          gridlines={false}
          ticks={xTicks}
          formatTick={formatTickXAsTime}
          snapTicks={true}
          tickMarks={true}
        />
        <AxisY ticks={yTicks} />
        {#if shotsData}
          {#each shotsData as shot}
            <ProgressLine
              frameno={shot.frame}
              xKey="start_frame"
              yKey="cluster_id"
              yDomain={[0, maxCluster]}
              lineType="shot-line"
            />
          {/each}
        {/if}
        <ScatterSvg r={dotRadius} fill={"rgba(0, 0, 204, 0.75)"} />
        <ProgressLine
          frameno={$currentFrame || 0}
          xKey="start_frame"
          yKey="cluster_id"
          yDomain={[0, maxCluster]}
        />
      </Svg>
      <Html>
        <PoseTooltip
          {formatTitle}
          dataset={posesData}
          searchRadius={"10"}
          highlightKey={"cluster_id"}
        />
      </Html>
    </LayerCake>
  </div>
  <div>
    <ul>
      {#each Array(maxCluster + 1) as _, index (index)}
        <li class="ambassador-box">
          cluster {index}
          <img
            src={`${API_BASE}/pose_cluster_image/${videoName}/${index}/`}
            class="ambassador-pose-image"
          />
        </li>
      {/each}
    </ul>
  </div>
{:else}
  Loading poses data... <ProgressBar />
{/if}

<style>
  .chart-container {
    width: 100%;
    height: 450px;
    padding-top: 20px;
    padding-left: 10px;
    padding-right: 10px;
  }
  .ambassador-box {
    display: inline-block;
    list-style-position: inside;
    border: 1px solid black;
    margin: 0.75em;
    padding: 5px;
  }
  .ambassador-pose-image {
    width: 100px;
  }
</style>
