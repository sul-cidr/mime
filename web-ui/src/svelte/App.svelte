<script lang="ts">
  import {
    AppBar,
    AppShell,
    Modal,
    modalStore,
    Tab,
    TabGroup,
  } from "@skeletonlabs/skeleton";
  import CameraPoseInput from "@svelte/CameraPoseInput.svelte";
  import Input3DModal from "@svelte/Input3DModal.svelte";
  import VideosTable from "@svelte/VideosTable.svelte";
  import PoseDataExplorer from "@svelte/PoseDataExplorer.svelte";
  import FacesTimeline from "@svelte/FacesTimeline.svelte";
  import FrameViewer from "@svelte/FrameViewer.svelte";
  import PosesTimeline from "./PosesTimeline.svelte";
  import SimilarActions from "@svelte/SimilarActions.svelte";
  import SimilarPoses from "@svelte/SimilarPoses.svelte";
  import Icon from "@svelte/Icon.svelte";
  import {
    currentVideo,
    currentFrame,
    currentPose,
    similarPoseFrames,
    similarActionFrames,
    currentActionPose,
  } from "@svelte/stores";
  import { tooltip } from "@svelte/actions/tooltip";

  import { baseTitle } from "@/site-metadata.json";
  const base = import.meta.env.BASE_URL;

  let tabSet: number = 0;

  let poseplotFrame = "";

  let modalActive = false;

  // ??? Importing ModalComponent and ModalSettings the usual way causes an
  // "ambiguous indirect export" syntax error, but the app somehow works fine
  // without the imports, so...

  const cameraModalComponent: ModalComponent = {
    // Pass a reference to your custom component
    ref: CameraPoseInput,
    // Provide a template literal for the default component slot
    slot: "<p>Camera Search</p>",
  };

  const input3DModalComponent: ModalComponent = {
    // Pass a reference to your custom component
    ref: Input3DModal,
    // Provide a template literal for the default component slot
    slot: "<p>Sketch Search</p>",
  };

  const cameraModal: ModalSettings = {
    type: "component",
    title: "Use the camera to search for a pose",
    modalClasses: "w-modal",
    component: cameraModalComponent,
    background: "bg-surface-100-800-token",
    buttonTextCancel: "Cancel",
  };

  const input3DModal: ModalSettings = {
    type: "component",
    title: "Manipulate a stick-figure pose in 3D to search",
    modalClasses: "w-modal",
    component: input3DModalComponent,
    background: "gray",
    buttonTextCancel: "Cancel",
  };

  const toggleCameraPoseModal = () => {
    if (modalActive) modalStore.close();
    else modalStore.trigger(cameraModal);
  };

  const toggle3DPoseModal = () => {
    if (modalActive) modalStore.close();
    else modalStore.trigger(input3DModal);
  };

  $: poseplotFrame = `<iframe src="/poseplot/${$currentVideo?.video_name}/index.html" width="100%" height="1200px" title="Pose Cluster Explorer" />`;
</script>

<Modal />

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
          target="_blank"
        >
          <Icon name="file-analytics" height="24" width="24" />
        </a>

        <a
          href={`${base}jupyter/tree/notebooks`}
          use:tooltip={"Jupyter"}
          target="_blank"
        >
          <Icon name="jupyter" height="24" width="24" />
        </a>

        <a
          href={`${base}api/docs`}
          use:tooltip={"Swagger API docs"}
          target="_blank"
        >
          <Icon name="book-2" height="24" width="24" />
        </a>

        <a
          href={`${base}api/redoc`}
          use:tooltip={"ReDoc API docs"}
          target="_blank"
        >
          <Icon name="notebook" height="24" width="24" />
        </a>

        <a
          href="https://github.com/sul-cidr/mime"
          use:tooltip={"GitHub"}
          target="_blank"
        >
          <Icon name="github" height="24" width="24" />
        </a>
      </svelte:fragment>
    </AppBar>
  </svelte:fragment>

  <section class="m-8 flex flex-col gap-10">
    <TabGroup
      justify="justify-left"
      active="variant-filled-primary"
      hover="hover:variant-soft-primary"
      flex="flex-1 lg:flex-none"
      rounded=""
      border=""
      class="bg-surface-100-800-token w-full"
    >
      <Tab bind:group={tabSet} name="tab1" value={0}>Performances</Tab>
      <Tab
        bind:group={tabSet}
        name="tab2"
        value={1}
        class={$currentVideo ? "opacity-100" : "opacity-50"}>Timeline</Tab
      >
      <Tab
        bind:group={tabSet}
        name="tab3"
        value={2}
        class={$currentVideo ? "opacity-100" : "opacity-50"}>Poses</Tab
      >
      <Tab
        bind:group={tabSet}
        name="tab4"
        value={3}
        class={$currentVideo ? "opacity-100" : "opacity-50"}>Faces</Tab
      >
      <Tab
        bind:group={tabSet}
        name="tab5"
        value={4}
        class={$currentVideo ? "opacity-100" : "opacity-50"}>Explorer</Tab
      >

      <svelte:fragment slot="panel">
        {#if tabSet === 0}
          <VideosTable />
        {:else if tabSet === 1}
          {#if $currentVideo}
            <h2>{$currentVideo.video_name}</h2>
            <PoseDataExplorer
              videoId={$currentVideo.id}
              {toggleCameraPoseModal}
              {toggle3DPoseModal}
            />
            {#if $currentFrame}
              <FrameViewer />
            {/if}
            {#if $similarActionFrames && $currentActionPose}
              <SimilarActions />
            {/if}
            {#if $similarPoseFrames && $currentPose}
              <SimilarPoses {toggle3DPoseModal} />
            {/if}
          {/if}
        {:else if tabSet === 2}
          {#if $currentVideo}
            <h2>{$currentVideo.video_name}</h2>
            <PosesTimeline
              videoId={$currentVideo.id}
              videoName={$currentVideo.video_name}
            />
            {#if $currentFrame}
              <FrameViewer />
            {/if}
            {#if $similarActionFrames && $currentActionPose}
              <SimilarActions />
            {/if}
            {#if $similarPoseFrames && $currentPose}
              <SimilarPoses />
            {/if}
          {/if}
        {:else if tabSet === 3}
          {#if $currentVideo}
            <h2>{$currentVideo.video_name}</h2>
            <FacesTimeline
              videoId={$currentVideo.id}
              videoName={$currentVideo.video_name}
            />
            {#if $currentFrame}
              <FrameViewer />
            {/if}
            {#if $similarActionFrames && $currentActionPose}
              <SimilarActions />
            {/if}
            {#if $similarPoseFrames && $currentPose}
              <SimilarPoses />
            {/if}
          {/if}
        {:else if tabSet === 4}
          {#if $currentVideo}
            <h2>{$currentVideo.video_name}</h2>
            <div>{@html poseplotFrame}</div>
          {/if}
        {/if}
      </svelte:fragment>
    </TabGroup>
  </section>
</AppShell>
