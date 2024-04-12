<script lang="ts">
  import {
    Paginator,
    RadioGroup,
    RadioItem,
    SlideToggle,
  } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas, Html } from "layercake";
  import Pose from "@svelte/Pose.svelte";
  import { formatSeconds } from "../lib/utils";
  import { getExtent, getNormDims } from "../lib/poseutils";

  import { API_BASE } from "@config";
  import {
    currentFrame,
    currentActionPose,
    currentVideo,
    similarActionFrames,
    searchThresholds,
  } from "@svelte/stores";
  let avoidShotInResults: boolean = false;
  export let similarityMetric = "cosine";
  let actionPoses: Array<PoseRecord>;
  let displayOption = "show_both";

  const simStep = 5;
  let simPager = {
    page: 0,
    offset: 0,
    limit: simStep,
    size: 50,
    amounts: [simStep],
  };

  const resetActionPoses = () => {
    $currentActionPose = null;
    $similarActionFrames = {};
  };

  const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);

  const updateActionData = (data: PoseRecord[]) => {
    actionPoses = data;
    $similarActionFrames = {};
    actionPoses.forEach((pose) => {
      $similarActionFrames[pose["frame"]] = 1;
    });

    // This is necessary to make the pager reset reactively
    simPager = {
      page: 0,
      offset: 0,
      limit: simStep,
      size: actionPoses.length,
      amounts: [simStep],
    };
    simPager = simPager;
  };

  const updateCurrentAction = (data: ActionRecord) => {
    $currentActionPose = data;
  };

  async function getActionData(
    thisActionPose: PoseRecord | null,
    similarityMetric: string,
    searchThresholds: { [id: string]: number },
    avoidShot: boolean,
  ) {
    if (thisActionPose === null) return [];
    const response = avoidShot
      ? await fetch(
          `${API_BASE}/actions/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${thisActionPose.video_id}/${thisActionPose.frame}/${thisActionPose.track_id}/${thisActionPose.shot}/`,
        )
      : await fetch(
          `${API_BASE}/actions/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${thisActionPose.video_id}/${thisActionPose.frame}/${thisActionPose.track_id}/`,
        );
    return await response.json();
  }

  //   async function getActionFromPose(thisActionPose: PoseRecord | null) {
  //     if (thisActionPose === null) return null;
  //     const response = await fetch(
  //       `${API_BASE}/action/pose/${thisActionPose.video_id}/${thisActionPose.frame}/${thisActionPose.track_id}/`,
  //     );
  //     return await response.json();
  //   }

  $: getActionData(
    $currentActionPose,
    similarityMetric,
    $searchThresholds,
    avoidShotInResults,
  ).then((data) => updateActionData(data));

  //   $: getActionFromPose($currentActionPose).then((data) =>
  //     updateCurrentAction(data),
  //   );
</script>

{#if $currentActionPose}
  <section
    class="variant-ghost-secondary px-4 pt-4 pb-8 flex flex-col gap-4 items-center"
  >
    <div class="p-1 inline-flex items-center space-x-10 rounded-token">
      <div class="flex items-center space-x-1">
        <span><strong>Similar actions</strong></span>
        <span class="divider-vertical !border-l-8 !border-double" />
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
            on:click={resetActionPoses}>X</button
          ></strong
        ></span
      >
    </div>
    {#if actionPoses}
      <div class="flex gap-4">
        <div
          class="card flex flex-col justify-between variant-ghost-tertiary drop-shadow-lg"
        >
          <header class="p-2">
            Frame {$currentActionPose.frame}, Pose: {$currentActionPose.pose_idx +
              1}
          </header>
          <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
            <LayerCake>
              {#if displayOption == "show_background" || displayOption == "show_both"}
                <Html zIndex={0}>
                  <img
                    class="object-contain h-full w-full"
                    src={`${API_BASE}/frame/resize/${$currentActionPose.video_id}/${
                      $currentActionPose.frame
                    }/${getExtent($currentActionPose.keypoints).join(
                      ",",
                    )}|${getNormDims($currentActionPose.norm).join(",")}/`}
                    alt={`Frame ${$currentActionPose.frame}, Pose: ${
                      $currentActionPose.pose_idx + 1
                    }`}
                  />
                </Html>
              {/if}
              {#if displayOption == "show_pose" || displayOption == "show_both"}
                <Canvas zIndex={1}>
                  <Pose
                    poseData={$currentActionPose.norm}
                    normalizedPose={true}
                  />
                </Canvas>
              {/if}
            </LayerCake>
          </div>
          <footer class="p-2">
            <ul>
              <li>
                Time: {formatSeconds(
                  $currentActionPose.frame / $currentVideo.fps,
                )}
              </li>
              <li>
                <ul>
                  {#each $currentActionPose.action_labels as action, a}
                    <li>{action}</li>
                  {/each}
                </ul>
              </li>
              <li>
                Face group: {$currentActionPose.face_cluster_id}
              </li>
            </ul>
            <span
              ><strong
                ><button
                  class="btn-sm variant-filled"
                  type="button"
                  value={$currentActionPose.frame}
                  on:click={goToFrame}
                  >Go to frame {$currentActionPose.frame}</button
                ></strong
              ></span
            >
          </footer>
        </div>

        <span class="divider-vertical !border-l-8 !border-double" />

        {#each actionPoses as pose, p}
          {#if p >= simPager.offset * simPager.limit && p < simPager.offset * simPager.limit + simPager.limit}
            <div class="card flex flex-col justify-between drop-shadow-lg">
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
                <ul>
                  <li>Time: {formatSeconds(pose.frame / $currentVideo.fps)}</li>
                  <li>Distance: {pose.distance?.toFixed(5)}</li>
                  <li>
                    <ul>
                      {#each pose.action_labels as action, a}
                        <li>{action}</li>
                      {/each}
                    </ul>
                  </li>
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
              </footer>
            </div>
          {/if}
        {/each}
      </div>
      <div class="flex items-center space-x-5">
        <SlideToggle
          name="avoid-shot-toggle"
          bind:checked={avoidShotInResults}
          size="sm"
        >
          Exclude current shot
        </SlideToggle>
        <div class="hide-paginator-label flex items-center">
          <span>Similar action poses</span>
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
