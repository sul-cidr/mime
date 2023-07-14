<script lang="ts">
  import { AppShell } from "@skeletonlabs/skeleton";
  import { AppBar } from "@skeletonlabs/skeleton";

  import VideosTable from "@svelte/VideosTable.svelte";
  import PoseDataExplorer from "@svelte/PoseDataExplorer.svelte";
  import FrameViewer from "@svelte/FrameViewer.svelte";
  import SimilarMovelets from "@svelte/SimilarMovelets.svelte";
  import SimilarPoses from "@svelte/SimilarPoses.svelte";
  import Icon from "@svelte/Icon.svelte";
  import { currentVideo, currentFrame, currentPose, similarPoseFrames, similarMoveletFrames, currentMoveletPose } from "@svelte/stores";
  import { tooltip } from "@svelte/actions/tooltip";

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
        <a
          href={`${base}jupyter/notebooks/notebooks/video_posedata_explorer.ipynb`}
          use:tooltip={"PoseData Explorer Notebook"}
        >
          <Icon name="file-analytics" height="24" width="24" />
        </a>

        <a href={`${base}jupyter/tree/notebooks`} use:tooltip={"Jupyter"}>
          <Icon name="jupyter" height="24" width="24" />
        </a>

        <a href={`${base}api/docs`} use:tooltip={"Swagger API docs"}>
          <Icon name="book-2" height="24" width="24" />
        </a>

        <a href={`${base}api/redoc`} use:tooltip={"ReDoc API docs"}>
          <Icon name="notebook" height="24" width="24" />
        </a>

        <a href="https://github.com/sul-cidr/mime" use:tooltip={"GitHub"}>
          <Icon name="github" height="24" width="24" />
        </a>
      </svelte:fragment>
    </AppBar>
  </svelte:fragment>

  <section class="m-8 flex flex-col gap-10">
    <VideosTable />
    {#if $currentVideo}
      <h2>{$currentVideo.video_name}</h2>
      <PoseDataExplorer videoId={$currentVideo.id} />
    {/if}
    {#if $currentFrame}
      <FrameViewer />
    {/if}
    {#if $similarMoveletFrames && $currentMoveletPose}
      <SimilarMovelets />
    {/if}
    {#if $similarPoseFrames && $currentPose}
      <SimilarPoses />
    {/if}
  </section>
</AppShell>
