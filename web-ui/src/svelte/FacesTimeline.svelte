<script lang="ts">
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import { LayerCake, Svg, Html } from "layercake";
  import { API_BASE } from "@config";
  import { formatSeconds } from "@utils";

  import AxisX from "@layercake/AxisX.svelte";
  import AxisY from "@layercake/AxisY.svelte";
  import ProgressLine from "@layercake/ProgressLine.svelte";
  import ScatterSvg from "@layercake/ScatterSvg.svelte";
  import FaceTooltip from "@layercake/FaceTooltip.html.svelte";
  import { currentFrame, currentVideo } from "@svelte/stores";

  export let videoId: string;
  export let videoName: string;

  let facesData: Array<FaceRecord> | undefined;
  let shotsData: Array<ShotRecord> | undefined;

  let maxCluster: number = 0;

  const xKey = "frame";
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

  const updateFacesData = (data: Array<FaceRecord>) => {
    if (data) {
      facesData = data;
      facesData.forEach((face) => {
        maxCluster = Math.max(maxCluster, face["cluster_id"]);
        face.pose_idx = face.pose_idx += 1;
        face.time = formatSeconds(face.frame / $currentVideo.fps);
        face[xKey] = +face[xKey];
        face[yKey] = +face[yKey];
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

  async function getClusteredFacesData(videoId: string) {
    const response = await fetch(`${API_BASE}/clustered_faces/${videoId}/`);
    return await response.json();
  }

  async function getShotBoundaries(videoId: string) {
    const response = await fetch(`${API_BASE}/shots/${videoId}/`);
    return await response.json();
  }

  $: {
    facesData = undefined;
    getClusteredFacesData(videoId).then((data) => updateFacesData(data));
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

{#if facesData}
  <div class="chart-container">
    <LayerCake
      padding={{ top: 0, right: 15, bottom: 20, left: 75 }}
      x={xKey}
      y={yKey}
      xDomain={[0, $currentVideo.frame_count]}
      yDomain={[0, maxCluster]}
      xPadding={[plotPadding, plotPadding]}
      data={facesData}
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
              yKey="cluster_id"
              yDomain={[0, maxCluster]}
              lineType="shot-line"
            />
          {/each}
        {/if}
        <ScatterSvg r={dotRadius} fill={"rgba(0, 0, 204, 0.75)"} />
        <ProgressLine
          frameno={$currentFrame || 0}
          yKey="cluster_id"
          yDomain={[0, maxCluster]}
        />
      </Svg>
      <Html>
        <FaceTooltip
          {formatTitle}
          dataset={facesData}
          searchRadius={"10"}
          highlightKey={"cluster_id"}
          hiddenKeys={["bbox"]}
        />
      </Html>
    </LayerCake>
  </div>
  <h3>Face cluster averages</h3>
  <div>
    <ul>
      {#each Array(maxCluster + 1) as _, index (index)}
        <li class="ambassador-box">
          cluster {index}
          <img
            alt={`Representative blended face image for cluster ${index}`}
            src={`${API_BASE}/face_cluster_image/${videoName}/${index}/`}
            class="ambassador-image"
          />
        </li>
      {/each}
    </ul>
  </div>
{:else}
  Loading faces data... <ProgressBar />
{/if}

<style>
  .chart-container {
    width: 100%;
    height: 450px;
    margin-top: 50px;
    padding-top: 10px;
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
  .ambassador-image {
    width: 100px;
  }
</style>
