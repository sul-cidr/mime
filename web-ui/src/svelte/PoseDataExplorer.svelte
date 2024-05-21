<script lang="ts">
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import Icon from "@svelte/Icon.svelte";
  import { API_BASE } from "@config";
  import { formatSeconds } from "@utils";

  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import PoseDataFilters from "@/src/svelte/PoseDataFilters.svelte";
  import { currentVideo } from "@svelte/stores";

  export let videoId: string;
  export let toggleCameraPoseModal;
  export let toggle3DPoseModal;

  let data: Array<FrameRecord> | undefined;
  let filteredData: Array<FrameRecord>;

  let showFilters = false;

  async function getPoseData(videoId: string) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/`);
    return await response.json();
  }

  const updatePoseData = (_data: Array<FrameRecord>) => {
    data = filteredData = _data;
    filteredData.forEach((frame) => {
      frame.time = formatSeconds(frame.frame / $currentVideo.fps);
    });
  };

  $: {
    getPoseData(videoId).then((_data) => updatePoseData(_data));
  }
</script>

{#if data}
  <div class="flex flex-row">
    <div class="variant-ringed-primary flex flex-col flex-1">
      <button
        class="flex items-center gap-2 p-2 hover:bg-primary-hover-token"
        class:mb-2={showFilters}
        on:click={() => (showFilters = !showFilters)}
      >
        <Icon name="filter" />
        <span class="grow text-left">Filters</span>
        {#if showFilters}
          <Icon name="chevron-up" />
        {:else}
          <Icon name="chevron-down" />
        {/if}
      </button>
      <div
        class="overflow-hidden h-0 pt-0"
        class:h-full={showFilters}
        class:p-2={showFilters}
      >
        <PoseDataFilters {data} bind:filteredData />
      </div>
    </div>
    <div class="flex">
      <button
        type="button"
        class="btn-sm px-2 variant-ghost"
        on:click={toggle3DPoseModal}>Search by sketch</button
      >
    </div>
    <div class="flex">
      <button
        type="button"
        class="btn-sm px-2 variant-ghost"
        on:click={toggleCameraPoseModal}>Search by camera</button
      >
    </div>
  </div>
  <PosesByFrameChart timelineData={filteredData} />
{:else}
  Loading pose data... <ProgressBar />
  <section class="card w-full">
    <div class="p-4 space-y-4">
      <div class="placeholder h-96 animate-pulse" />
      <div class="placeholder h-28 animate-pulse" />
    </div>
  </section>
{/if}
