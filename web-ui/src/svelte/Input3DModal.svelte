<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { Canvas as Canvas3D } from "@threlte/core";
  import { currentPose, currentVideo } from "@svelte/stores";
  import QueryPose3D from "@svelte/QueryPose3D.svelte";
  import Pose from "./Pose.svelte";

  export let parent: any;

  const startup = async () => {
    return;
  };

  const shutdown = (triggerClose = false) => {
    if (triggerClose) {
      parent.onClose();
    }
  };


  const setSearchPose = () => {

    const searchPose = shiftNormalizeRescalePoseCoords(
      projCoco13Pose,
      $currentVideo.id,
      projExtent.x,
      projExtent.y,
      projExtent.w,
      projExtent.h,
    );

    $currentPose = searchPose;
  };

  onMount(async () => {
    startup();
  });
  onDestroy(async () => {
    shutdown();
  });
</script>
  
<div
  class="w-modal-wide card variant-glass-primary pb-4 flex flex-row items-center"
>
  <div class="flex flex-col items-center w-full">
    <header class="card-header font-bold">
      <h3>Click keypoints to set query pose</h3>
    </header>
    <div class="flex flex-row justify-center">
      <button
        type="button"
        title="Search current pose"
        class="btn-sm px-2 variant-ghost"
        on:click={setSearchPose}>Search pose</button
      >
      <span class="divider-vertical !border-l-8 !border-double"></span>
      <button
        type="button"
        title="Close the camera controls"
        class="btn-sm px-2 variant-ghost"
        on:click={() => {
          shutdown(true);
        }}>Close</button
      >
    </div>
    <div class="card stretch-vert variant-ghost-tertiary drop-shadow-lg">
      <header class="p-2">3D Pose</header>
      <div>
        <Canvas3D size={{width: 800, height: 800}}>
          <QueryPose3D  />
        </Canvas3D>
      </div>
    </div>
  </div>
</div>
  
<style>
</style>
  