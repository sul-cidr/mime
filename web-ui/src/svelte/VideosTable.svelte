<script lang="ts">
  import { onMount } from "svelte";
  import { ProgressBar, Table } from "@skeletonlabs/skeleton";
  import type { TableSource } from "@skeletonlabs/skeleton";

  import { currentVideo } from "@svelte/stores";

  import { API_BASE } from "@config";

  import Icon from "@svelte/Icon.svelte";

  let videoTableSource: TableSource | void;

  async function getVideos() {
    const response = await fetch(`${API_BASE}/videos/`);
    return await response.json();
  }

  const updateVideoData = (): Promise<TableSource | void> =>
    getVideos()
      .then((data) => ({
        head: ["Name", "Meta", "Frame Count"],
        body: data.videos.map((video: VideoRecord) => [
          video.video_name,
          `${video.width}x${video.height}@${video.fps}fps`,
          video.frame_count,
        ]),
        // Passed to the `on:selected` handler:
        meta: data.videos.map((video: VideoRecord) => video),
        // foot: [...],
      }))
      .catch((error) => error);

  const selectVideoHandler = ({ detail: video }: { detail: VideoRecord }) => {
    $currentVideo = video;
  };

  onMount(async () => {
    videoTableSource = await updateVideoData();
  });
</script>

{#if videoTableSource !== undefined && !(videoTableSource instanceof Error)}
  <Table
    source={videoTableSource}
    interactive={true}
    on:selected={selectVideoHandler}
  />
{:else if videoTableSource instanceof Error}
  <div class="alert variant-filled-error flex items-baseline">
    <Icon
      name="alert-triangle"
      height="24px"
      width="24px"
      class="self-center mr-4"
    />
    Error fetching data from API server:
    <span class="font-mono">{videoTableSource.message}</span>
  </div>
{:else}
  <p>Initializing database and fetching videos...</p>
  <ProgressBar />
{/if}
