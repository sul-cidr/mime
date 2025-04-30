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
    //import Hand3D from "@svelte/Hand3D.svelte";
    import { formatSeconds } from "@utils";
    import { getExtent, getNormDims } from "../lib/poseutils";
  
    import { API_BASE } from "@config";
    import {
      currentFrame,
      currentHand,
      currentHandPose,
      currentVideo,
      similarHandFrames,
      searchAllVideos,
      searchThresholds,
      webcamImage,
    } from "@svelte/stores";
  
    export let similarityMetric = "cosine";
    //export let toggle3DHandModal;
  
    let avoidShotInResults: boolean = false;
    let poses: Array<PoseRecord>;
    let hands: Array<HandRecord>;
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
      $currentHand = null;
      $currentHandPose = null;
      $similarHandFrames = {};
    };
  
    const goToFrame = (e: any) => ($currentFrame = e.originalTarget.value);
  
    const updateHandData = (data: Array<HandRecord>) => {
      hands = data;
      $similarHandFrames = {};
      hands.forEach((hand) => {
        if (hand.video_id.toString() == $currentVideo.id)
          $similarHandFrames[hand["frame"]] = 1;
      });
  
      // This is necessary to make the pager reset reactively
      simPager = {
        page: 0,
        offset: 0,
        limit: simStep,
        size: hands.length,
        amounts: [simStep],
      };
      simPager = simPager;
    };
  
    async function getHandData(
      //thisHand: HandRecord | null,
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
  
      //if (thisHand.from_webcam) {
      //  query = `${API_BASE}/poses/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${videoParam}/${similarityMetric === "global" ? thisPose.global3d_coco13 : thisPose.norm}/`;
      //} else {
      query = `${API_BASE}/hands/similar/${searchThresholds["total_results"]}/${similarityMetric}|${searchThresholds[similarityMetric]}/${videoParam}/${thisHandPose.frame}/${thisHandPose.pose_idx}/${thisHandPose.search_is_right}/${avoidShot ? thisHandPose.shot : -1}/`;
      //}
  
      console.log("Hands query:", query)

      const response = await fetch(query);
      return await response.json();
    }
  
    $: getHandData(
      //$currentHand,
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
              value="cosine">Cosine</RadioItem
            >
            <!-- <RadioItem
              bind:group={similarityMetric}
              name="similarity-metric"
              value="euclidean">Euclidean</RadioItem
            > -->
            <!-- <RadioItem
              bind:group={similarityMetric}
              name="similarity-metric"
              value="innerproduct">Inner Product</RadioItem
            > -->
            <!-- <RadioItem
              bind:group={similarityMetric}
              name="similarity-metric"
              value="view_invariant">2D+ Cosine</RadioItem
            > -->
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
              name="show-hand"
              value="show_hand">Hand</RadioItem
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
      {#if hands}
        <div class="flex gap-4">
          <div
            class="card min-w-48 stretch-vert variant-ghost-tertiary drop-shadow-lg"
          >
            <header class="p-2">3D Pose</header>
            <!-- <div>
              <Canvas3D size={{ width: 200, height: 300 }}>
                <Hand3D hand={$currentHand} />
              </Canvas3D>
            </div> -->
            <!-- <footer class="p-2">
              <span
                ><strong
                  ><button
                    class="btn-sm variant-filled"
                    type="button"
                    on:click={toggle3DPoseModal}>Open in sketch editor</button
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
                Frame {$currentHandPose.frame}, Pose: {$currentHandPose.pose_idx + 1}
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
                        src={`${API_BASE}/frame/resize/${$currentHandPose.video_id}/${
                          $currentHandPose.frame
                        }/${getExtent($currentHandPose.keypoints).join(
                          ",",
                        )}|${getNormDims($currentHandPose.norm).join(",")}/`}
                        alt={`Frame ${$currentHandPose.frame}, Pose: ${
                          $currentHandPose.pose_idx + 1
                        }`}
                      />
                    {:else if $webcamImage !== ""}
                      <!-- <img
                        class="object-contain h-full w-full"
                        src={$webcamImage}
                        alt="Pose excerpt from webcam"
                      /> -->
                    {:else}
                      <div class="object-contain h-full w-full frame-display" />
                    {/if}
                  </Html>
                {/if}
                {#if displayOption == "show_hand" || displayOption == "show_both"}
                  <Canvas zIndex={1}>
                    <Pose poseData={$currentHandPose.norm} normalizedPose={true} />
                  </Canvas>
                {/if}
              </LayerCake>
            </div>
            <footer class="p-2">
              {#if !$currentHandPose.from_webcam}
                <ul>
                  <li>
                    Time: {formatSeconds($currentHandPose.frame / $currentVideo.fps)}
                  </li>
                  <!-- <li>
                    Face group: {$currentPose.face_cluster_id}
                  </li> -->
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
  
          <!-- {#each hands as hand, h}
            {#if h >= simPager.offset * simPager.limit && h < simPager.offset * simPager.limit + simPager.limit}
              <div
                class="card min-w-48 flex flex-col justify-between drop-shadow-lg"
              >
                <header class="p-2">
                  Frame {hand.frame}, Pose: {hand.pose_idx + 1}
                </header>
                <div
                  class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]"
                >
                  <LayerCake>
                    {#if displayOption == "show_background" || displayOption == "show_both"}
                      <Html zIndex={0}>
                        <img
                          class="object-contain h-full w-full"
                          src={`${API_BASE}/frame/resize/${hand.video_id}/${
                            hand.frame
                          }/${getExtent(hand.keypoints2d).join(",")}|${getNormDims(
                            hand.norm,
                          ).join(",")}/`}
                          alt={`Frame ${hand.frame}, Pose: ${hand.pose_idx + 1}`}
                        />
                      </Html>
                    {/if}
                    {#if displayOption == "show_hand" || displayOption == "show_both"}
                      <Canvas zIndex={1}>
                        <Hand handData={hand.norm} normalizedHand={true} />
                      </Canvas>
                    {/if}
                  </LayerCake>
                </div>
                <footer class="p-2">
                  {#if hand.video_id.toString() == $currentVideo.id}
                    <ul>
                      <li>
                        Time: {formatSeconds(hand.frame / $currentVideo.fps)}
                      </li>
                      <li>Distance: {hand.distance?.toFixed(5)}</li>
                      <li>
                        Face group: {hand.face_cluster_id}
                      </li>
                    </ul>
                    <span
                      ><strong
                        ><button
                          class="btn-sm variant-filled"
                          type="button"
                          value={hand.frame}
                          on:click={goToFrame}>Go to frame {hand.frame}</button
                        ></strong
                      ></span
                    >
                  {:else}
                    <ul>
                      <li>{hand.video_name}</li>
                      <li>Distance: {hand.distance?.toFixed(5)}</li>
                    </ul>
                  {/if}
                </footer>
              </div>
            {/if}
          {/each} -->
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
      {/if}
    </section>
  {/if}
  
  <style>
    .frame-display {
      background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
      box-shadow: inset 0px 0px 30px 0px #666;
    }
  </style>
  