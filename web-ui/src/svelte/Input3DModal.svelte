<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { Canvas as Canvas3D } from "@threlte/core";
  import { currentPose, currentVideo, webcamImage } from "@svelte/stores";
  import QueryPose3D from "@svelte/QueryPose3D.svelte";
  import Pose from "./Pose.svelte";
  import { getPoseExtent, shiftNormalizeRescalePoseCoords } from "../lib/poseutils";


  export let parent: any;

  let posePoints;

  const shutdown = (triggerClose = false) => {
    if (triggerClose) {
      parent.onClose();
    }
  };

  const setSearchPose = () => {

    // The normalized 2D search pose should have 0,0 at top left, with max
    // width and height 100x100, so the 3D pose needs to be normalized and
    // mirrored vertically to work as a 2D search pose.
    let projCoco13Pose = [];
    posePoints.forEach((p) => {
      projCoco13Pose.push({ x: p[0], y: p[1] });
    });

    const pointsExtent = getPoseExtent(projCoco13Pose);

    const xMid = (pointsExtent.x + (pointsExtent.x + pointsExtent.w)) / 2;
    const yMid = (pointsExtent.y + (pointsExtent.y + pointsExtent.h)) / 2;

    let invertedCoco13Pose = [];
    projCoco13Pose.forEach((p) => {
      invertedCoco13Pose.push({ x: p.x, y: p.y - ((p.y - yMid)*2)})
    })

    const invExtent = getPoseExtent(invertedCoco13Pose);

    const searchPose = shiftNormalizeRescalePoseCoords(
      invertedCoco13Pose,
      $currentVideo.id,
      invExtent.x,
      invExtent.y,
      invExtent.w,
      invExtent.h,
    );

    // The 3D viz upscales the pose coords by a factor of 100 from the values
    // in the DB (and returned by the pose estimator), so we need to downscale
    // them at some point before using them to query the DB.
    let proj3dCoords = [];
    posePoints.forEach((p) => {
      proj3dCoords.push(p[0]/100.0, p[1]/100.0, p[2]/100.0);
    });

    searchPose.global3d_coco13 = proj3dCoords;

    $currentPose = searchPose;

    // XXX Maybe draw a blank background? Or don't show this card at all in the search results?
    $webcamImage = "";
  };

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
          <QueryPose3D bind:posePoints />
        </Canvas3D>
      </div>
    </div>
  </div>
</div>
  
<style>
</style>
  