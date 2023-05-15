<script lang="ts">
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import Icon from "@svelte/Icon.svelte";
  import { API_BASE } from "@config";

  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import PoseDataFilters from "@/src/svelte/PoseDataFilters.svelte";

  export let videoId: Number;
  let data: Array<FrameRecord> | undefined;
  let filteredData: Array<FrameRecord>;

  let showFilters = false;

  async function getPoseData(videoId: Number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/`);
    return await response.json();
  }

  $: {
    data = undefined;
    getPoseData(videoId).then((_data) => (data = filteredData = _data));
  }
</script>

{#if data}
  <div class="variant-ringed-primary flex flex-col">
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
  <PosesByFrameChart data={filteredData} />
{:else}
  Loading pose data... <ProgressBar />
{/if}
