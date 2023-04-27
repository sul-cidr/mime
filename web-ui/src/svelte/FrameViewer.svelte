<script lang="ts">
  import { ProgressBar, dataTableHandler } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas } from "layercake";

  import Pose from "./Pose.svelte";

  import { API_BASE } from "@config";

  export let videoId: Number;
  export let frameNumber: Number;
  export let frameHeight: Number;
  export let frameWidth: Number;

  let poseData;

  async function getPoseData(videoId: Number, frame: Number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  $: getPoseData(videoId, frameNumber).then((data) => {
    poseData = data;
  });
</script>

<div>
  <div
    class="h-[480px] border border-solid border-black"
    style={`aspect-ratio: ${frameWidth}/${frameHeight}`}
  >
    {#if poseData}
      <LayerCake>
        {#if poseData.length}
          {#each poseData as pose}
            <Canvas zIndex={3}>
              <Pose poseData={pose.keypoints} />
            </Canvas>
          {/each}
        {:else}
          <p>No poses found</p>
        {/if}
      </LayerCake>
    {:else}
      Loading pose data... <ProgressBar />
    {/if}
  </div>
</div>

<style>
</style>
