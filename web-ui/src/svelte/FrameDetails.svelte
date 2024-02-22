<script lang="ts">
  import {
    currentVideo,
    currentFrame,
    currentPose,
    currentMoveletPose,
    maxDistances,
  } from "@svelte/stores";
  import { formatSeconds } from "@utils";
  import Icon from "@svelte/Icon.svelte";

  export let poses: Array<PoseRecord>;
  export let trackCt: number;
  export let faceCt: number;
  export let hoveredPoseIdx: number | undefined;
  export let shot: number | 0;
  export let interest: number | 0;
</script>

<div class="card variant-ghost-secondary w-full">
  <header class="card-header font-bold">
    <h3>Details for frame #{$currentFrame}</h3>
  </header>
  <div class="flex">
    <dl class="grid grid-cols-2 gap-2 p-4 [&>dt]:font-bold w-2/3">
      <dt>#Tracked Poses:</dt>
      <dd>{trackCt}</dd>
      <dt>#Detected Faces:</dt>
      <dd>{faceCt}</dd>
      <dt>Time:</dt>
      <dd>{formatSeconds(($currentFrame || 0) / $currentVideo.fps)}</dd>
      <dt>Shot:</dt>
      <dd>{shot}</dd>
      <dt>Interest:</dt>
      <dd>{(interest * 100).toFixed(2)}%</dd>
    </dl>

    <div class="grid w-1/3 gap-2 p-4">
      <h4>Max search distances</h4>
      <div class="flex justify-between">
        Cosine (.01-.1)
        <label>
          <input
            type="number"
            name="max-cosine-distance"
            bind:value={$maxDistances["cosine"]}
            size="4"
            min=".01"
            max=".1"
            step=".01"
          />
        </label>
      </div>
      <div class="flex justify-between">
        Euclidean (1-100)
        <label>
          <input
            type="number"
            name="max-euclidean-distance"
            bind:value={$maxDistances["euclidean"]}
            size="4"
            min="1"
            max="100"
            step="1"
          />
        </label>
      </div>
      <div class="flex justify-between">
        View-invariant (.01-.1)
        <label>
          <input
            type="number"
            name="max-invarian-distance"
            bind:value={$maxDistances["view_invariant"]}
            size="4"
            min=".01"
            max=".1"
            step=".01"
          />
        </label>
      </div>
    </div>
  </div>

  <div class="p-4 w-full">
    <ul>
      {#each poses as pose, i}
        <!-- svelte-ignore a11y-mouse-events-have-key-events -->
        <li
          class="px-4 py-1 flex items-center gap-2 justify-between cursor-pointer"
          class:variant-ghost={hoveredPoseIdx === i}
          on:mouseover={() => (hoveredPoseIdx = i)}
          on:mouseout={() => (hoveredPoseIdx = undefined)}
        >
          Pose #{i + 1} | Confidence: {pose.score.toFixed(3)}
          {#if pose.track_id !== null}
            | Track {pose.track_id}
          {/if}
          <div class="flex align-stretch gap-2">
            <button
              class="button px-2 variant-filled"
              on:click={() => {
                $currentPose = pose;
              }}
            >
              sim pose
            </button>
            {#if pose.track_id !== null}
              <button
                class="button px-2 variant-filled"
                on:click={() => {
                  $currentMoveletPose = pose;
                }}
              >
                sim movelet
              </button>
            {/if}
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
</div>
