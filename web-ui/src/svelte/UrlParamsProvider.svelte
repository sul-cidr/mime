<script lang="ts">
  import { currentPose, currentVideo } from "@svelte/stores";
  import { API_BASE } from "@config";

  const loadDataFromParams = async () => {
    const urlParams = Object.fromEntries(
      new URLSearchParams(window.location.search),
    );

    const { videos } = await (await fetch(`${API_BASE}/videos/`)).json();
    $currentVideo = videos.find((v) => v.id === urlParams.video);

    const poses = await (
      await fetch(`${API_BASE}/poses/${$currentVideo.id}/${urlParams.frame}/`)
    ).json();
    $currentPose = poses[urlParams.pose];
  };
</script>

{#await loadDataFromParams()}
  <p>loading data...</p>
{:then}
  <slot />
{/await}
