<script lang="ts">
  import { LayerCake, Canvas } from "layercake";
  import Pose from "@svelte/Pose.svelte";

  export let moveletData: MoveletRecord;
</script>

<LayerCake>
  <Canvas zIndex={1}>
    <Pose poseData={moveletData.norm} normalizedPose={true} opacity={0.5} />
  </Canvas>
  <Canvas zIndex={2}>
    <Pose
      poseData={moveletData.prev_norm}
      normalizedPose={true}
      opacity={0.3}
    />
  </Canvas>
</LayerCake>
