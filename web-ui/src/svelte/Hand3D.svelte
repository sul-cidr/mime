<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, OrbitControls } from "@threlte/extras";
  import { HAND_21_SKELETON, get3DPoseExtent } from "../lib/poseutils";

  export let handPose: PoseRecord;

  let handPoints: number[][] = [];
  let handLines = [];

  let sceneMidpoint = [0, 0, 0];

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
    let zAdjust = 0;
    handPoints = [];

    let minCoords = [null, null, null];
    let maxCoords = [null, null, null];
    sceneMidpoint = [0, 0, 0];

    console.log("hand camera transform:", pose.hand_camera_transform);

    if (pose.search_is_right && pose.rh_keypoints_3d !== undefined) {
      handCoords = pose.rh_keypoints_3d;
    } else if (!pose.search_is_right && pose.lh_keypoints_3d !== undefined) {
      handCoords = pose.lh_keypoints_3d;
    }

    let rawPoints: number[][] = [];
    for (let i = 0; i < handCoords.length; i += 3) {
      rawPoints.push([handCoords[i], handCoords[i + 1], handCoords[i + 2]]);
    }

    // Project the 3D keypoints of the raw hand detection (which seems to have
    // no particular orientation) into the scene so that they can be drawn
    // with the same orientation as seen in the 2D image. Also scale up the
    // distances between the points in every dimension and flip the Y and Z
    // axes so that the hand appears correctly in the visualization.
    let projPoints: number[][] = [];
    rawPoints.forEach((point) => {
      projPoints.push([
        (point[0] + pose.hand_camera_transform[0]) * 100,
        (point[1] + pose.hand_camera_transform[1]) * -100,
        (point[2] + pose.hand_camera_transform[2]) * -100,
      ]);
    });

    // Determine the midpoint of the hand in the projected 3D space
    [minCoords, maxCoords] = get3DPoseExtent(projPoints, minCoords, maxCoords);

    let anchorPoint = [
      (minCoords[0] + maxCoords[0]) / 2,
      (minCoords[1] + maxCoords[1]) / 2,
      (minCoords[2] + maxCoords[2]) / 2,
    ];

    // Shift the projected points so that the hand midpoint is at [0,0,0]
    projPoints.forEach((point) => {
      handPoints.push([
        point[0] - anchorPoint[0],
        point[1] - anchorPoint[1],
        point[2] - anchorPoint[2],
      ]);
    });

    [minCoords, maxCoords] = get3DPoseExtent(handPoints, minCoords, maxCoords);

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
    <T.BoxGeometry args={[1, 1, 1]} />
    <T.MeshPhongMaterial
      color={handPose.search_is_right ? 0x00ff00 : 0xff0000}
    />
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
  position={[0, 0, 15]}
  on:create={({ ref }) => {
    ref.lookAt([0, 0, 0]);
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
<T.DirectionalLight color={0xffffff} position={[0, 0, 1]} />
<T.AmbientLight intensity={0.3} />
