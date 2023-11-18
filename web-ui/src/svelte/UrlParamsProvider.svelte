<script lang="ts">
  import { currentPose, currentVideo } from "@svelte/stores";
  import { API_BASE } from "@config";

  const urlParams = Object.fromEntries(
    new URLSearchParams(window.location.search),
  );

  const loadDataFromParams = async () => {
    const { videos } = await (await fetch(`${API_BASE}/videos/`)).json();
    $currentVideo = videos.find((v) => v.id === urlParams.video);

    const poses = await (
      await fetch(`${API_BASE}/poses/${$currentVideo.id}/${urlParams.frame}/`)
    ).json();
    $currentPose = poses[urlParams.pose - 1];
  };
</script>

{#await loadDataFromParams()}
  <p>loading data...</p>
{:then}
  {#if $currentVideo && $currentPose}
    <slot />
  {:else}
    <p>
      Can't find pose #{urlParams.pose - 1} in frame #{urlParams.frame} of video
      {urlParams.video}
    </p>
  {/if}
{/await}
