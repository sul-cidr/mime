<script lang="ts">
  import {
    COCO_13_SKELETON,
    COCO_17_SKELETON,
    COCO_COLORS,
    HAND_21_SKELETON,
  } from "../lib/poseutils";

  const SMPL_COLOR = "white";

  // Face coords are right_eye, left_eye, nose, mouth_right, mouth_left
  // Pose will already draw face landmark connectors, so if there's
  // additional face detection data, just draw dots on the points
  const FACE_COLORS = [
    "lime",
    "limegreen",
    "chartreuse",
    "lawngreen",
    "springgreen",
  ];

  export let poseData: CocoSkeletonWithConfidence | CocoSkeletonNoConfidence;
  export let pose4dhData:
    | SmplSkeletonWithConfidence
    | SmplSkeletonNoConfidence = null;
  export let faceData: FaceLandmarks = null;
  export let rightHandData: HandJoints2D = null;
  export let leftHandData: HandJoints2D = null;
  export let scaleFactor = 1;
  export let normalizedPose = false;
  export let maxXywh: FixedLengthArray<number, 4> = [0, 0, null, null];
  export let searchHandData: HandJoints2D = null;
  export let searchHandIsRight: boolean = undefined;
  export let opacity = 1;

  let heightOffset = 0;
  let widthOffset = 0;

  let total_coco_coords = 13;
  let coco_skeleton = COCO_13_SKELETON;
  if (poseData.length % 17 == 0) {
    total_coco_coords = 17;
    coco_skeleton = COCO_17_SKELETON;
  }

  let segments: FixedLengthArray<
    FixedLengthArray<number, 2> | FixedLengthArray<number, 3>,
    total_coco_coords
  >;

  import { getContext } from "svelte";
  import { scaleCanvas } from "layercake";

  const { width, height } = <
    { width: SvelteStore<number>; height: SvelteStore<number> }
  >getContext("LayerCake");
  const { ctx }: { ctx: SvelteStore<CanvasRenderingContext2D> } =
    getContext("canvas");

  const segmentArray = (arr: Array<number>, l = 3) => {
    if (arr == null) {
      return null;
    }
    const _arr = [...arr];
    return [...Array(Math.ceil(arr.length / l))].map((_) => _arr.splice(0, l));
  };

  $: segments = segmentArray(poseData, poseData.length / total_coco_coords);

  $: smplPoints = segmentArray(pose4dhData, pose4dhData?.length / 45);

  $: facePoints = segmentArray(faceData, 2);

  $: rightHandPoints = segmentArray(rightHandData, 2);
  $: leftHandPoints = segmentArray(leftHandData, 2);
  $: searchHandPoints = segmentArray(searchHandData, 2);

  $: {
    if ($ctx) {
      /* --------------------------------------------
       * TODO ??
       * If you were to have multiple canvas layers
       * maybe for some artistic layering purposes
       * put these reset functions in the first layer, not each one
       * since they should only run once per update
       */

      // "Scale your canvas size to retina screens."
      // (see https://layercake.graphics/guide#scalecanvas)

      scaleCanvas($ctx, $width, $height);
      $ctx.globalAlpha = opacity;
      $ctx.clearRect(0, 0, $width, $height);

      const normalizationFactor = normalizedPose ? $width / 100 : 1;

      if (maxXywh[2] !== null && maxXywh[3] !== null) {
        scaleFactor =
          maxXywh[2] >= maxXywh[3] ? $width / maxXywh[2] : $height / maxXywh[3];
        widthOffset = ($width - maxXywh[2] * scaleFactor) / 2;
        heightOffset = ($height - maxXywh[3] * scaleFactor) / 2;
      }

      // Draw a line on the canvas for each skeleton segment.
      // If the confidence value for a given armature point is 0, skip related segments.
      coco_skeleton.forEach(([from, to], i) => {
        let fromX, fromY, toX, toY;
        if (poseData.length === total_coco_coords * 3) {
          let fromConfidence, toConfidence;
          [fromX, fromY, fromConfidence] = segments[from! - 1]!;
          [toX, toY, toConfidence] = segments[to! - 1]!;
          if (fromConfidence == 0 || toConfidence == 0) return;
        } else {
          [fromX, fromY] = segments[from! - 1]!;
          [toX, toY] = segments[to! - 1]!;
          if ([fromX, fromY, toX, toY].some((x) => x === -1)) return;
        }

        $ctx.lineWidth = scaleFactor > 0.8 ? 3 : 2;
        $ctx.strokeStyle = COCO_COLORS[i]!;

        $ctx.beginPath();
        $ctx.moveTo(
          (fromX - maxXywh[0]) * normalizationFactor * scaleFactor +
            widthOffset,
          (fromY - maxXywh[1]) * normalizationFactor * scaleFactor +
            heightOffset,
        );
        $ctx.lineTo(
          (toX - maxXywh[0]) * normalizationFactor * scaleFactor + widthOffset,
          (toY - maxXywh[1]) * normalizationFactor * scaleFactor + heightOffset,
        );
        $ctx.stroke();
      });

      if (pose4dhData) {
        const dotRadius = scaleFactor > 0.8 ? 2 : 4;
        smplPoints?.forEach(([centerX, centerY], i) => {
          $ctx.beginPath();
          $ctx.arc(
            (centerX! - maxXywh[0]) * normalizationFactor * scaleFactor +
              widthOffset,
            (centerY! - maxXywh[1]) * normalizationFactor * scaleFactor +
              heightOffset,
            dotRadius * scaleFactor,
            0,
            2 * Math.PI,
            false,
          );
          $ctx.globalAlpha = 0.8;
          $ctx.fillStyle = SMPL_COLOR!;
          $ctx.fill();
          // Just draw points for the SMPL+ vertices, not connections
          //$ctx.lineWidth = dotRadius;
          //$ctx.strokeStyle = SMPL_COLOR!;
          //$ctx.stroke();
        });
      }

      const drawHand = (handPoints: Array<number[]>, isRight: boolean) => {
        if (handPoints === null) return;

        HAND_21_SKELETON.forEach(([from, to], i) => {
          let fromX, fromY, toX, toY;
          [fromX, fromY] = handPoints[from! - 1]!;
          [toX, toY] = handPoints[to! - 1]!;

          $ctx.lineWidth = scaleFactor > 0.8 ? 3 : 2;
          // port (left) wine is red, starboard is green
          $ctx.strokeStyle = isRight ? "green" : "red ";

          $ctx.beginPath();
          $ctx.moveTo(
            (fromX - maxXywh[0]) * normalizationFactor * scaleFactor +
              widthOffset,
            (fromY - maxXywh[1]) * normalizationFactor * scaleFactor +
              heightOffset,
          );
          $ctx.lineTo(
            (toX - maxXywh[0]) * normalizationFactor * scaleFactor +
              widthOffset,
            (toY - maxXywh[1]) * normalizationFactor * scaleFactor +
              heightOffset,
          );
          $ctx.stroke();
        });
      };

      if (searchHandData !== null && searchHandIsRight !== undefined) {
        drawHand(searchHandPoints, searchHandIsRight);
      } else {
        drawHand(rightHandPoints, true);
        drawHand(leftHandPoints, false);
      }

      if (faceData) {
        const dotRadius = scaleFactor > 0.8 ? 3 : 2;
        facePoints?.forEach(([centerX, centerY], i) => {
          $ctx.beginPath();
          $ctx.arc(
            (centerX! - maxXywh[0]) * normalizationFactor * scaleFactor +
              widthOffset,
            (centerY! - maxXywh[1]) * normalizationFactor * scaleFactor +
              heightOffset,
            dotRadius * scaleFactor,
            0,
            2 * Math.PI,
            false,
          );
          $ctx.fillStyle = FACE_COLORS[i]!;
          $ctx.fill();
          $ctx.lineWidth = dotRadius;
          $ctx.strokeStyle = FACE_COLORS[i]!;
          $ctx.stroke();
        });
      }
    }
  }
</script>

<!-- 
  @component
  Render an individual pose as a canvas element.
  
  Usage:
    ```tsx
  <Pose poseData={COCO_Keypoints} />
  ```
 -->
