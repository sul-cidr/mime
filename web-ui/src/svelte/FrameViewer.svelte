<script lang="ts">
  import { ProgressBar, SlideToggle } from "@skeletonlabs/skeleton";

  import FrameDisplay from "@svelte/FrameDisplay.svelte";
  import FrameDetails from "@svelte/FrameDetails.svelte";

  import { API_BASE } from "@config";
  import { currentVideo, currentFrame } from "@svelte/stores";

  let poseData: Array<PoseData>;
  let showFrame: boolean = true;
  let playInterval: number | undefined;
  let hoveredPoseIdx: number | undefined;

  async function getPoseData(videoId: number, frame: number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  $: getPoseData($currentVideo.id, $currentFrame!).then(
    (data) => (poseData = data),
  );
</script>

<SlideToggle name="slider-label" bind:checked={showFrame} size="sm">
  Show Frame
</SlideToggle>
<div class="flex">
  <button
    type="button"
    class="btn variant-filled"
    on:click={() => ($currentFrame = ($currentFrame || 0) - 1)}>previous</button
  >
  <button
    type="button"
    class="btn variant-filled"
    on:click={() => ($currentFrame = ($currentFrame || 0) + 1)}>next</button
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
          $currentFrame = ($currentFrame || 0) + 10;
        }, 400);
      }
    }}>{playInterval ? "stop" : "play"}</button
  >
</div>
<div class="flex w-full gap-4">
  {#if poseData}
    <FrameDisplay {showFrame} poses={poseData} bind:hoveredPoseIdx />
    <FrameDetails poses={poseData} bind:hoveredPoseIdx />
  {:else}
    Loading pose data... <ProgressBar />
  {/if}
</div>
