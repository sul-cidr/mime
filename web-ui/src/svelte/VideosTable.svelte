<script lang="ts">
  import { onMount } from "svelte";
  import { ProgressBar, Table } from "@skeletonlabs/skeleton";
  import type { TableSource } from "@skeletonlabs/skeleton";

  import { videoTableData, currentVideo, similarPoseFrames, similarMoveletFrames } from "@svelte/stores";

  import { API_BASE } from "@config";

  import Icon from "@svelte/Icon.svelte";

  let videoTableSource: TableSource | void;

  async function getVideos() {

    if ($videoTableData) return $videoTableData;

    const response = await (await fetch(`${API_BASE}/videos/`)).json();
    $videoTableData = response;
    return response;
  }

  const updateVideoData = (): Promise<TableSource | void> => {
    return getVideos()
      .then((data) => ({
        head: ["", "Name", "Meta", "Frame Count", "Pose Count", "Poses/Frame", "Face Count", "Tracked Poses"],
        body: data.videos.map((video: VideoRecord) => [
          (video.video_name === $currentVideo?.video_name ? "⮕" : " "),
          video.video_name,
          `${video.width}x${video.height}@${video.fps.toFixed(2)}fps`,
          video.frame_count,
          video.pose_ct,
          video.poses_per_frame,
          video.face_ct,
          video.track_ct,
        ]),
        // Passed to the `on:selected` handler:
        meta: data.videos.map((video: VideoRecord) => video),
        // foot: [...],
      }))
      .catch((error) => error);
    };

  const highlightVideoRow = (video: VideoRecord) => {
    if (video === undefined || document === undefined) return;

    const allTrs = document.querySelectorAll('tr');
    allTrs.forEach((tr) => { tr.classList.remove("table-row-checked");
                             const unselectedTd = tr.querySelector('td[tabindex="0"]');
                             if (unselectedTd) unselectedTd.textContent = " ";  
                           });
    const allTds = document.querySelectorAll('td');
    const selectedTd = Array.from(allTds).find(td => td.textContent === video.video_name);
    const selectedTr = selectedTd?.parentElement;
    selectedTr?.classList.add("table-row-checked");
    const bulletTd = selectedTr?.querySelector('td[tabindex="0"]');
    if (bulletTd) {
      bulletTd.textContent = "⮕";
    }
  }

  const selectVideoHandler = ({ detail: video }: { detail: VideoRecord }) => {
    $currentVideo = video;
    highlightVideoRow(video);
    // $currentPose = null;
    // $currentMovelet = null;
    $similarPoseFrames = {};
    $similarMoveletFrames = {};
  };

  onMount(async () => {
    videoTableSource = await updateVideoData();
  });

  $: highlightVideoRow($currentVideo);

</script>

{#if videoTableSource !== undefined && !(videoTableSource instanceof Error)}
  <Table
    source={videoTableSource}
    interactive={true}
    on:selected={selectVideoHandler}
  />
  {#if videoTableSource.body.length === 0}
    <div class="alert variant-ghost-warning -mt-8">
      <Icon
        name="alert-triangle"
        height="24px"
        width="24px"
        class="self-center mr-4"
      />
      No videos available. Please load some videos into the system using the CLI.
    </div>
  {/if}
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
