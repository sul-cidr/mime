<script lang="ts">
  import { RadioGroup, RadioItem } from "@skeletonlabs/skeleton";
  import { LayerCake, Canvas } from "layercake";
  import Pose from "@svelte/Pose.svelte";
  import { formatSeconds } from "../lib/utils";

  import { API_BASE } from "@config";
  import { currentPose, currentVideo } from "@svelte/stores";

  export let similarityMetric = "cosine";
  let poses: Array<PoseRecord>;

  const updatePoseData = (data: Array<PoseRecord>) => (poses = data);

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
  {#if poses}
    <div class="flex gap-4">
      <div class="card variant-ghost-tertiary drop-shadow-lg">
        <header class="p-2">
          Frame {$currentPose.frame}, Pose: {$currentPose.pose_idx + 1}
        </header>
        <div class="w-full aspect-[5/6] frame-display py-[20px] px-[10px]">
          <LayerCake>
            <!-- {#if showFrame}
        <Html zIndex={0}>
          <img
            src={`${API_BASE}/frame/${videoId}/${$currentFrame}/`}
            alt={`Frame ${$currentFrame}`}
          />
        </Html>
      {/if} -->
            <Canvas zIndex={1}>
              <Pose poseData={$currentPose.norm} scalePoseToCanvas={true} />
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

      {#each poses as pose}
        <div class="card drop-shadow-lg">
          <header class="p-2">
            Frame {pose.frame}, Pose: {pose.pose_idx + 1}
          </header>
          <div class="w-full aspect-[5/6] frame-display py-[20px] px-[10px]">
            <LayerCake>
              <!-- {#if showFrame}
        <Html zIndex={0}>
          <img
            src={`${API_BASE}/frame/${videoId}/${$currentFrame}/`}
            alt={`Frame ${$currentFrame}`}
          />
        </Html>
      {/if} -->
              <Canvas zIndex={1}>
                <Pose poseData={pose.norm} scalePoseToCanvas={true} />
              </Canvas>
            </LayerCake>
          </div>
          <footer class="p-2">
            <ul>
              <li>Time: {formatSeconds(pose.frame / $currentVideo.fps)}</li>
              <li>Similarity: {pose.distance.toFixed(2)}</li>
            </ul>
          </footer>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .frame-display {
    background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
    box-shadow: inset 0px 0px 30px 0px #666;
  }
</style>
