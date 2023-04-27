<script lang="ts">
  import { LayerCake, Canvas, Html, Svg } from "layercake";
  import Pose from "./Pose.svelte";

  import { API_BASE } from "@config";
  import { currentVideo, currentFrame } from "@svelte/stores";

  const { id: videoId, width: frameWidth, height: frameHeight } = $currentVideo;

  export let showFrame: boolean;
  export let poses: Array<{ keypoints: Array<number>; bbox: Array<number> }>;
</script>

<div>
  <div class="h-[480px]" style={`aspect-ratio: ${frameWidth}/${frameHeight}`}>
    <LayerCake>
      {#if showFrame}
        <Html zIndex={0}>
          <img
            src={`${API_BASE}/frame/${videoId}/${$currentFrame}/`}
            alt={`Frame ${$currentFrame}`}
          />
        </Html>
      {/if}
      {#if poses.length}
        {#each poses as poseData}
          <Canvas zIndex={1}>
            <Pose {poseData} />
          </Canvas>
        {/each}
        <Svg zIndex={2}>
          {#each poses as poseData, i}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-mouse-events-have-key-events -->
            <rect
              data-id={i}
              x={poseData.bbox[0]}
              y={poseData.bbox[1]}
              height={poseData.bbox[3]}
              width={poseData.bbox[2]}
              stroke="white"
              fill="none"
              stroke-width="1"
              on:click={() => console.log(`bbox ${i}`)}
              on:mouseover={(e) => (e.target.style.stroke = "red")}
              on:mouseout={(e) => (e.target.style.stroke = "white")}
              pointer-events="visible"
              style="cursor: pointer"
            />
          {/each}
        </Svg>
      {:else}
        <p>No poses found</p>
      {/if}
    </LayerCake>
  </div>
</div>
