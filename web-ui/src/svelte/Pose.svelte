<script>
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

  export let poseData;
  let segments;

  import { getContext } from "svelte";
  import { scaleCanvas } from "layercake";

  const { width, height } = getContext("LayerCake");
  const { ctx } = getContext("canvas");

  $: segments = [...Array(Math.ceil(poseData.keypoints.length / 3))].map((_) =>
    poseData.keypoints.splice(0, 3),
  ); // nb. mutates `poseData`...

  $: {
    if ($ctx) {
      /* --------------------------------------------
       * TODO ??
       * If you were to have multiple canvas layers
       * maybe for some artistic layering purposes
       * put these reset functions in the first layer, not each one
       * since they should only run once per update
       */
      scaleCanvas($ctx, $width, $height);
      $ctx.clearRect(0, 0, $width, $height);

      // Draw a line on the canvas for each skeleton segment.
      // If the confidence value for a given armature point is 0, skip related segments.
      COCO_PERSON_SKELETON.forEach(([from, to], i) => {
        const [fromX, fromY, fromConfidence] = segments[from - 1];
        const [toX, toY, toConfidence] = segments[to - 1];
        if (fromConfidence == 0 || toConfidence == 0) {
          return;
        }

        $ctx.lineWidth = 3;
        $ctx.strokeStyle = COCO_COLORS[i];

        $ctx.beginPath();
        $ctx.moveTo(fromX, fromY);
        $ctx.lineTo(toX, toY);
        $ctx.stroke();

        // $ctx.lineWidth = 1;
        // $ctx.strokeStyle = "white";
        // $ctx.beginPath();
        // $ctx.rect(...poseData.bbox);
        // $ctx.stroke();
      });
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
