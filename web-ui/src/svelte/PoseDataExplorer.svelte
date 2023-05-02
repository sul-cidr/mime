<script lang="ts">
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import { API_BASE } from "@config";

  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";
  import PoseDataFilters from "@/src/svelte/PoseDataFilters.svelte";

  export let videoId: Number;
  let data: Array<Object> | undefined;
  let filteredData: Array<Object> | undefined;

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
  <PosesByFrameChart data={filteredData} />
  <PoseDataFilters {data} bind:filteredData />
{:else}
  Loading pose data... <ProgressBar />
{/if}
