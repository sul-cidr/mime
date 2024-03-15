<script lang="ts">
  import {
    Paginator,
    RadioGroup,
    RadioItem,
    SlideToggle,
  } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas } from "layercake";
  import Movelet from "@svelte/Movelet.svelte";
  import { formatSeconds } from "../lib/utils";

  import { API_BASE } from "@config";
  import {
    currentFrame,
    currentMovelet,
    currentMoveletPose,
    currentVideo,
    similarMoveletFrames,
    searchThresholds,
  } from "@svelte/stores";
  let avoidShotInResults: boolean = false;
  export let similarityMetric = "cosine";
  let movelets: Array<MoveletRecord>;

  const simStep = 5;
  let simPager = {
    page: 0,
    offset: 0,
    limit: simStep,
    size: 50,
    amounts: [simStep],
  };

  const resetMovelets = () => {
    $currentMovelet = null;
    $currentMoveletPose = null;
    $similarMoveletFrames = {};
  };

  const updateMoveletData = (data: MoveletRecord[]) => {
    movelets = data;
    $similarMoveletFrames = {};
    movelets.forEach((movelet) => {
      for (let i = movelet["start_frame"]; i <= movelet["end_frame"]; i++) {
        $similarMoveletFrames[i] = 1;
      }
    });

    // This is necessary to make the pager reset reactively
    simPager = {
      page: 0,
      offset: 0,
      limit: simStep,
      size: movelets.length,
      amounts: [simStep],
    };
    simPager = simPager;
  };

  const updateCurrentMovelet = (data: MoveletRecord) => {
    $currentMovelet = data;
  };

  const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);

  async function getMoveletData(
    thisMoveletPose: PoseRecord | null,
    similarityMetric: string,
    searchThresholds: { [id: string]: number },
    avoidShot: boolean,
  ) {
    if (thisMoveletPose === null) return [];
    const response = avoidShot
      ? await fetch(
          `${API_BASE}/movelets/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${thisMoveletPose.video_id}/${thisMoveletPose.frame}/${thisMoveletPose.track_id}/${thisMoveletPose.shot}/`,
        )
      : await fetch(
          `${API_BASE}/movelets/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${thisMoveletPose.video_id}/${thisMoveletPose.frame}/${thisMoveletPose.track_id}/`,
        );
    return await response.json();
  }

  async function getMoveletFromPose(thisMoveletPose: PoseRecord | null) {
    if (thisMoveletPose === null) return null;
    const response = await fetch(
      `${API_BASE}/movelets/pose/${thisMoveletPose.video_id}/${thisMoveletPose.frame}/${thisMoveletPose.track_id}/`,
    );
    return await response.json();
  }

  $: getMoveletData(
    $currentMoveletPose,
    similarityMetric,
    $searchThresholds,
    avoidShotInResults,
  ).then((data) => updateMoveletData(data));

  $: getMoveletFromPose($currentMoveletPose).then((data) =>
    updateCurrentMovelet(data),
  );
</script>

{#if $currentMovelet}
  <section
    class="variant-ghost-secondary px-4 pt-4 pb-8 flex flex-col gap-4 items-center"
  >
    <div class="p-1 inline-flex items-center space-x-1 rounded-token">
      <span><strong>Movelets similarity:</strong></span>
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
      </RadioGroup>
      <span
        ><strong
          ><button
            class="btn-sm variant-filled"
            type="button"
            on:click={resetMovelets}>X</button
          ></strong
        ></span
      >
    </div>
    {#if movelets}
      <div class="flex gap-4">
        <div
          class="card flex flex-col justify-between variant-ghost-tertiary drop-shadow-lg"
        >
          <header class="p-2">
            Frames {$currentMovelet.start_frame} - {$currentMovelet.end_frame},
            Track: {$currentMovelet.track_id}
          </header>
          <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
            <LayerCake>
              <Canvas zIndex={1}>
                <Movelet moveletData={$currentMovelet} />
                <!-- <Pose poseData={$currentMoveletPose.norm} normalizedPose={true} /> -->
              </Canvas>
            </LayerCake>
          </div>
          <footer class="p-2">
            <ul>
              <li>
                Time: {formatSeconds(
                  $currentMovelet.start_frame / $currentVideo.fps,
                )}
              </li>
              <li>
                Face group: {$currentMoveletPose?.face_cluster_id}
              </li>
            </ul>
            <span
              ><strong
                ><button
                  class="btn-sm variant-filled"
                  type="button"
                  value={$currentMovelet.start_frame}
                  on:click={goToFrame}
                  >Go to frame {$currentMovelet.start_frame}</button
                ></strong
              ></span
            >
          </footer>
        </div>

        <span class="divider-vertical !border-l-8 !border-double" />

        {#each movelets as movelet, m}
          {#if m >= simPager.offset * simPager.limit && m < simPager.offset * simPager.limit + simPager.limit}
            <div class="card flex flex-col justify-between drop-shadow-lg">
              <header class="p-2">
                Frames {movelet.start_frame} - {movelet.end_frame}, Track: {movelet.track_id}
              </header>
              <div
                class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]"
              >
                <Movelet moveletData={movelet} />
              </div>
              <footer class="p-2">
                <ul>
                  <li>
                    Time: {formatSeconds(
                      movelet.start_frame / $currentVideo.fps,
                    )}
                  </li>
                  <li>Distance: {movelet.distance?.toFixed(4)}</li>
                  <li>
                    Face group: {movelet.face_cluster_id}
                  </li>
                </ul>
                <span
                  ><strong
                    ><button
                      class="btn-sm variant-filled"
                      type="button"
                      value={movelet.start_frame}
                      on:click={goToFrame}
                      >Go to frame {movelet.start_frame}</button
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
        <div class="hide-paginator-label flex items-baseline">
          <span>Similar movelets</span>
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
