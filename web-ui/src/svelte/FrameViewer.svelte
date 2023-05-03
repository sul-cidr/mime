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

  const updatePoseData = (data: Array<PoseData>) => {
    poseData = data;
  };

  async function getPoseData(videoId: number, frame: number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  $: getPoseData($currentVideo.id, $currentFrame!).then((data) =>
    updatePoseData(data),
  );
</script>

<div>
  <header
    class="bg-surface-200-700-token p-4 flex justify-between items-center gap-4"
  >
    <div
      class="p-1 inline-flex border-token border-surface-400-500-token space-x-1 rounded-token"
    >
      <!-- class="radio-item flex-auto text-base text-center cursor-pointer px-4 py-1 rounded-token variant-filled" -->
      <button
        type="button"
        class="btn btn-sm variant-filled"
        on:click={() => ($currentFrame = ($currentFrame || 0) - 1)}
        >previous</button
      >
      <button
        type="button"
        class="btn btn-sm variant-filled"
        on:click={() => ($currentFrame = ($currentFrame || 0) + 1)}>next</button
      >
      <button
        type="button"
        class="btn btn-sm"
        class:variant-filled={!playInterval}
        class:variant-ghost-primary={playInterval}
        on:click={() => {
          if (playInterval) {
            clearInterval(playInterval);
            playInterval = undefined;
          } else {
            playInterval = setInterval(() => {
              $currentFrame = ($currentFrame || 0) + 5;
            }, 400);
          }
        }}>{playInterval ? "stop" : "play"}</button
      >
    </div>
    <SlideToggle name="slider-label" bind:checked={showFrame} size="sm">
      Show Frame
    </SlideToggle>
  </header>

  <div class="flex gap-4 p-4 bg-surface-100-800-token">
    {#if poseData}
      <FrameDisplay {showFrame} bind:poses={poseData} bind:hoveredPoseIdx />
      <FrameDetails bind:poses={poseData} bind:hoveredPoseIdx />
    {:else}
      Loading pose data... <ProgressBar />
    {/if}
  </div>
</div>
