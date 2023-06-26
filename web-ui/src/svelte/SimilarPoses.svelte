<script lang="ts">
  import { Paginator, RadioGroup, RadioItem, SlideToggle } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas, Html } from "layercake";
  import Pose from "@svelte/Pose.svelte";
  import { formatSeconds } from "../lib/utils";

  import { API_BASE } from "@config";
  import { currentPose, currentVideo } from "@svelte/stores";

  let showFrame: boolean = false;
  export let similarityMetric = "cosine";
  let poses: Array<PoseRecord>;

  const simStep = 5;
  let simPager = {
	  offset: 0,
	  limit: simStep,
	  size: 50,
    amounts: [simStep]
  };

  const updatePoseData = (data: Array<PoseRecord>) => {poses = data; simPager.size=poses.length};

  async function getPoseData(
    videoId: number,
    frame: number,
    poseIdx: number,
    similarityMetric: string,
  ) {
    const response = await fetch(
      `${API_BASE}/poses/similar/${similarityMetric}/${videoId}/${frame}/${poseIdx}`,
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


  $: getPoseData(
    $currentPose.video_id,
    $currentPose.frame,
    $currentPose.pose_idx,
    similarityMetric,
  ).then((data) => updatePoseData(data));
</script>

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
    <SlideToggle name="slider-label" bind:checked={showFrame} size="sm">
      Show Image
    </SlideToggle>
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
              <img class="object-contain h-full w-full"
              src={`${API_BASE}/frame/resize/${$currentPose.video_id}/${$currentPose.frame}/${getExtent($currentPose.keypoints).join(",")}|${getNormDims($currentPose.norm).join(",")}`}
              alt={`Frame ${$currentPose.frame}, Pose: ${$currentPose.pose_idx + 1}`}
              />
            </Html>
          {/if}
            <Canvas zIndex={1}>
              <Pose poseData={$currentPose.norm} normalizedPose={true} />
            </Canvas>
          </LayerCake>
        </div>
        <footer class="p-2">
          <ul>
            <li>
              Time: {formatSeconds($currentPose.frame / $currentVideo.fps)}
            </li>
          </ul>
        </footer>
      </div>

      <span class="divider-vertical !border-l-8 !border-double" />

      {#each poses as pose, p}
        {#if p >= (simPager.offset * simPager.limit) && p < (simPager.offset * simPager.limit) + simPager.limit}
          <div class="card drop-shadow-lg">
            <header class="p-2">
              Frame {pose.frame}, Pose: {pose.pose_idx + 1}
            </header>
            <div class="w-full aspect-[5/6] frame-display py-[30px] px-[10px]">
              <LayerCake>
                {#if showFrame}
                  <Html zIndex={0}>
                    <img class="object-contain h-full w-full"
                    src={`${API_BASE}/frame/resize/${pose.video_id}/${pose.frame}/${getExtent(pose.keypoints).join(",")}|${getNormDims(pose.norm).join(",")}`}
                    alt={`Frame ${pose.frame}, Pose: ${pose.pose_idx + 1}`}
                    />
                  </Html>
                {/if}
                <Canvas zIndex={1}>
                  <Pose poseData={pose.norm} normalizedPose={true} />
                </Canvas>
              </LayerCake>
            </div>
            <footer class="p-2">
              <ul>
                <li>Time: {formatSeconds(pose.frame / $currentVideo.fps)}</li>
                <li>Distance: {pose.distance?.toFixed(2)}</li>
              </ul>
            </footer>
          </div>
        {/if}
      {/each}
    </div>
    <div class="hide-paginator-label flex items-baseline"><span>Similar poses</span>
      <Paginator
        bind:settings={simPager}
        showFirstLastButtons="{false}"
        showPreviousNextButtons="{true}"
        amountText="Poses"
      />
    </div>
  {/if}
</section>

<style>
  .frame-display {
    background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
    box-shadow: inset 0px 0px 30px 0px #666;
  }
</style>
