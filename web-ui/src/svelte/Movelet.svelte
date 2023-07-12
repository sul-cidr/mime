<script lang="ts">
  import { LayerCake, Canvas, Html } from "layercake";
  import Pose from "@svelte/Pose.svelte";

  export let moveletData: MoveletRecord;

  export let scaleFactor = 1;
  export let normalizedPose = true; // Movelets are always normalized
</script>

<LayerCake>
  <Canvas zIndex={1}>
    <Pose poseData={moveletData.norm} normalizedPose={true} opacity={.5} />
  </Canvas>
  <Canvas zIndex={2}>
    <Pose poseData={moveletData.prev_norm} normalizedPose={true} opacity={.3} />
  </Canvas>
</LayerCake>
  