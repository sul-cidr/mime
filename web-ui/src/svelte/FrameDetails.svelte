<script lang="ts">
  import { currentVideo, currentFrame } from "@svelte/stores";
  import { formatSeconds } from "../lib/utils";
  export let poses: Array<PoseData>;
  export let hoveredPoseIdx: number | undefined;
</script>

<div class="card variant-ghost-secondary p-4 w-full">
  <header class="card-header font-bold">
    <h3>Details for frame #{$currentFrame}</h3>
  </header>
  <dl class="grid grid-cols-2 gap-2 p-4 [&>dt]:font-bold">
    <dt>#Poses:</dt>
    <dd>{poses.length}</dd>
    <dt>Time:</dt>
    <dd>{formatSeconds(($currentFrame || 0) / $currentVideo.fps)}</dd>
  </dl>

  {#each poses as pose, i}
    <!-- svelte-ignore a11y-mouse-events-have-key-events -->
    <p
      class="px-4 py-1"
      class:font-bold={hoveredPoseIdx === i}
      on:mouseover={() => (hoveredPoseIdx = i)}
      on:mouseout={() => (hoveredPoseIdx = undefined)}
    >
      Pose #{i + 1}. Confidence: {pose.score}
    </p>
  {/each}
</div>