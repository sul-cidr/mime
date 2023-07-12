<script lang="ts">
    import { Paginator, RadioGroup, RadioItem, SlideToggle } from "@skeletonlabs/skeleton";
    import { LayerCake, Canvas, Html } from "layercake";
    import Movelet from "@svelte/Movelet.svelte";
    import { formatSeconds } from "../lib/utils";
  
    import { API_BASE } from "@config";
    import { currentMovelet, currentMoveletPose, currentVideo, similarMoveletFrames, similarPoseFrames } from "@svelte/stores";
  
    //let showFrame: boolean = false;
    export let similarityMetric = "cosine";
    let movelets: Array<MoveletRecord>;
  
    const simStep = 5;
    let simPager = {
      offset: 0,
      limit: simStep,
      size: 50,
      amounts: [simStep]
    };
  
    const updateMoveletData = (data: MoveletRecord[]) => {
      movelets = data;
      $similarMoveletFrames = {};
      $similarPoseFrames = {};
      movelets.forEach((movelet) => {
        for (let i = movelet['start_frame']; i <= movelet['end_frame']; i++) {
            $similarMoveletFrames[i] = 1;
            $similarPoseFrames[i] = 1;
        }
      });
      simPager.size=movelets.length
    };

    const updateCurrentMovelet = (data: MoveletRecord) => {
      $currentMovelet = data;
    }
  
    async function getMoveletData(
      videoId: number,
      frame: number,
      trackIdx: number,
      similarityMetric: string,
    ) {
      const response = await fetch(
        `${API_BASE}/movelets/similar/${similarityMetric}/${videoId}/${frame}/${trackIdx}`,
      );
      return await response.json();
    }

    async function getMoveletFromPose(
      videoId: number,
      frame: number,
      trackIdx: number,
    ) {
      const response = await fetch(
        `${API_BASE}/movelets/pose/${videoId}/${frame}/${trackIdx}/`,
      );
      return await response.json();
    }
  
    // Not currently used, but worth keeping around for a bit
    const shiftToOrigin = (keypoints: CocoSkeletonWithConfidence, bbox:FixedLengthArray<number, 4>) => {
      let newKeypoints: CocoSkeletonWithConfidence = [...keypoints];
  
      for (let x:number = 0; x<keypoints.length; x+=3) {
        newKeypoints[x] -= bbox[0];
      }
      for (let y:number = 1; y<keypoints.length; y+=3) {
        newKeypoints[y] -= bbox[1];
      }
      return newKeypoints;
    }
  
    const getNormDims = (keypoints: CocoSkeletonNoConfidence) => {
      let x_values:Array<number> = [];
      let y_values:Array<number> = [];
      for (let i:number = 0; i<keypoints.length; i++) {
        if (keypoints[i] >= 0) {
          if (i % 2 == 0) {
            x_values.push(keypoints[i]);
          } else {
            y_values.push(keypoints[i]);
          }
        }
      }
      let min_x = Math.min(...x_values);
      let max_x = Math.max(...x_values);
      let min_y = Math.min(...y_values);
      let max_y = Math.max(...y_values);
  
      let width = max_x - min_x;
      let height = max_y - min_y;
  
      return [width, height];
    }
  
    const getExtent = (keypoints: CocoSkeletonWithConfidence) => {
      let x_values:Array<number> = [];
      let y_values:Array<number> = [];
      for (let i:number = 0; i<keypoints.length; i++) {
        if ((i % 3 == 0) && (keypoints[i+2] > 0)) {
          x_values.push(keypoints[i]);        
        } else if (((i-1) % 3 == 0) && (keypoints[i+1] > 0)) {
          y_values.push(keypoints[i]);      
        }
      }
  
      let min_x = Math.min(...x_values);
      let max_x = Math.max(...x_values);
      let min_y = Math.min(...y_values);
      let max_y = Math.max(...y_values);
  
      let width = max_x - min_x;
      let height = max_y - min_y;
  
      return [min_x, min_y, width, height];
    }
  
  
    $: getMoveletData(
      $currentMoveletPose.video_id,
      $currentMoveletPose.frame,
      $currentMoveletPose.track_id,
      similarityMetric,
    ).then((data) => updateMoveletData(data));

    $: getMoveletFromPose(
      $currentMoveletPose.video_id,
      $currentMoveletPose.frame,
      $currentMoveletPose.track_id,
    ).then((data) => updateCurrentMovelet(data));
  </script>
  
  {#if Object.keys($similarMoveletFrames).length}
    <section
      class="variant-ghost-secondary px-4 pt-4 pb-8 flex flex-col gap-4 items-center"
    >
      <div class="p-1 inline-flex items-center space-x-1 rounded-token">
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
            value="innerproduct">Inner Product</RadioItem
          >
        </RadioGroup>
        <!-- <SlideToggle name="slider-label" bind:checked={showFrame} size="sm">
          Show Image
        </SlideToggle> -->
      </div>
      {#if movelets}
        <div class="flex gap-4">
          <div class="card variant-ghost-tertiary drop-shadow-lg">
            <header class="p-2">
              Frames {$currentMovelet.start_frame} - {$currentMovelet.end_frame}, Track: {$currentMovelet.track_id}
            </header>
            <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
              <LayerCake>
                <Canvas zIndex={1}>
                  <Movelet moveletData={$currentMovelet} normalizedPose={true} />
                  <!-- <Pose poseData={$currentMoveletPose.norm} normalizedPose={true} /> -->
                </Canvas>
              </LayerCake>
            </div>
            <footer class="p-2">
              <ul>
                <li>
                  Time: {formatSeconds($currentMoveletPose.frame / $currentVideo.fps)}
                </li>
              </ul>
            </footer>
          </div>
  
          <span class="divider-vertical !border-l-8 !border-double" />
  
          {#each movelets as movelet, m}
            {#if m >= (simPager.offset * simPager.limit) && m < (simPager.offset * simPager.limit) + simPager.limit}
              <div class="card drop-shadow-lg">
                <header class="p-2">
                  Frames {movelet.start_frame} - {movelet.end_frame}, Track: {movelet.track_id + 1}
                </header>
                <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
                  <Movelet moveletData={movelet} normalizedPose={true} />
                </div>
                <footer class="p-2">
                  <ul>
                    <li>Time: {formatSeconds(movelet.start_frame / $currentVideo.fps)}</li>
                    <li>Distance: {movelet.distance?.toFixed(2)}</li>
                  </ul>
                </footer>
              </div>
            {/if}
          {/each}
        </div>
        <div class="hide-paginator-label flex items-baseline"><span>Similar movelets</span>
          <Paginator
            bind:settings={simPager}
            showFirstLastButtons="{false}"
            showPreviousNextButtons="{true}"
            amountText="Poses"
          />
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
  