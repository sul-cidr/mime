<script lang="ts">
  import { LayerCake, Canvas, Html, Svg } from "layercake";
  import Pose from "./Pose.svelte";

  import { API_BASE } from "@config";
  import { currentVideo, currentFrame } from "@svelte/stores";

  const { id: videoId, width: frameWidth, height: frameHeight } = $currentVideo;

  export let showFrame: boolean;
  export let poses: Array<PoseRecord>;
  export let hoveredPoseIdx: number | undefined;
  export let displayWidthPx = 640;

  const scaleFactor = displayWidthPx / frameWidth;
</script>

<div>
  <div
    class="box-content border border-solid border-black frame-display"
    style={`width:${displayWidthPx}px;aspect-ratio:${frameWidth}/${frameHeight}`}
  >
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
          {#if !poseData.hidden}
            <Canvas zIndex={1}>
              <Pose poseData={poseData.keypoints} {scaleFactor} />
            </Canvas>
          {/if}
        {/each}
        <Svg viewBox={`0 0 ${frameWidth} ${frameHeight}`} zIndex={2}>
          <defs>
            <filter x="0" y="0" width="1" height="1" id="solid">
              <feFlood flood-color="white" result="bg" />
              <feMerge>
                <feMergeNode in="bg" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          {#each poses as poseData, i}
            {#if !poseData.hidden}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-mouse-events-have-key-events -->
              <rect
                data-id={i}
                x={poseData.bbox[0]}
                y={poseData.bbox[1]}
                height={poseData.bbox[3]}
                width={poseData.bbox[2]}
                stroke={poseData.track_id ? "magenta" : "white"}
                fill="none"
                stroke-width="1"
                class:selected={hoveredPoseIdx === i}
                on:click={() => console.log(`bbox ${i}`)}
                on:mouseover={() => (hoveredPoseIdx = i)}
                on:mouseout={() => (hoveredPoseIdx = undefined)}
                pointer-events="visible"
                style="cursor: pointer"
              />
              <text
                dominant-baseline="hanging"
                x={poseData.bbox[0] + 2}
                y={poseData.bbox[1] + 5}
                stroke="white"
                fill="white"
              >
                {#if poseData.track_id != 0}
                  {poseData.track_id}
                {:else}
                  {i + 1}
                {/if}
              </text>
            {/if}
          {/each}
        </Svg>
      {:else}
        <p>No poses found</p>
      {/if}
    </LayerCake>
  </div>
</div>

<style>
  :global(rect.selected) {
    stroke: red;
    fill: white;
    fill-opacity: 0.25;
  }

  :global(rect.selected + text) {
    stroke: red;
    fill: red;
    filter: url(#solid);
  }

  .frame-display {
    background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
    box-shadow: inset 0px 0px 30px 0px #666;
  }
</style>
