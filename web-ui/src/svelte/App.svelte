<script lang="ts">
  import { AppShell } from "@skeletonlabs/skeleton";
  import { AppBar } from "@skeletonlabs/skeleton";

  import VideosTable from "@svelte/VideosTable.svelte";
  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import FrameViewer from "@svelte/FrameViewer.svelte";
  import Icon from "@svelte/Icon.svelte";
  import { currentVideo, currentFrame } from "@svelte/stores";

  import { baseTitle } from "@/site-metadata.json";
  const base = import.meta.env.BASE_URL;

  $: $currentVideo, ($currentFrame = undefined);
</script>

<AppShell>
  <svelte:fragment slot="header">
    <AppBar slotTrail="place-content-end">
      <header>
        <h1><a href={base}>{baseTitle}</a></h1>
      </header>
      <svelte:fragment slot="trail">
        <a href="https://github.com/sul-cidr/mime">
          <Icon name="github" height="24" width="24" />
        </a>

        <a href={`${base}api/docs`}>
          <Icon name="book-2" height="24" width="24" />
        </a>

        <a href={`${base}api/redoc`}>
          <Icon name="notebook" height="24" width="24" />
        </a>
      </svelte:fragment>
    </AppBar>
  </svelte:fragment>

  <section class="m-8 flex flex-col gap-10">
    <VideosTable />
    {#if $currentVideo}
      <h2>{$currentVideo.video_name}</h2>
      <PosesByFrameChart videoId={$currentVideo.id} />
    {/if}
    {#if $currentFrame}
      <FrameViewer />
    {/if}
  </section>
</AppShell>
