<!--
  @component
  Generates a tooltip that works on multiseries datasets, like multiline charts. It creates a tooltip showing the name of the series and the current value. It finds the nearest data point using the [QuadTree.html.svelte](https://layercake.graphics/components/QuadTree.html.svelte) component.
 -->
<script>
  import { getContext } from "svelte";
  import { LayerCake, Canvas, Html } from "layercake";
  import { format } from "d3-format";
  import { API_BASE } from "@config";
  import Pose from "@svelte/Pose.svelte";
  import { currentVideo } from "@svelte/stores";
  import { getExtent, getNormDims } from "../../lib/poseutils";

  import QuadTree from "./QuadTree.html.svelte";

  const { data, width, yScale, config } = getContext("LayerCake");

  const commas = format(",");
  const titleCase = (d) => d.replace(/^\w/, (w) => w.toUpperCase());

  /** @type {Function} [formatTitle=d => d] - A function to format the tooltip title, which is `$config.x`. */
  export let formatTitle = (d) => d;

  /** @type {Function} [formatValue=d => isNaN(+d) ? d : commas(d)] - A function to format the value. */
  export let formatValue = (d) => d;

  /** @type {Function} [formatKey=d => titleCase(d)] - A function to format the series name. */
  export let formatKey = (d) => titleCase(d);

  /** @type {Number} [offset=-20] - A y-offset from the hover point, in pixels. */
  export let offset = -20;

  /** @type {Array} [dataset] - The dataset to work off of—defaults to $data if left unset. You can pass something custom in here in case you don't want to use the main data or it's in a strange format. */
  export let dataset = undefined;

  /** @type {String} [searchRadius] – The number of pixels to search around the mouse's location. This is the third argument passed to [`quadtree.find`](https://github.com/d3/d3-quadtree#quadtree_find) and by default a value of `undefined` means an unlimited range. */
  export let searchRadius = undefined;

  /** @type {String} [highlightKey] – The key of the matching search item that should be used for the Y value of the highlight circle. */
  export let highlightKey = undefined;

  /** @type {Array} [hiddenKeys] – Keys from the data rows that should not be shown in the tooltip. */
  export let hiddenKeys = [];

  const w = 300;
  const w2 = w / 2;

  let showFrame = true;

  /* --------------------------------------------
   * Convert results object into a list of key->values,
   * sorting by highest value if doSort is set.
   */
  function resultArray(result, doSort = false) {
    if (Object.keys(result).length === 0) return [];
    let rows = Object.keys(result)
      .filter((d) => d !== $config.x)
      .map((key) => {
        return {
          key,
          value: result[key],
        };
      });
    if (doSort) {
      rows = rows.sort((a, b) => b.value - a.value);
    }

    return rows;
  }

  /* --------------------------------------------
   * If a highlight key is specified, get its value
   */
  function getHighlightValue(result) {
    if (
      Object.keys(result).length > 0 &&
      Object.keys(result).includes(highlightKey)
    )
      return result[highlightKey];
    return null;
  }

  /* --------------------------------------------
   * Get the necessary data about a moused-over pose to draw it in the tooltip.
   */
  async function poseFromMatch(result) {
    if (Object.keys(result).length === 0) return null;
    const response = await fetch(
      `${API_BASE}/frame_track_pose/${$currentVideo.id}/${result.start_frame}/${result.track_id}`,
    );
    const responseJson = await response.json();
    return responseJson[0];
  }
</script>

<QuadTree
  dataset={dataset || $data}
  {searchRadius}
  y={highlightKey ? undefined : "x"}
  let:x
  let:y
  let:visible
  let:found
  let:e
>
  {@const foundArray = resultArray(found)}
  {@const highlightKeyValue = getHighlightValue(found)}
  {#if visible === true}
    <div style="left:{x}px;" class="line" />
    <div
      class="svelte-tooltip"
      style="
        width:{w}px;
        display: {visible ? 'flex' : 'none'};
        top:{$yScale(
        highlightKeyValue === null ? foundArray[0].value : highlightKeyValue,
      ) + offset}px;
        left:{Math.min(Math.max(w2, x), $width - w2)}px;"
    >
      <div class="tooltip-data">
        <div class="title">{formatTitle(found[$config.x])}</div>
        {#each foundArray as row}
          {#if !hiddenKeys.includes(row.key)}
            <div class="row">
              <span class="key">{formatKey(row.key)}:</span>
              {formatValue(row.value)}
            </div>
          {/if}
        {/each}
      </div>
      <div class="tooltip-image aspect-[5/6] py-[30px] px-[10px]">
        {#await poseFromMatch(found)}
          <p>Pose data loading...</p>
        {:then mouseoverPose}
          <LayerCake>
            <Html zIndex={0}>
              <img
                class="object-contain h-full w-full"
                src={`${API_BASE}/frame/resize/${mouseoverPose.video_id}/${
                  mouseoverPose.frame
                }/${getExtent(mouseoverPose.keypoints).join(",")}|${getNormDims(
                  mouseoverPose.norm,
                ).join(",")}`}
                alt={`Frame ${mouseoverPose.frame}, Pose: ${
                  mouseoverPose.pose_idx + 1
                }`}
              />
            </Html>
            <Canvas zIndex={1}>
              <Pose poseData={mouseoverPose.norm} normalizedPose={true} />
            </Canvas>
          </LayerCake>
        {/await}
      </div>
    </div>
    {#if searchRadius !== undefined && highlightKey !== undefined}
      <div
        class="circle"
        style="top:{$yScale(highlightKeyValue)}px;left:{x}px;display: {visible
          ? 'block'
          : 'none'};"
      ></div>
    {/if}
  {/if}
</QuadTree>

<style>
  .svelte-tooltip {
    position: absolute;
    font-size: 13px;
    pointer-events: none;
    border: 1px solid #ccc;
    background: rgba(255, 255, 255, 0.85);
    transform: translate(-50%, -100%);
    padding: 5px;
    z-index: 15;
    pointer-events: none;
    flex-direction: row;
    align-items: center;
  }
  .line {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    border-left: 1px dotted #666;
    pointer-events: none;
  }
  .svelte-tooltip,
  .line {
    transition:
      left 250ms ease-out,
      top 250ms ease-out;
  }
  .title {
    font-weight: bold;
  }
  .key {
    color: #999;
  }
  .circle {
    position: absolute;
    border-radius: 50%;
    background-color: rgba(171, 0, 214);
    transform: translate(-50%, -50%);
    pointer-events: none;
    width: 10px;
    height: 10px;
  }
  .tooltip-data {
    width: 40%;
    margin-left: 10px;
  }
  .tooltip-image {
    width: 60%;
  }
</style>
