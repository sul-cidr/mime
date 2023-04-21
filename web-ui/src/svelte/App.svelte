<script lang="ts">
  import { AppShell } from "@skeletonlabs/skeleton";
  import { AppBar } from "@skeletonlabs/skeleton";

  import VideosTable from "@svelte/VideosTable.svelte";
  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import { videoId, videoTitle } from "@svelte/stores";

  import { baseTitle } from "@/site-metadata.json";
  const base = import.meta.env.BASE_URL;
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
    {#if $videoId}
      <h2>{$videoTitle}</h2>
      <PosesByFrameChart videoId={$videoId} />
    {/if}
  </section>
</AppShell>
