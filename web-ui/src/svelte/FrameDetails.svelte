<script lang="ts">
  import { SlideToggle } from "@skeletonlabs/skeleton";
  import {
    currentVideo,
    currentFrame,
    currentPose,
    currentActionPose,
    searchAllVideos,
    searchThresholds,
  } from "@svelte/stores";
  import { formatSeconds } from "@utils";
  import Icon from "@svelte/Icon.svelte";

  export let poses: Array<PoseRecord>;
  export let trackCt: number;
  export let faceCt: number;
  export let hoveredPoseIdx: number | undefined;
  export let shot: number | 0;
  export let pose_interest: number | 0;
  export let action_interest: number | 0;

  let showSearchSettings = false;

  const updateSearchThresholds = (event) => {
    const input = event.target.form.querySelectorAll("input");
    input.forEach((item: HTMLInputElement) => {
      $searchThresholds[item.name] = parseFloat(item.value);
    });
  };
</script>

<div class="card variant-ghost-secondary w-full">
  <header class="card-header font-bold">
    <h3>Details for frame #{$currentFrame}</h3>
  </header>
  <div class="flex">
    <div class="flex flex-col w-2/3">
      <dl class="grid grid-cols-2 gap-1 p-4 [&>dt]:font-bold">
        <dt>#Tracked Poses:</dt>
        <dd>{trackCt}</dd>
        <dt>#Detected Faces:</dt>
        <dd>{faceCt}</dd>
        <dt>Time:</dt>
        <dd>{formatSeconds(($currentFrame || 0) / $currentVideo.fps)}</dd>
        <dt>Shot:</dt>
        <dd>{shot}</dd>
        {#if pose_interest}
          <dt>Avg pose interest:</dt>
          <dd>{(pose_interest * 100).toFixed(2)}%</dd>
        {/if}
        {#if action_interest}
          <dt>Avg action interest:</dt>
          <dd>{(action_interest * 100).toFixed(2)}%</dd>
        {/if}
      </dl>
      <div class="flex pl-4">
        <SlideToggle
          name="search-all-toggle"
          bind:checked={$searchAllVideos}
          size="sm"
        >
          Search all videos
        </SlideToggle>
      </div>
    </div>
    {#if showSearchSettings}
      <div class="grid w-1/3 gap-1 p-4 search-settings">
        <form>
          <div class="flex justify-between search-options">
            Max matches [1-10000]
            <label>
              <input
                type="number"
                name="total_results"
                value={$searchThresholds["total_results"]}
                size="5"
                min="1"
                max="10000"
                step="10"
              />
            </label>
          </div>
          <p>Max distance thresholds:</p>
          <div class="flex justify-between search-options">
            Cosine [.01-.1]
            <label>
              <input
                type="number"
                name="cosine"
                value={$searchThresholds["cosine"]}
                size="4"
                min=".01"
                max=".1"
                step=".01"
              />
            </label>
          </div>
          <div class="flex justify-between search-options">
            Euclidean [1-100]
            <label>
              <input
                type="number"
                name="euclidean"
                value={$searchThresholds["euclidean"]}
                size="4"
                min="1"
                max="100"
                step="1"
              />
            </label>
          </div>
          <div class="flex justify-between search-options">
            2D+ Cosine [.01-.3]
            <label>
              <input
                type="number"
                name="view_invariant"
                value={$searchThresholds["view_invariant"]}
                size="4"
                min=".01"
                max=".3"
                step=".01"
              />
            </label>
          </div>
          <div class="flex justify-between search-options">
            3D Cosine [.01-.2]
            <label>
              <input
                type="number"
                name="global"
                value={$searchThresholds["global"]}
                size="4"
                min=".01"
                max=".2"
                step=".01"
              />
            </label>
          </div>
          <div class="flex flex-row justify-between">
            <div>
              <button
                type="button"
                class="btn-sm px-2 variant-ghost"
                on:click={updateSearchThresholds}>Apply</button
              >
            </div>
            <div>
              <button
                type="button"
                class="btn-sm px-2 variant-ghost"
                on:click={() => (showSearchSettings = false)}>Close</button
              >
            </div>
          </div>
        </form>
      </div>
    {:else}
      <div class="flex">
        <button
          type="button"
          class="btn px-2 py-2 variant-ghost h-fit"
          on:click={() => (showSearchSettings = true)}>Search settings</button
        >
      </div>
    {/if}
  </div>

  <div class="p-4 w-full">
    <ul>
      {#each poses as pose, i}
        <!-- svelte-ignore a11y-mouse-events-have-key-events -->
        <li
          class="py-1 px-2 flex items-center gap-2 justify-between cursor-pointer"
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
              similar poses
            </button>
            {#if pose.track_id !== null}
              <button
                class="button px-2 variant-filled"
                on:click={() => {
                  $currentActionPose = pose;
                }}
              >
                similar actions
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

<style>
  .search-settings {
    border: 1px solid black;
    margin-right: 1em;
  }
  .search-options {
    font-weight: bold;
  }
  .search-options label {
    font-weight: normal;
  }
</style>
