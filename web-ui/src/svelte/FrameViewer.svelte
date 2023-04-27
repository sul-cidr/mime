<script lang="ts">
  import { ProgressBar, SlideToggle } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas, Html } from "layercake";

  import Pose from "./Pose.svelte";

  import { API_BASE } from "@config";

  export let videoId: number;
  export let frameNumber: number;
  export let frameHeight: number;
  export let frameWidth: number;

  let poseData: Array<{ keypoints: Array<number> }>;
  let showFrame: boolean = false;
  let playInterval: number | undefined;

  async function getPoseData(videoId: number, frame: number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  $: getPoseData(videoId, frameNumber).then((data) => {
    poseData = data;
  });
</script>

<SlideToggle name="slider-label" bind:checked={showFrame} size="sm"
  >Show Frame</SlideToggle
>
<div class="flex">
  <button
    type="button"
    class="btn variant-filled"
    on:click={() => frameNumber--}>previous</button
  >
  <button
    type="button"
    class="btn variant-filled"
    on:click={() => frameNumber++}>next</button
  >
  <button
    type="button"
    class="btn variant-filled"
    on:click={() => {
      if (playInterval) {
        clearInterval(playInterval);
        playInterval = undefined;
      } else {
        playInterval = setInterval(() => {
          frameNumber += 24;
        }, 1000);
      }
    }}>{playInterval ? "stop" : "play"}</button
  >
</div>
<div>
  <div
    class="h-[480px] border border-solid border-black"
    style={`aspect-ratio: ${frameWidth}/${frameHeight}`}
  >
    {#if poseData}
      <LayerCake>
        {#if showFrame}
          <Html zIndex={0}>
            <img
              src={`${API_BASE}/frame/${videoId}/${frameNumber}/`}
              alt={`Frame ${frameNumber}`}
            />
          </Html>
        {/if}
        {#if poseData.length}
          {#each poseData as pose}
            <Canvas zIndex={1}>
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
