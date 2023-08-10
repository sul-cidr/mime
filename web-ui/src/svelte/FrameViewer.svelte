<script lang="ts">
  import { ProgressBar, SlideToggle } from "@skeletonlabs/skeleton";

  import FrameDisplay from "@svelte/FrameDisplay.svelte";
  import FrameDetails from "@svelte/FrameDetails.svelte";

  import { API_BASE } from "@config";
  import { currentVideo, currentFrame } from "@svelte/stores";

  let poseData: Array<PoseRecord>;
  let trackCt: number | 0;
  let showFrame: boolean = true;
  let playInterval: number | undefined;
  let hoveredPoseIdx: number | undefined;

  const updatePoseData = (data: Array<PoseRecord>) => {
    if (data) {
      poseData = data;
      let trackCount = 0;
      if (data.length) {
        data.forEach((pr: PoseRecord) => {
          if (pr.track_id != 0)
            trackCount += 1;
        })
      }
      trackCt = trackCount;
    }
    getFaceData($currentVideo.id, $currentFrame!).then((data) =>
      integrateFaceData(data),
    );
  };

  const integrateFaceData = (data: Array<FaceRecord>) => {
    if (data && poseData) {
      if (data.length && poseData.length) {
        data.forEach((fr: FaceRecord) => {
          poseData.forEach((pr: PoseRecord, pi: number) => {
            if (fr.pose_idx == pr.pose_idx) {
              poseData[pi]!.face_bbox = fr.bbox;
              poseData[pi]!.face_landmarks = fr.landmarks;
            }
          })
        })
      }
    }
  }

  async function getPoseData(videoId: string, frame: number) {
    if (!frame) {
      return null;
    }
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  async function getFaceData(videoId: string, frame: number) {
    if (!frame) {
      return null;
    }
    const response = await fetch(`${API_BASE}/faces/${videoId}/${frame}/`);
    return await response.json();
  }

  $: getPoseData($currentVideo.id, $currentFrame!).then((data) =>
    updatePoseData(data),
  );
  // $: getFaceData($currentVideo.id, $currentFrame!).then((data) =>
  //   integrateFaceData(data),
  // );
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
    <div>
      <label class="label flex items-center gap-4">
        <span>Frame</span>
        <input
          class="input pl-2 text-right w-28 m-0"
          type="number"
          placeholder="Frame #"
          bind:value={$currentFrame}
        />
      </label>
    </div>
    <SlideToggle name="slider-label" bind:checked={showFrame} size="sm">
      Show Frame
    </SlideToggle>
  </header>

  <div class="flex gap-4 p-4 bg-surface-100-800-token">
    {#if poseData}
      <FrameDisplay {showFrame} bind:poses={poseData} bind:hoveredPoseIdx />
      <FrameDetails bind:poses={poseData} bind:trackCt={trackCt} bind:hoveredPoseIdx />
    {:else}
      Loading pose data... <ProgressBar />
    {/if}
  </div>
</div>
