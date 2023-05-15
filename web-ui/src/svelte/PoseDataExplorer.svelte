<script lang="ts">
  import {
    Accordion,
    AccordionItem,
    ProgressBar,
  } from "@skeletonlabs/skeleton";
  import Icon from "@svelte/Icon.svelte";
  import { API_BASE } from "@config";

  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import PoseDataFilters from "@/src/svelte/PoseDataFilters.svelte";

  export let videoId: Number;
  let data: Array<FrameRecord> | undefined;
  let filteredData: Array<FrameRecord>;

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
  <Accordion class="variant-ringed-primary">
    <AccordionItem open>
      <svelte:fragment slot="lead"><Icon name="filter" /></svelte:fragment>
      <svelte:fragment slot="summary">Filters</svelte:fragment>
      <svelte:fragment slot="content">
        <PoseDataFilters {data} bind:filteredData />
      </svelte:fragment>
    </AccordionItem>
  </Accordion>
  <PosesByFrameChart data={filteredData} />
{:else}
  Loading pose data... <ProgressBar />
{/if}
