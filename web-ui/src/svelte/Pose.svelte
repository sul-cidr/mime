<script lang="ts">
  // The body part numberings and armature connectors for the 17-keypoint COCO pose format are defined in
  // https://github.com/openpifpaf/openpifpaf/blob/main/src/openpifpaf/plugins/coco/constants.py
  // Note that the body part numbers in the connector (skeleton) definitions begin with 1, for some reason, not 0
  const COCO_PERSON_SKELETON = [
    [16, 14],
    [14, 12],
    [17, 15],
    [15, 13],
    [12, 13],
    [6, 12],
    [7, 13],
    [6, 7],
    [6, 8],
    [7, 9],
    [8, 10],
    [9, 11],
    [2, 3],
    [1, 2],
    [1, 3],
    [2, 4],
    [3, 5],
    [4, 6],
    [5, 7],
  ];

  const COCO_COLORS = [
    "orangered",
    "orange",
    "blue",
    "lightblue",
    "darkgreen",
    "red",
    "lightgreen",
    "pink",
    "plum",
    "purple",
    "brown",
    "saddlebrown",
    "mediumorchid",
    "gray",
    "salmon",
    "chartreuse",
    "lightgray",
    "darkturquoise",
    "goldenrod",
  ];

  // Face coords are right_eye, left_eye, nose, mouth_right, mouth_left
  // Pose will already draw face landmark connectors, so if there's
  // additional face detection data, just draw dots on the points
  const FACE_COLORS = ["lime", "limegreen", "chartreuse", "lawngreen", "springgreen"]

  export let poseData: CocoSkeletonWithConfidence | CocoSkeletonNoConfidence;
  export let faceData: FaceLandmarks = null;
  export let scaleFactor = 1;
  export let normalizedPose = false;
  export let opacity = 1;
  let segments: FixedLengthArray<
    FixedLengthArray<number, 2> | FixedLengthArray<number, 3>,
    17
  >;

  import { getContext } from "svelte";
  import { scaleCanvas } from "layercake";

  const { width, height } = <
    { width: SvelteStore<number>; height: SvelteStore<number> }
  >getContext("LayerCake");
  const { ctx }: { ctx: SvelteStore<CanvasRenderingContext2D> } =
    getContext("canvas");

  const segmentArray = (arr: Array<number>, l = 3) => {
    if (arr === null) {
      return null
    }
    const _arr = [...arr];
    return [...Array(Math.ceil(arr.length / l))].map((_) => _arr.splice(0, l));
  };

  $: segments = segmentArray(poseData, poseData.length / 17);

  $: facePoints = segmentArray(faceData, 2);

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

      // Draw a line on the canvas for each skeleton segment.
      // If the confidence value for a given armature point is 0, skip related segments.
      COCO_PERSON_SKELETON.forEach(([from, to], i) => {
        let fromX, fromY, toX, toY;
        if (poseData.length === 51) {
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
          fromX * normalizationFactor * scaleFactor,
          fromY * normalizationFactor * scaleFactor,
        );
        $ctx.lineTo(
          toX * normalizationFactor * scaleFactor,
          toY * normalizationFactor * scaleFactor,
        );
        $ctx.stroke();
      });

      if (faceData) {
        const dotRadius = scaleFactor > 0.8 ? 3 : 2;
        facePoints?.forEach(([centerX, centerY], i) => {
          $ctx.beginPath();
          $ctx.arc(centerX! * normalizationFactor * scaleFactor, centerY! * normalizationFactor * scaleFactor, dotRadius * scaleFactor, 0, 2 * Math.PI, false);
          $ctx.fillStyle = FACE_COLORS[i]!;
          $ctx.fill();
          $ctx.lineWidth = dotRadius;
          $ctx.strokeStyle = FACE_COLORS[i]!;
          $ctx.stroke();
        })
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
