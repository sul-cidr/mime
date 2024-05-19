<script lang="ts">
  import { ProgressBar, SlideToggle } from "@skeletonlabs/skeleton";
  import { Canvas as Canvas3D } from "@threlte/core";

  import Scene3D from "@svelte/Scene3D.svelte";
  import FrameDisplay from "@svelte/FrameDisplay.svelte";
  import FrameDetails from "@svelte/FrameDetails.svelte";

  import { API_BASE } from "@config";
  import { currentVideo, currentFrame } from "@svelte/stores";

  let poseData: Array<PoseRecord>;
  let trackCt: number;
  let faceCt: number;
  let showFrame: boolean = true;
  let playInterval: number | undefined;
  let hoveredPoseIdx: number | undefined;
  let shot: number | 0;
  let pose_interest: number | 0;
  let action_interest: number | 0;
  let show3Dframe: boolean = false;

  const updatePoseData = (data: Array<PoseRecord>) => {
    if (data) {
      poseData = data;
      let trackCount = 0;
      if (data.length) {
        data.forEach((pr: PoseRecord) => {
          if (pr.track_id !== null) trackCount += 1;
          shot = pr.shot;
          pose_interest = pr.pose_interest;
          action_interest = pr.action_interest;
        });
      }
      trackCt = trackCount;
    }
    getFaceData($currentVideo.id, $currentFrame!).then((data) =>
      integrateFaceData(data),
    );
  };

  const integrateFaceData = (data: Array<FaceRecord>) => {
    faceCt = 0;
    if (data && poseData) {
      if (data.length && poseData.length) {
        data.forEach((fr: FaceRecord) => {
          poseData.forEach((pr: PoseRecord, pi: number) => {
            if (fr.pose_idx == pr.pose_idx) {
              faceCt += 1;
              poseData[pi]!.face_bbox = fr.bbox;
              poseData[pi]!.face_landmarks = fr.landmarks;
              poseData[pi]!.face_cluster_id = fr.cluster_id;
            }
          });
        });
      }
    }
  };

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
        on:click={() => ($currentFrame = (Number($currentFrame) || 0) - 1)}
        >previous</button
      >
      <button
        type="button"
        class="btn btn-sm variant-filled"
        on:click={() => ($currentFrame = (Number($currentFrame) || 0) + 1)}
        >next</button
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
              $currentFrame = (Number($currentFrame) || 0) + 5;
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
    <SlideToggle name="show-3d-frame" bind:checked={show3Dframe} size="sm">
      3D scene
    </SlideToggle>
    <SlideToggle
      name="slider-label"
      bind:checked={showFrame}
      size="sm"
      disabled={show3Dframe}
    >
      Show Frame
    </SlideToggle>
    <div>
      <button
        type="button"
        class="btn btn-sm variant-filled"
        on:click={() => ($currentFrame = 0)}>X</button
      >
    </div>
  </header>

  <div class="flex gap-4 p-4 bg-surface-100-800-token">
    {#if poseData}
      {#if !show3Dframe}
        <FrameDisplay {showFrame} bind:poses={poseData} bind:hoveredPoseIdx />
      {:else}
        <div>
          <Canvas3D size={{ width: 640, height: 480 }}>
            <Scene3D></Scene3D>
          </Canvas3D>
        </div>
      {/if}
      <FrameDetails
        bind:poses={poseData}
        {trackCt}
        {faceCt}
        bind:hoveredPoseIdx
        {shot}
        {pose_interest}
        {action_interest}
      />
    {:else}
      Loading pose data... <ProgressBar />
    {/if}
  </div>
</div>
