<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, OrbitControls } from "@threlte/extras";
  import { HAND_21_SKELETON } from "../lib/poseutils";

  export let handPose: PoseRecord;

  let handPoints = [];
  let handLines = [];

  let autoRotate: boolean = false;
  let enableDamping: boolean = true;
  let rotateSpeed: number = 1;
  let zoomToCursor: boolean = false;
  let zoomSpeed: number = 1;
  let minPolarAngle: number = 0;
  let maxPolarAngle: number = Math.PI;
  let enableZoom: boolean = true;

  const updateHand = (handPoints) => {
    // Draw lines connecting the armature points
    handLines = [];
    handLines = HAND_21_SKELETON.map(([from, to]) => {
      let fromX, fromY, fromZ, toX, toY, toZ;
      [fromX, fromY, fromZ] = handPoints[from! - 1]!;
      [toX, toY, toZ] = handPoints[to! - 1]!;

      let geom = new THREE.BufferGeometry();
      const points = new Float32Array([fromX, fromY, fromZ, toX, toY, toZ]);
      geom.setAttribute("position", new THREE.BufferAttribute(points, 3));
      return geom;
    });
  };

  const updateHandData = (pose: PoseRecord) => {
    let handCoords = [];
    handPoints = [];
    if (pose.search_is_right && pose.rh_keypoints_3d !== undefined) {
      handCoords = pose.rh_keypoints_3d;
    } else if (!pose.search_is_right && pose.lh_keypoints_3d !== undefined) {
      handCoords = pose.lh_keypoints_3d;
    }

    for (let i = 0; i < handCoords.length; i += 3) {
      handPoints.push(
        handCoords.slice(i, i + 3).map((point) => Math.round(point * 1000)),
      );
    }

    updateHand(handPoints);
  };

  $: updateHandData(handPose);
</script>

{#each handPoints as armaturePoint}
  <T.Mesh
    position.x={armaturePoint[0]}
    position.y={armaturePoint[1]}
    position.z={armaturePoint[2]}
  >
    <T.BoxGeometry args={[10, 10, 10]} />
    <T.MeshPhongMaterial color={0x00ff00} />
  </T.Mesh>
{/each}
{#each handLines as handLine, i}
  <T.Line geometry={handLine}>
    <T.LineBasicMaterial color="black" attach="material" />
  </T.Line>
{/each}
<T.PerspectiveCamera
  makeDefault
  aspect={1}
  fov={75}
  near={0.1}
  far={500}
  position={[0, 0, 250]}
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
