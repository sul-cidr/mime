<script lang="ts">
  import { currentVideo, currentFrame } from "@svelte/stores";
  export let poses: Array<{ keypoints: Array<number> }>;
</script>

<div class="card variant-ghost-secondary p-4">
  <header class="card-header font-bold">
    <h3>Details for frame #{$currentFrame}</h3>
  </header>
  <dl class="w-96 grid grid-cols-2 gap-2 p-4 [&>dt]:font-bold">
    <dt># Poses:</dt>
    <dd>{poses.length}</dd>
    <dt>Time:</dt>
    <dd>{($currentFrame || 0) / $currentVideo.fps} seconds</dd>
  </dl>
</div>
