<script lang="ts">
  import { onMount } from "svelte";
  import { ProgressBar } from "@skeletonlabs/skeleton";
  import { API_BASE } from "@config";

  import PosesByFrameChart from "@svelte/PosesByFrameChart.svelte";

  export let videoId: Number;
  let data: Array<Object> | undefined;

  async function getPoseData(videoId: Number) {
    const response = await fetch(`${API_BASE}/poses/${videoId}/`);
    return await response.json();
  }

  onMount(async () => {
    data = await getPoseData(videoId);
  });

  $: {
    data = undefined;
    getPoseData(videoId).then((_data) => (data = _data));
  }
</script>

{#if data}
  <PosesByFrameChart {data} />
{:else}
  Loading pose data... <ProgressBar />
{/if}
