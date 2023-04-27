<script lang="ts">
  import { AppShell } from "@skeletonlabs/skeleton";
  import { AppBar } from "@skeletonlabs/skeleton";

  import VideosTable from "@svelte/VideosTable.svelte";
  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import FrameViewer from "@svelte/FrameViewer.svelte";
  import { currentVideo, currentFrame } from "@svelte/stores";

  import { baseTitle } from "@/site-metadata.json";
  const base = import.meta.env.BASE_URL;

  $: console.log($currentVideo);
</script>

<AppShell>
  <svelte:fragment slot="header">
    <AppBar>
      <header>
        <h1><a href={base}>{baseTitle}</a></h1>
      </header>
    </AppBar>
  </svelte:fragment>

  <section class="m-8 flex flex-col gap-10">
    <VideosTable />
    {#if $currentVideo}
      <h2>{$currentVideo.video_name}</h2>
      <PosesByFrameChart videoId={$currentVideo.id} />
    {/if}
    {#if $currentFrame}
      <FrameViewer
        videoId={$currentVideo.id}
        frameNumber={$currentFrame}
        frameHeight={$currentVideo.height}
        frameWidth={$currentVideo.width}
      />
    {/if}
  </section>
</AppShell>
