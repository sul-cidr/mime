<script lang="ts">
  import { onDestroy } from "svelte";
  import { Canvas as Canvas3D } from "@threlte/core";
  import { currentPose, currentVideo, webcamImage } from "@svelte/stores";
  import QueryPose3D from "@svelte/QueryPose3D.svelte";
  import {
    getPoseExtent,
    shiftNormalizeRescalePoseCoords,
  } from "../lib/poseutils";

  export let parent: any;

  let posePoints: [];
  let viewPoint = "front";
  let resetPose;

  const buttonClass = "btn-sm px-2 variant-ghost";
  const selectedButtonClass = "btn-sm px-2 variant-ghost-success";

  const shutdown = (triggerClose = false) => {
    if (triggerClose) {
      parent.onClose();
    }
  };

  const setSearchPose = () => {
    if (viewPoint === "side") {
      viewPoint = "front";
      let rotatedCoords: [] = [];
      posePoints.forEach((p) => {
        rotatedCoords.push([p[2], p[1], -p[0]]);
      });
      posePoints = [...rotatedCoords];
    }

    // The normalized 2D search pose should have 0,0 at top left, with max
    // width and height 100x100, so the 3D pose needs to be normalized and
    // mirrored vertically to work as a 2D search pose.
    let projCoco13Pose: [] = [];
    posePoints.forEach((p) => {
      projCoco13Pose.push({ x: p[0], y: p[1] });
    });

    const pointsExtent = getPoseExtent(projCoco13Pose);

    const yMid = (pointsExtent.y + (pointsExtent.y + pointsExtent.h)) / 2;

    let invertedCoco13Pose: [] = [];
    projCoco13Pose.forEach((p) => {
      invertedCoco13Pose.push({ x: p.x, y: p.y - (p.y - yMid) * 2 });
    });

    const invExtent = getPoseExtent(invertedCoco13Pose);

    const searchPose = shiftNormalizeRescalePoseCoords(
      invertedCoco13Pose,
      $currentVideo.id,
      invExtent.x,
      invExtent.y,
      invExtent.w,
      invExtent.h,
    );

    // The 3D viz shifts and scales the pose coords from the DB/PHALP to fit in
    // a -.5 <-> .5 box in each dimension, then upscales them by a factor of
    // 100, so we need to downscale them at some point before using them to query
    // the DB.
    // NOTE: Actually the 3D coords in the DB tend to exceed a 1x1x1 box in at
    // least one dimension, so the synthesized 3D poses from the pose editor
    // don't have quite the same scaling and centering regime. But the
    // similarity indices used for searching (Euclidean, cosine) tend to be
    // fairly robust to these discrepancies.
    let proj3dCoords: [] = [];
    posePoints.forEach((p) => {
      proj3dCoords.push(p[0] / 100.0, p[1] / 100.0, p[2] / 100.0);
    });

    searchPose.global3d_coco13 = proj3dCoords;

    $currentPose = searchPose;

    // Maybe draw in a blank background? Currently the alt text is visible if
    // there's no actual webcam image (as is the case with synthetic poses).
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
      <h3>Click and drag keypoints to modify query pose</h3>
    </header>
    <div class="flex flex-row justify-center items-center">
      <button
        type="button"
        title="Edit pose in frontal view"
        class={viewPoint === "front" ? selectedButtonClass : buttonClass}
        on:click={() => (viewPoint = "front")}>Edit front</button
      >
      <button
        type="button"
        title="Edit pose in side view"
        class={viewPoint === "side" ? selectedButtonClass : buttonClass}
        on:click={() => (viewPoint = "side")}>Edit side</button
      >
      <span class="divider-vertical !border-l-8 !border-double"></span>
      <button
        type="button"
        title="Search current pose"
        class={buttonClass}
        on:click={setSearchPose}>Search pose</button
      >
      <button
        type="button"
        title="Reset query pose to default"
        class={buttonClass}
        on:click={resetPose}>Reset pose</button
      >
      <span class="divider-vertical !border-l-8 !border-double"></span>
      <button
        type="button"
        title="Close the sketch window"
        class={buttonClass}
        on:click={() => {
          shutdown(true);
        }}>Close</button
      >
    </div>
    <div class="card stretch-vert variant-ghost-tertiary drop-shadow-lg">
      <header class="p-2">3D Pose - {viewPoint} view</header>
      <div>
        <Canvas3D size={{ width: 800, height: 800 }}>
          <QueryPose3D bind:posePoints {viewPoint} bind:resetPose />
        </Canvas3D>
      </div>
    </div>
  </div>
</div>

<style>
</style>
