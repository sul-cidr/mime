<script lang="ts">
  import { onMount } from "svelte";
  import { ProgressBar, Table } from "@skeletonlabs/skeleton";
  import type { TableSource } from "@skeletonlabs/skeleton";

  import { currentVideo } from "@svelte/stores";
  import type { VideoRecord } from "@svelte/stores";

  import { API_BASE } from "@config";

  let videoTableSource: TableSource;

  async function getVideos() {
    const response = await fetch(`${API_BASE}/videos/`);
    return await response.json();
  }

  const updateVideoData = (): Promise<TableSource> =>
    getVideos().then((data) => ({
      head: ["Name", "Meta", "Frame Count"],
      body: data.videos.map((video: VideoRecord) => [
        video.video_name,
        `${video.width}x${video.height}@${video.fps}fps`,
        video.frame_count,
      ]),
      // Passed to the `on:selected` handler:
      meta: data.videos.map((video: VideoRecord) => video),
      // foot: [...],
    }));

  const selectVideoHandler = ({ detail: video }: { detail: VideoRecord }) => {
    $currentVideo = video;
  };

  onMount(async () => {
    videoTableSource = await updateVideoData();
  });
</script>

{#if videoTableSource}
  <Table
    source={videoTableSource}
    interactive={true}
    on:selected={selectVideoHandler}
  />
{:else}
  <p>Initializing database and fetching videos...</p>
  <ProgressBar />
{/if}
