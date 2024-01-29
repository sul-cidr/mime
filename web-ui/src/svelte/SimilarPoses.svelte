<script lang="ts">
  import {
    Paginator,
    RadioGroup,
    RadioItem,
    SlideToggle,
  } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas, Html } from "layercake";
  import Pose from "@svelte/Pose.svelte";
  import { formatSeconds } from "@utils";
  import { getExtent, getNormDims } from "../lib/poseutils";

  import { API_BASE } from "@config";
  import { currentFrame, currentPose, currentVideo, similarPoseFrames } from "@svelte/stores";

  let showFrame: boolean = false;
  let avoidShotInResults: boolean = false;
  export let similarityMetric = "cosine";
  let poses: Array<PoseRecord>;

  const simStep = 5;
  let simPager = {
    offset: 0,
    limit: simStep,
    size: 50,
    amounts: [simStep],
  };

  const resetPoses = () => ($similarPoseFrames = {});

  const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);

  const updatePoseData = (data: Array<PoseRecord>) => {
    poses = data;
    $similarPoseFrames = {};
    poses.forEach((pose) => {
      $similarPoseFrames[pose["frame"]] = 1;
    });
    simPager.size = poses.length;
  };

  async function getPoseData(
    videoId: number,
    frame: number,
    poseIdx: number,
    similarityMetric: string,
    shot: string,
    avoidShot: boolean,
  ) {
    const response = avoidShot ?
    await fetch(
      `${API_BASE}/poses/similar/${similarityMetric}/${videoId}/${frame}/${poseIdx}/${shot}/`,
    )
    :
    await fetch(
      `${API_BASE}/poses/similar/${similarityMetric}/${videoId}/${frame}/${poseIdx}/`,

    );
    return await response.json();
  }

  $: getPoseData(
    $currentPose.video_id,
    $currentPose.frame,
    $currentPose.pose_idx,
    similarityMetric,
    $currentPose.shot,
    avoidShotInResults,
  ).then((data) => updatePoseData(data));
</script>

{#if Object.keys($similarPoseFrames).length}
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
          <RadioItem
            bind:group={similarityMetric}
            name="similarity-metric"
            value="poem_embedding">View Invariant</RadioItem
          >
        </RadioGroup>
      </div>
      <SlideToggle name="show-frame-toggle" bind:checked={showFrame} size="sm">
        Show Image
      </SlideToggle>
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
        <div class="card variant-ghost-tertiary drop-shadow-lg">
          <header class="p-2">
            Frame {$currentPose.frame}, Pose: {$currentPose.pose_idx + 1}
          </header>
          <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
            <LayerCake>
              {#if showFrame}
                <Html zIndex={0}>
                  <img
                    class="object-contain h-full w-full"
                    src={`${API_BASE}/frame/resize/${$currentPose.video_id}/${
                      $currentPose.frame
                    }/${getExtent($currentPose.keypointsopp).join(
                      ",",
                    )}|${getNormDims($currentPose.norm).join(",")}/`}
                    alt={`Frame ${$currentPose.frame}, Pose: ${
                      $currentPose.pose_idx + 1
                    }`}
                  />
                </Html>
              {/if}
              <Canvas zIndex={1}>
                <Pose poseData={$currentPose.norm} pose4dhData={$currentPose.norm4dh} normalizedPose={true} />
              </Canvas>
            </LayerCake>
          </div>
          <footer class="p-2">
            <ul>
              <li>
                Time: {formatSeconds($currentPose.frame / $currentVideo.fps)}
              </li>
            </ul>
            <span
            ><strong
              ><button
                class="btn-sm variant-filled"
                type="button"
                value={$currentPose.frame}
                on:click={goToFrame}>Go to frame {$currentPose.frame}</button
              ></strong
            ></span>
          </footer>
        </div>

        <span class="divider-vertical !border-l-8 !border-double" />

        {#each poses as pose, p}
          {#if p >= simPager.offset * simPager.limit && p < simPager.offset * simPager.limit + simPager.limit}
            <div class="card drop-shadow-lg">
              <header class="p-2">
                Frame {pose.frame}, Pose: {pose.pose_idx + 1}
              </header>
              <div
                class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]"
              >
                <LayerCake>
                  {#if showFrame}
                    <Html zIndex={0}>
                      <img
                        class="object-contain h-full w-full"
                        src={`${API_BASE}/frame/resize/${pose.video_id}/${
                          pose.frame
                        }/${getExtent(pose.keypointsopp).join(",")}|${getNormDims(
                          pose.norm,
                        ).join(",")}/`}
                        alt={`Frame ${pose.frame}, Pose: ${pose.pose_idx + 1}`}
                      />
                    </Html>
                  {/if}
                  <Canvas zIndex={1}>
                    <Pose poseData={pose.norm} pose4dhData={$currentPose.norm4dh} normalizedPose={true} />
                  </Canvas>
                </LayerCake>
              </div>
              <footer class="p-2">
                <ul>
                  <li>Time: {formatSeconds(pose.frame / $currentVideo.fps)}</li>
                  <li>Distance: {pose.distance?.toFixed(5)}</li>
                </ul>
                <span
                ><strong
                  ><button
                    class="btn-sm variant-filled"
                    type="button"
                    value={pose.frame}
                    on:click={goToFrame}>Go to frame {pose.frame}</button
                  ></strong
                ></span>
              </footer>
            </div>
          {/if}
        {/each}
      </div>
      <div class="flex items-center space-x-5">
        <SlideToggle name="avoid-shot-toggle" bind:checked={avoidShotInResults} size="sm">
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
