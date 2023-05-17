<script lang="ts">
  import { onMount, getContext } from "svelte";

  import { API_BASE } from "@config";

  export let poseRecord: PoseRecord;

  let clipUrl = "";

  const { width, height } = getContext("LayerCake");

  const getBboxForBackground = (bbox) => {
    return bbox.map((d) => Math.round(d)).join("/");
  };

  const scaleBbox = (bbox) => {
    const [, , bboxWidth, bboxHeight] = bbox;
    const longAxis = Math.max(bboxWidth, bboxHeight);
    const f = 100 / longAxis;
    const scaleForCanvasSize = $width / 100;
    const newHeight = bboxHeight * f * scaleForCanvasSize;
    const newWidth = bboxWidth * f * scaleForCanvasSize;
    const xOffset = bboxWidth < bboxHeight ? ($width - newWidth) / 2 : 0;
    const yOffset = bboxWidth > bboxHeight ? ($height - newHeight) / 2 : 0;
    return [xOffset, yOffset, newWidth, newHeight];
  };

  const expandBox = (bbox) => {
    const [originalX, originalY, originalWidth, originalHeight] =
      poseRecord.bbox;
    const [normedX, normedY, normedWidth, normedHeight] = bbox;
    const scaleForCanvasSize = $width / 100;
    const left = originalX - ($width - normedWidth) / 2 / scaleForCanvasSize;
    const top = originalY - ($height - normedHeight) / 2 / scaleForCanvasSize;
    const width = originalWidth + ($width - normedWidth) / scaleForCanvasSize;
    const height =
      originalHeight + ($height - normedHeight) / scaleForCanvasSize;
    return [left, top, width, height];
  };

  let bboxLeft, bboxTop, bboxWidth, bboxHeight;
  let imgLeft, imgTop, imgWidth, imgHeight;

  $: {
    const scaledBbox = scaleBbox(poseRecord.bbox);
    [bboxLeft, bboxTop, bboxWidth, bboxHeight] = scaledBbox;
    // [imgLeft, imgTop, imgWidth, imgHeight] = expandBox(scaledBbox);
    clipUrl = `${API_BASE}/frame/${poseRecord.video_id}/${
      poseRecord.frame
    }/${getBboxForBackground(expandBox(scaledBbox))}/`;
  }
</script>

<div
  style={`
  outline: 1px solid #00ff0077;
  
  position: absolute;
  height: ${bboxHeight || 0}px;
  width: ${bboxWidth || 0}px;
  top: ${bboxTop || 0}px;
  left: ${bboxLeft || 0}px;
`}
/>

<div
  style={`
  outline: 1px solid #ff000077;

  position: absolute;
  height: 100%;
  width: 100%;
  top: 0px
  left: 0px;

  background-image: url(${clipUrl});
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
`}
/>
