<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, OrbitControls } from "@threlte/extras";
  import {
    shiftNormalizeRescalePoseCoords,
    COCO_13_SKELETON,
    COCO_COLORS,
  } from "../lib/poseutils";
  import { currentPose, currentVideo } from "@svelte/stores";

  export let pose: PoseRecord;

  let posePoints = [];
  let poseLines = [];

  let autoRotate: boolean = false;
  let enableDamping: boolean = true;
  let rotateSpeed: number = 1;
  let zoomToCursor: boolean = false;
  let zoomSpeed: number = 1;
  let minPolarAngle: number = 0;
  let maxPolarAngle: number = Math.PI;
  let enableZoom: boolean = true;

  const updatePose = (posePoints) => {
    // Draw lines connecting the armature points
    poseLines = [];
    poseLines = COCO_13_SKELETON.map(([from, to]) => {
      let fromX, fromY, fromZ, toX, toY, toZ;
      [fromX, fromY, fromZ] = posePoints[from! - 1]!;
      [toX, toY, toZ] = posePoints[to! - 1]!;

      let geom = new THREE.BufferGeometry();
      const points = new Float32Array([fromX, fromY, fromZ, toX, toY, toZ]);
      geom.setAttribute("position", new THREE.BufferAttribute(points, 3));
      return geom;
    });
  };

  const updatePoseData = (pose: PoseRecord) => {
    posePoints = [];
    if (pose.global3d_coco13) {
      for (let i = 0; i < pose.global3d_coco13.length; i += 3) {
        posePoints.push(
          pose.global3d_coco13
            .slice(i, i + 3)
            .map((point) => Math.round(point * 100)),
        );
      }
    } else {
      // Provides some degraded functionality if 3D pose data is not available
      // (Pose appears in the 3D Pose pane, but is not available in 3D pose editor)
      for (let i = 0; i < pose.norm.length; i += 2) {
        posePoints.push([pose.norm[i] - 50, 50 - pose.norm[i + 1], 0]);
      }
    }
    updatePose(posePoints);
  };

  $: updatePoseData(pose);
</script>

{#each posePoints as armaturePoint}
  <T.Mesh
    position.x={armaturePoint[0]}
    position.y={armaturePoint[1]}
    position.z={armaturePoint[2]}
  >
    <T.BoxGeometry args={[10, 10, 10]} />
    <T.MeshPhongMaterial color={0x00ff00} />
  </T.Mesh>
{/each}
{#each poseLines as poseLine, i}
  <T.Line geometry={poseLine}>
    <T.LineBasicMaterial color={COCO_COLORS[i]} attach="material" />
  </T.Line>
{/each}
<T.PerspectiveCamera
  makeDefault
  aspect={1}
  fov={75}
  near={0.1}
  far={300}
  position={[0, 0, 150]}
  on:create={({ ref }) => {
    ref.lookAt(0, 0, 0);
  }}
>
  <OrbitControls
    {enableDamping}
    {autoRotate}
    {rotateSpeed}
    {zoomToCursor}
    {zoomSpeed}
    {minPolarAngle}
    {maxPolarAngle}
    {enableZoom}
  />
</T.PerspectiveCamera>
<Gizmo horizontalPlacement="left" size={56} paddingX={10} paddingY={10} />
<T.DirectionalLight color={0xffffff} position={[0, 0, 2]} />
<T.AmbientLight intensity={0.3} />
