<script lang="ts">
  import { SlideToggle } from "@skeletonlabs/skeleton";

  export let data: Array<FrameRecord>;
  export let filteredData;

  let filterByAvgScoreActive: boolean = false;
  let filterByAvgScoreMin: number = 0.5;
  let filterByAvgScoreMax: number = 1;

  let filterByPoseCountActive: boolean = false;
  let filterByPoseCountMin: number = 2;
  let filterByPoseCountMax: number = 15;

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
        return { frame: p.frame, avgScore: 0, poseCt: 0 };
      });
    }
    if (filterByPoseCountActive) {
      filteredData = filteredData.map((p) => {
        if (
          p.poseCt >= filterByPoseCountMin &&
          p.poseCt <= filterByPoseCountMax
        ) {
          return p;
        }
        return { frame: p.frame, avgScore: 0, poseCt: 0 };
      });
    }
  };

  $: filterByAvgScoreActive,
    filterByAvgScoreMin,
    filterByAvgScoreMax,
    filterByPoseCountActive,
    filterByPoseCountMin,
    filterByPoseCountMax,
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
  <div class="card w-80" class:variant-ghost-primary={filterByPoseCountActive}>
    <div class="flex items-center justify-between p-4">
      Filter by Pose Count: <SlideToggle
        name="filter-by-avg-score-active"
        size="sm"
        bind:checked={filterByPoseCountActive}
      />
    </div>
    <div class="flex">
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByPoseCountActive}
      >
        Min:
        <input
          type="number"
          bind:value={filterByPoseCountMin}
          disabled={!filterByPoseCountActive}
          min="0"
          max={filterByPoseCountMax}
          step="1"
          class="text-center w-16 ml-4"
        />
      </label>
      <label
        class="flex items-center justify-center w-1/2 pb-4"
        class:opacity-50={!filterByPoseCountActive}
      >
        Max:
        <input
          type="number"
          bind:value={filterByPoseCountMax}
          disabled={!filterByPoseCountActive}
          min={filterByPoseCountMin}
          max="15"
          step="1"
          class="text-center w-16 ml-4"
        />
      </label>
    </div>
  </div>
</div>
