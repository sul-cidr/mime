<script>
  // The body part numberings and armature connectors for the 17-keypoint COCO pose format are defined in
  // https://github.com/openpifpaf/openpifpaf/blob/main/src/openpifpaf/plugins/coco/constants.py
  // Note that the body part numbers in the connector (skeleton) definitions begin with 1, for some reason, not 0
  const OPP_COCO_SKELETON = [
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

  const OPP_COCO_COLORS = [
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

  const segments = [...Array(Math.ceil(poseData.length / 3))].map((_) =>
    poseData.splice(0, 3),
  ); // nb. mutates `poseData`...

  import { getContext } from "svelte";
  import { scaleCanvas } from "layercake";

  const { width, height } = getContext("LayerCake");
  const { ctx } = getContext("canvas");

  console.log($width, $height);

  $: {
    if ($ctx) {
      /* --------------------------------------------
       * If you were to have multiple canvas layers
       * maybe for some artistic layering purposes
       * put these reset functions in the first layer, not each one
       * since they should only run once per update
       */
      scaleCanvas($ctx, $width, $height);
      $ctx.clearRect(0, 0, $width, $height);

      $ctx.lineWidth = 3;

      OPP_COCO_SKELETON.forEach(([from, to], i) => {
        const [fromX, fromY, fromConfidence] = segments[from - 1];
        const [toX, toY, toConfidence] = segments[to - 1];
        if (fromConfidence == 0 || toConfidence == 0) {
          return;
        }
        $ctx.strokeStyle = OPP_COCO_COLORS[i];

        $ctx.beginPath();
        $ctx.moveTo(fromX, fromY);
        $ctx.lineTo(toX, toY);
        $ctx.stroke();
      });
    }
  }
</script>
