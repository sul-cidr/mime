<script lang="ts">
  import { SlideToggle } from "@skeletonlabs/skeleton";

  export let data: Array<FrameRecord>;
  export let filteredData;

  let filterByAvgScoreActive: boolean = false;
  let filterByAvgScoreMin: number = 0.5;
  let filterByAvgScoreMax: number = 1;

  let filterByTrackCountActive: boolean = false;
  let filterByTrackCountMin: number = 2;
  let filterByTrackCountMax: number = 15;

  const filterPoses = () => {
    filteredData = data;
    if (filterByAvgScoreActive) {
      filteredData = filteredData.map((p) => {
        if (
          p.avgScore >= filterByAvgScoreMin &&
          p.avgScore <= filterByAvgScoreMax
        ) {
          return p;
        }
        return { frame: p.frame, avgScore: 0, trackCt: 0, faceCt: 0 };
      });
    }
    if (filterByTrackCountActive) {
      filteredData = filteredData.map((p) => {
        if (
          p.trackCt >= filterByTrackCountMin &&
          p.trackCt <= filterByTrackCountMax
        ) {
          return p;
        }
        return { frame: p.frame, avgScore: 0, trackCt: 0, faceCt: 0 };
      });
    }
  };

  $: filterByAvgScoreActive,
    filterByAvgScoreMin,
    filterByAvgScoreMax,
    filterByTrackCountActive,
    filterByTrackCountMin,
    filterByTrackCountMax,
    filterPoses();
</script>

<div class="flex gap-4">
  <div class="card w-80" class:variant-ghost-primary={filterByAvgScoreActive}>
    <div class="flex items-center justify-between p-4">
      Filter by Avg. Score: <SlideToggle
        name="filter-by-avg-score-active"
        size="sm"
        bind:checked={filterByAvgScoreActive}
      />
    </div>
    <div class="flex">
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByAvgScoreActive}
      >
        Min:
        <input
          type="number"
          bind:value={filterByAvgScoreMin}
          disabled={!filterByAvgScoreActive}
          min="0"
          max={filterByAvgScoreMax}
          step="0.1"
          class="text-center w-16 ml-4"
        />
      </label>
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByAvgScoreActive}
      >
        Max:
        <input
          type="number"
          bind:value={filterByAvgScoreMax}
          disabled={!filterByAvgScoreActive}
          min={filterByAvgScoreMin}
          max="1"
          step="0.1"
          class="text-center w-16 ml-4"
        />
      </label>
    </div>
  </div>
  <div class="card w-80" class:variant-ghost-primary={filterByTrackCountActive}>
    <div class="flex items-center justify-between p-4">
      Filter by Track Count: <SlideToggle
        name="filter-by-avg-score-active"
        size="sm"
        bind:checked={filterByTrackCountActive}
      />
    </div>
    <div class="flex">
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByTrackCountActive}
      >
        Min:
        <input
          type="number"
          bind:value={filterByTrackCountMin}
          disabled={!filterByTrackCountActive}
          min="0"
          max={filterByTrackCountMax}
          step="1"
          class="text-center w-16 ml-4"
        />
      </label>
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByTrackCountActive}
      >
        Max:
        <input
          type="number"
          bind:value={filterByTrackCountMax}
          disabled={!filterByTrackCountActive}
          min={filterByTrackCountMin}
          max="15"
          step="1"
          class="text-center w-16 ml-4"
        />
      </label>
    </div>
  </div>
</div>
