<script lang="ts">
  import { currentVideo, currentFrame, currentPose } from "@svelte/stores";
  import { formatSeconds } from "@utils";
  import Icon from "@svelte/Icon.svelte";

  export let poses: Array<PoseRecord>;
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

  <ul>
    {#each poses as pose, i}
      <!-- svelte-ignore a11y-mouse-events-have-key-events -->
      <li
        class="px-4 py-1 flex items-center gap-2 justify-between cursor-pointer"
        class:variant-ghost={hoveredPoseIdx === i}
        on:mouseover={() => (hoveredPoseIdx = i)}
        on:mouseout={() => (hoveredPoseIdx = undefined)}
      >
        Pose #{i + 1}. Confidence: {pose.score}
        <div class="flex align-stretch gap-2">
          <button
            class="button px-2 variant-filled"
            on:click={() => {
              // console.log(pose);
              $currentPose = pose;
            }}
          >
            similar
          </button>
          <button
            class="btn p-2"
            class:variant-filled={!pose.hidden}
            class:variant-ghost-primary={pose.hidden}
            on:click={() => {
              pose.hidden = !pose.hidden;
            }}
          >
            {#if pose.hidden}
              <Icon name="eye" />
            {:else}
              <Icon name="eye-off" />
            {/if}
          </button>
        </div>
      </li>
    {/each}
  </ul>
</div>
