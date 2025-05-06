<script lang="ts">
  import {
    Paginator,
    RadioGroup,
    RadioItem,
    SlideToggle,
  } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas, Html } from "layercake";
  import { Canvas as Canvas3D } from "@threlte/core";
  import Pose from "@svelte/Pose.svelte";
  import Hand3D from "@svelte/Hand3D.svelte";
  import { formatSeconds } from "@utils";
  import { getExtentFlat } from "../lib/poseutils";

  import { API_BASE } from "@config";
  import {
    currentFrame,
    currentHandPose,
    currentVideo,
    similarHandFrames,
    searchAllVideos,
    searchThresholds,
    webcamImage,
  } from "@svelte/stores";

  export let similarityMetric = "cosine";
  //export let toggle3DHandModal; // May implement this eventually

  let avoidShotInResults: boolean = false;
  let poses: Array<PoseRecord> = [];
  let displayOption = "show_both";

  const simStep = 4;
  let simPager = {
    page: 0,
    offset: 0,
    limit: simStep,
    size: 50,
    amounts: [simStep],
  };

  const resetHands = () => {
    $currentHandPose = null;
    $similarHandFrames = {};
  };

  const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);

  const updateHandData = (data: Array<PoseRecord>) => {
    poses = data;
    $similarHandFrames = {};
    poses.forEach((pose) => {
      if (pose.video_id.toString() == $currentVideo.id)
        $similarHandFrames[pose["frame"]] = 1;
    });

    // This is necessary to make the pager reset reactively
    simPager = {
      page: 1,
      offset: 0,
      limit: simStep,
      size: poses.length,
      amounts: [simStep],
    };
    simPager = simPager;
  };

  const getMaxXywh = (thisPose) => {
    let poseBbox,
      faceBbox,
      rhBbox,
      lhBbox,
      smplPointsWithConfidence,
      cocoPointsWithConfidence,
      facePoints,
      rightHandPoints,
      leftHandPoints,
      searchHandPoints = null;

    ({
      bbox: poseBbox,
      face_bbox: faceBbox,
      rh_bbox: rhBbox,
      lh_bbox: lhBbox,
      keypoints4dh: smplPointsWithConfidence,
      keypoints: cocoPointsWithConfidence,
      face_landmarks: facePoints,
      rh_keypoints_2d: rightHandPoints,
      lh_keypoints_2d: leftHandPoints,
      keypoints2d: searchHandPoints,
    } = thisPose);

    const bboxPoints = [poseBbox, faceBbox].flatMap((xywh) =>
      xywh === undefined
        ? []
        : [xywh[0], xywh[1], xywh[0] + xywh[2], xywh[1] + xywh[3]],
    );

    const smplPoints =
      smplPointsWithConfidence !== undefined
        ? smplPointsWithConfidence.filter((_, index) => (index + 1) % 3 !== 0)
        : null;
    const cocoPoints =
      cocoPointsWithConfidence !== undefined
        ? cocoPointsWithConfidence.filter((_, index) => (index + 1) % 3 !== 0)
        : null;

    const allPointSets = [
      bboxPoints,
      rhBbox,
      lhBbox,
      smplPoints,
      cocoPoints,
      facePoints,
      rightHandPoints,
      leftHandPoints,
      searchHandPoints,
    ].filter((a) => a !== undefined && a !== null);
    const allCoords = allPointSets.flat(1);
    return getExtentFlat(allCoords);
  };

  async function getHandData(
    thisHandPose: PoseRecord | null,
    similarityMetric: string,
    searchAllVideos: boolean,
    searchThresholds: { [id: string]: number },
    avoidShot: boolean,
  ) {
    if (thisHandPose === null) return [];

    let query = "";

    let videoParam: any = thisHandPose.video_id;
    if (searchAllVideos) {
      videoParam = `ALL|${thisHandPose.video_id}`;
    }

    query = `${API_BASE}/hands/similar/${searchThresholds.total_results}/${similarityMetric}|${searchThresholds[similarityMetric]}/${videoParam}/${thisHandPose.frame}/${thisHandPose.pose_idx}/${thisHandPose.search_is_right}/${avoidShot ? thisHandPose.shot : -1}/`;

    const response = await fetch(query);
    return await response.json();
  }

  $: getHandData(
    $currentHandPose,
    similarityMetric,
    $searchAllVideos,
    $searchThresholds,
    avoidShotInResults,
  ).then((data) => updateHandData(data));
</script>

{#if $currentHandPose}
  <section
    class="variant-ghost-secondary px-4 pt-4 pb-8 flex flex-col gap-4 items-center"
  >
    <div class="p-1 inline-flex items-center rounded-token space-x-10">
      <div class="flex items-center space-x-1">
        <span><strong>Hands similarity:</strong></span>
        <RadioGroup>
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="cosine">Joint angles</RadioItem
          >
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="view_invariant">Embedding</RadioItem
          >
        </RadioGroup>
      </div>
      <div class="flex items-center space-x-1">
        <span><strong>Show:</strong></span>
        <RadioGroup>
          <RadioItem
            bind:group={displayOption}
            name="show-background"
            value="show_background">Image</RadioItem
          >
          <RadioItem
            bind:group={displayOption}
            name="show-hand"
            value="show_hand">Pose</RadioItem
          >
          <RadioItem
            bind:group={displayOption}
            name="show-both"
            value="show_both">Both</RadioItem
          >
        </RadioGroup>
      </div>
      <span
        ><strong
          ><button
            class="btn-sm variant-filled"
            type="button"
            on:click={resetHands}>X</button
          ></strong
        ></span
      >
    </div>
    <div class="flex gap-4">
      <div
        class="card min-w-48 stretch-vert variant-ghost-tertiary drop-shadow-lg"
      >
        <header class="p-2">Query Hand (3D)</header>
        <div>
          <Canvas3D size={{ width: 200, height: 300 }}>
            <Hand3D handPose={$currentHandPose} />
          </Canvas3D>
        </div>
        <!-- <footer class="p-2">
              <span
                ><strong
                  ><button
                    class="btn-sm variant-filled"
                    type="button"
                    on:click={toggle3DHandModal}>Open in sketch editor</button
                  ></strong
                ></span
              >
            </footer> -->
      </div>
      <div
        class={$currentHandPose.from_webcam
          ? "card min-w-48 flex flex-col justify-start variant-ghost-tertiary drop-shadow-lg"
          : "card min-w-48 flex flex-col justify-between variant-ghost-tertiary drop-shadow-lg"}
      >
        <header class="p-2">
          {#if !$currentHandPose.from_webcam}
            Frame {$currentHandPose.frame}, Pose: {$currentHandPose.pose_idx +
              1}
          {:else}
            2D Hand
          {/if}
        </header>
        <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
          <LayerCake>
            {#if displayOption == "show_background" || displayOption == "show_both"}
              <Html zIndex={0}>
                {#if !$currentHandPose.from_webcam}
                  <img
                    class="object-contain h-full w-full"
                    src={`${API_BASE}/frame/excerpt/${$currentHandPose.video_id}/${
                      $currentHandPose.frame
                    }/${getMaxXywh($currentHandPose).join(",")}/`}
                    alt={`Frame ${$currentHandPose.frame}, Pose: ${
                      $currentHandPose.pose_idx + 1
                    }`}
                  />
                {:else if $webcamImage !== ""}
                  <!-- <img
                        class="object-contain h-full w-full"
                        src={$webcamImage}
                        alt="Hand from webcam"
                      /> -->
                {:else}
                  <div class="object-contain h-full w-full frame-display" />
                {/if}
              </Html>
            {/if}
            {#if displayOption == "show_hand" || displayOption == "show_both"}
              <Canvas zIndex={1}>
                <Pose
                  poseData={$currentHandPose.keypoints}
                  pose4dhData={$currentHandPose.keypoints4dh}
                  faceData={$currentHandPose.face_landmarks}
                  rightHandData={$currentHandPose.rh_keypoints_2d}
                  leftHandData={$currentHandPose.lh_keypoints_2d}
                  normalizedPose={false}
                  maxXywh={getMaxXywh($currentHandPose)}
                />
              </Canvas>
            {/if}
          </LayerCake>
        </div>
        <footer class="p-2">
          {#if !$currentHandPose.from_webcam}
            <ul>
              <li>
                Time: {formatSeconds(
                  $currentHandPose.frame / $currentVideo.fps,
                )}
              </li>
              <li>
                Hand: {$currentHandPose.search_is_right ? "right" : "left"}
              </li>
              {#if $currentHandPose.face_cluster_id !== null}
                <li>
                  Face group: {$currentHandPose.face_cluster_id}
                </li>
              {/if}
            </ul>
            <span
              ><strong
                ><button
                  class="btn-sm variant-filled"
                  type="button"
                  value={$currentHandPose.frame}
                  on:click={goToFrame}
                  >Go to frame {$currentHandPose.frame}</button
                ></strong
              ></span
            >
          {/if}
        </footer>
      </div>

      <span class="divider-vertical !border-l-8 !border-double" />

      {#each poses as pose, p}
        {#if p >= simPager.offset * simPager.limit && p < simPager.offset * simPager.limit + simPager.limit}
          <div
            class="card min-w-48 flex flex-col justify-between drop-shadow-lg"
          >
            <header class="p-2">
              Frame {pose.frame}, Pose: {pose.pose_idx + 1}
            </header>
            <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
              <LayerCake>
                {#if displayOption == "show_background" || displayOption == "show_both"}
                  <Html zIndex={0}>
                    <img
                      class="object-contain h-full w-full"
                      src={`${API_BASE}/frame/excerpt/${pose.video_id}/${
                        pose.frame
                      }/${getMaxXywh(pose).join(",")}/`}
                      alt={`Frame ${pose.frame}, Pose: ${pose.pose_idx + 1}`}
                    />
                  </Html>
                {/if}
                {#if displayOption == "show_hand" || displayOption == "show_both"}
                  <Canvas zIndex={1}>
                    <Pose
                      poseData={pose.keypoints}
                      pose4dhData={pose.keypoints4dh}
                      faceData={pose.face_landmarks}
                      rightHandData={pose.rh_keypoints_2d}
                      leftHandData={pose.lh_keypoints_2d}
                      normalizedPose={false}
                      maxXywh={getMaxXywh(pose)}
                      searchHandData={pose.keypoints2d}
                      searchHandIsRight={pose.search_is_right}
                    />
                  </Canvas>
                {/if}
              </LayerCake>
            </div>
            <footer class="p-2">
              {#if pose.video_id.toString() == $currentVideo.id}
                <ul>
                  <li>
                    Time: {formatSeconds(pose.frame / $currentVideo.fps)}
                  </li>
                  <li>Distance: {pose.distance?.toFixed(5)}</li>
                  <li>
                    Hand: {pose.search_is_right ? "right" : "left"}
                  </li>
                  {#if pose.face_cluster_id !== null}
                    <li>
                      Face group: {pose.face_cluster_id}
                    </li>
                  {/if}
                </ul>
                <span
                  ><strong
                    ><button
                      class="btn-sm variant-filled"
                      type="button"
                      value={pose.frame}
                      on:click={goToFrame}>Go to frame {pose.frame}</button
                    ></strong
                  ></span
                >
              {:else}
                <ul>
                  <li>{pose.video_name}</li>
                  <li>Distance: {pose.distance?.toFixed(5)}</li>
                </ul>
              {/if}
            </footer>
          </div>
        {/if}
      {/each}
    </div>
    <div class="flex items-center space-x-5">
      <SlideToggle
        name="avoid-shot-toggle"
        bind:checked={avoidShotInResults}
        bind:disabled={$currentHandPose.from_webcam}
        size="sm"
      >
        Exclude current shot
      </SlideToggle>
      <div class="hide-paginator-label flex items-center">
        <span>Similar hands</span>
        <Paginator
          bind:settings={simPager}
          showFirstLastButtons={false}
          showPreviousNextButtons={true}
          amountText="Hands"
        />
      </div>
    </div>
  </section>
{/if}

<style>
  .frame-display {
    background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
    box-shadow: inset 0px 0px 30px 0px #666;
  }
</style>
