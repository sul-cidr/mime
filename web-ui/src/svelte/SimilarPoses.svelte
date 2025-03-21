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
  import Pose3D from "@svelte/Pose3D.svelte";
  import { formatSeconds } from "@utils";
  import { getExtent, getNormDims } from "../lib/poseutils";

  import { API_BASE } from "@config";
  import {
    currentFrame,
    currentPose,
    currentVideo,
    similarPoseFrames,
    searchAllVideos,
    searchThresholds,
    webcamImage,
  } from "@svelte/stores";

  export let similarityMetric = "cosine";
  export let toggle3DPoseModal;

  let avoidShotInResults: boolean = false;
  let poses: Array<PoseRecord>;
  let displayOption = "show_both";

  const simStep = 4;
  let simPager = {
    page: 0,
    offset: 0,
    limit: simStep,
    size: 50,
    amounts: [simStep],
  };

  const resetPoses = () => {
    $currentPose = null;
    $similarPoseFrames = {};
  };

  const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);

  const updatePoseData = (data: Array<PoseRecord>) => {
    poses = data;
    $similarPoseFrames = {};
    poses.forEach((pose) => {
      if (pose.video_id == $currentVideo.id)
        $similarPoseFrames[pose["frame"]] = 1;
    });

    // This is necessary to make the pager reset reactively
    simPager = {
      page: 0,
      offset: 0,
      limit: simStep,
      size: poses.length,
      amounts: [simStep],
    };
    simPager = simPager;
  };

  async function getPoseData(
    thisPose: PoseRecord | null,
    similarityMetric: string,
    searchAllVideos: boolean,
    searchThresholds: { [id: string]: number },
    avoidShot: boolean,
  ) {
    if (thisPose === null) return [];

    let query = "";

    let videoParam: any = thisPose.video_id;
    if (searchAllVideos) {
      videoParam = `ALL|${thisPose.video_id}`;
    }

    if (thisPose.from_webcam) {
      query = `${API_BASE}/poses/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${videoParam}/${similarityMetric === "global" ? thisPose.global3d_coco13 : thisPose.norm}/`;
    } else {
      query = `${API_BASE}/poses/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${videoParam}/${thisPose.frame}/${thisPose.pose_idx}/${avoidShot ? thisPose.shot : -1}/`;
    }

    const response = await fetch(query);
    return await response.json();
  }

  $: getPoseData(
    $currentPose,
    similarityMetric,
    $searchAllVideos,
    $searchThresholds,
    avoidShotInResults,
  ).then((data) => updatePoseData(data));
</script>

{#if $currentPose}
  <section
    class="variant-ghost-secondary px-4 pt-4 pb-8 flex flex-col gap-4 items-center"
  >
    <div class="p-1 inline-flex items-center rounded-token space-x-10">
      <div class="flex items-center space-x-1">
        <span><strong>Poses similarity:</strong></span>
        <RadioGroup>
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="cosine">Cosine</RadioItem
          >
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="euclidean">Euclidean</RadioItem
          >
          <!-- <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="innerproduct">Inner Product</RadioItem
          > -->
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="view_invariant">2D+ Cosine</RadioItem
          >
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="global">3D Cosine</RadioItem
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
            name="show-pose"
            value="show_pose">Pose</RadioItem
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
            on:click={resetPoses}>X</button
          ></strong
        ></span
      >
    </div>
    {#if poses}
      <div class="flex gap-4">
        <div
          class="card min-w-48 stretch-vert variant-ghost-tertiary drop-shadow-lg"
        >
          <header class="p-2">3D Pose</header>
          <div>
            <Canvas3D size={{ width: 200, height: 300 }}>
              <Pose3D pose={$currentPose} />
            </Canvas3D>
          </div>
          <footer class="p-2">
            <span
              ><strong
                ><button
                  class="btn-sm variant-filled"
                  type="button"
                  on:click={toggle3DPoseModal}>Open in sketch editor</button
                ></strong
              ></span
            >
          </footer>
        </div>
        <div
          class={$currentPose.from_webcam
            ? "card min-w-48 flex flex-col justify-start variant-ghost-tertiary drop-shadow-lg"
            : "card min-w-48 flex flex-col justify-between variant-ghost-tertiary drop-shadow-lg"}
        >
          <header class="p-2">
            {#if !$currentPose.from_webcam}
              Frame {$currentPose.frame}, Pose: {$currentPose.pose_idx + 1}
            {:else}
              2D Pose
            {/if}
          </header>
          <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
            <LayerCake>
              {#if displayOption == "show_background" || displayOption == "show_both"}
                <Html zIndex={0}>
                  {#if !$currentPose.from_webcam}
                    <img
                      class="object-contain h-full w-full"
                      src={`${API_BASE}/frame/resize/${$currentPose.video_id}/${
                        $currentPose.frame
                      }/${getExtent($currentPose.keypoints).join(
                        ",",
                      )}|${getNormDims($currentPose.norm).join(",")}/`}
                      alt={`Frame ${$currentPose.frame}, Pose: ${
                        $currentPose.pose_idx + 1
                      }`}
                    />
                  {:else if $webcamImage !== ""}
                    <img
                      class="object-contain h-full w-full"
                      src={$webcamImage}
                      alt="Pose excerpt from webcam"
                    />
                  {:else}
                    <div class="object-contain h-full w-full frame-display" />
                  {/if}
                </Html>
              {/if}
              {#if displayOption == "show_pose" || displayOption == "show_both"}
                <Canvas zIndex={1}>
                  <Pose poseData={$currentPose.norm} normalizedPose={true} />
                </Canvas>
              {/if}
            </LayerCake>
          </div>
          <footer class="p-2">
            {#if !$currentPose.from_webcam}
              <ul>
                <li>
                  Time: {formatSeconds($currentPose.frame / $currentVideo.fps)}
                </li>
                <li>
                  Face group: {$currentPose.face_cluster_id}
                </li>
              </ul>
              <span
                ><strong
                  ><button
                    class="btn-sm variant-filled"
                    type="button"
                    value={$currentPose.frame}
                    on:click={goToFrame}
                    >Go to frame {$currentPose.frame}</button
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
              <div
                class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]"
              >
                <LayerCake>
                  {#if displayOption == "show_background" || displayOption == "show_both"}
                    <Html zIndex={0}>
                      <img
                        class="object-contain h-full w-full"
                        src={`${API_BASE}/frame/resize/${pose.video_id}/${
                          pose.frame
                        }/${getExtent(pose.keypoints).join(",")}|${getNormDims(
                          pose.norm,
                        ).join(",")}/`}
                        alt={`Frame ${pose.frame}, Pose: ${pose.pose_idx + 1}`}
                      />
                    </Html>
                  {/if}
                  {#if displayOption == "show_pose" || displayOption == "show_both"}
                    <Canvas zIndex={1}>
                      <Pose poseData={pose.norm} normalizedPose={true} />
                    </Canvas>
                  {/if}
                </LayerCake>
              </div>
              <footer class="p-2">
                {#if pose.video_id == $currentVideo.id}
                  <ul>
                    <li>
                      Time: {formatSeconds(pose.frame / $currentVideo.fps)}
                    </li>
                    <li>Distance: {pose.distance?.toFixed(5)}</li>
                    <li>
                      Face group: {pose.face_cluster_id}
                    </li>
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
          bind:disabled={$currentPose.from_webcam}
          size="sm"
        >
          Exclude current shot
        </SlideToggle>
        <div class="hide-paginator-label flex items-center">
          <span>Similar poses</span>
          <Paginator
            bind:settings={simPager}
            showFirstLastButtons={false}
            showPreviousNextButtons={true}
            amountText="Poses"
          />
        </div>
      </div>
    {/if}
  </section>
{/if}

<style>
  .frame-display {
    background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
    box-shadow: inset 0px 0px 30px 0px #666;
  }
</style>
