<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, Grid, interactivity, OrbitControls } from "@threlte/extras";
  import { currentPose } from "@svelte/stores";

  import {
    COCO_13_DEFAULT,
    COCO_13_SKELETON,
    COCO_COLORS,
    getPoseVectorExtent,
  } from "../lib/poseutils";

  // If there's a currently selected search pose with a 3D version, use it
  export let posePoints = $currentPose?.global3d_coco13 || [...COCO_13_DEFAULT];
  export let viewPoint = "free";
  export const resetPose = () => {
    posePoints = [...COCO_13_DEFAULT];
    // The side "yz" plane view is just a manually rotated xy plane view, so we
    // need to apply this manual rotation to the default pose when in side view
    if (viewPoint === "side") {
      let rotatedCoords = [];
      posePoints.forEach((p) => {
        rotatedCoords.push([-p[2], p[1], p[0]]);
      });
      posePoints = [...rotatedCoords];
    }
  };

  let prevViewpoint = "free";

  let cameraPosition = [-50, 50, 200]; // A bit off from square, to show depth (?)
  let gridPosition = [0, 0, 0];

  let poseLines = [];
  let activePoint = null;

  // Camera orbit controls settings
  let autoRotate: boolean = false;
  let enableDamping: boolean = true;
  let rotateSpeed: number = 1;
  let zoomToCursor: boolean = false;
  let zoomSpeed: number = 1;
  let minPolarAngle: number = 0;
  let maxPolarAngle: number = Math.PI;
  let enableZoom: boolean = true;

  interactivity();

  const updatePose = (posePoints: []) => {
    // Given a set of pose points, make lines connecting the armature points.
    // Drawing these declaratively/reactively, as is done for the actual
    // armature points, doesn't seem to work well with threlte.
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

  const updatePosePoints = (newPose) => {
    // If the pose is from the DB, it will be a 39-element flat vector, rather
    // than an array of 13 coordinate objects. If we detect this, then we
    // preprocess the pose and convert it to a 13-point array before using it.
    if (newPose.length > 13) {
      // 3D poses from PHALP tend have x, y or z coords that slightly exceed
      // -.5 <= coord <= .5, but ideally they'd fit in a 1x1x1 cube that can
      // then be blown up to 100x100x100 for the 3D viz, so for now we just
      // scale and shift them so that they fit in the 1x1x1 cube.
      const poseExtent = getPoseVectorExtent(newPose);
      const xScale = poseExtent.w > 1 ? 1 / poseExtent.w : 1;
      const yScale = poseExtent.h > 1 ? 1 / poseExtent.h : 1;
      const zScale = poseExtent.d > 1 ? 1 / poseExtent.d : 1;
      const xOffset = poseExtent.x < -0.5 ? 0.5 + poseExtent.x : 0;
      const yOffset = poseExtent.y < -0.5 ? 0.5 + poseExtent.y : 0;
      const zOffset = poseExtent.z < -0.5 ? 0.5 + poseExtent.z : 0;

      let combinedPosePoints = [];

      for (let p = 0; p < newPose.length; p += 3) {
        combinedPosePoints.push([
          (newPose[p] + xOffset) * xScale * 100,
          (newPose[p + 1] + yOffset) * yScale * 100,
          (newPose[p + 2] + zOffset) * zScale * 100,
        ]);
      }
      posePoints = [...combinedPosePoints];
    }
  };

  const updateView = (viewPoint: string) => {
    // Slightly tortured logic here. A "side" view towards the yz plane seems
    // desirable for editing the depth (z axis) of the pose armature points,
    // but detecting pointer events only seems to work for the xy plane (maybe
    // a bug in Svelte/ThreeJS?), so for now we just manually rotate the coords
    // (by swapping the x and z values with their polarity reversed) when the
    // side view edit is selected while in the front pose editor or free view,
    // and then de-rotate them when switching back to front or free view, or
    // when using them to search the DB.
    cameraPosition = [-50, 50, 200];
    if (viewPoint === prevViewpoint) return;
    let rotatedCoords = [];
    if (
      (prevViewpoint === "free" || prevViewpoint === "front") &&
      viewPoint === "side"
    ) {
      posePoints.forEach((p) => {
        rotatedCoords.push([-p[2], p[1], p[0]]);
      });
      posePoints = [...rotatedCoords];
    } else if (
      prevViewpoint === "side" &&
      (viewPoint === "free" || viewPoint === "front")
    ) {
      posePoints.forEach((p) => {
        rotatedCoords.push([p[2], p[1], -p[0]]);
      });
      posePoints = [...rotatedCoords];
    }
    prevViewpoint = viewPoint;
  };

  $: updatePosePoints($currentPose?.global3d_coco13);
  $: updatePose(posePoints);
  $: updateView(viewPoint);
</script>

{#each posePoints as armaturePoint, p}
  <T.Mesh
    position.x={armaturePoint[0]}
    position.y={armaturePoint[1]}
    position.z={armaturePoint[2]}
    on:pointerdown={(e) => {
      if (viewPoint !== "free" && activePoint === null) {
        gridPosition = [0, 0, posePoints[p][2]];
        activePoint = p;
      }
      e.stopPropagation();
    }}
    on:pointermove={(e) => {
      if (viewPoint !== "free" && activePoint === p) {
        posePoints[p] = [e.point.x, e.point.y, posePoints[p][2]];
      }
      e.stopPropagation();
    }}
  >
    <T.BoxGeometry args={[5, 5, 5]} />
    <T.MeshPhongMaterial color={activePoint === p ? 0xff0000 : 0x00ff00} />
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
  far={800}
  position={cameraPosition}
  target={[0, 0, 0]}
>
  <OrbitControls
    enabled={viewPoint === "free"}
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
{#if viewPoint !== "free"}
  <Grid
    position={gridPosition}
    plane="xy"
    cellSize={5}
    cellThickness={1}
    cellColor="#cccccc"
    gridSize={[200, 200]}
    fadeDistance={300}
    sectionSize={10}
    sectionColor="#777777"
    sectionThickness={2}
    on:pointerup={(e) => {
      if (activePoint !== null) {
        posePoints[activePoint] = [
          e.point.x,
          e.point.y,
          posePoints[activePoint][2],
        ];
        activePoint = null;
      }
      e.stopPropagation();
    }}
    on:pointermove={(e) => {
      if (activePoint !== null)
        posePoints[activePoint] = [
          e.point.x,
          e.point.y,
          posePoints[activePoint][2],
        ];
      e.stopPropagation();
    }}
  />
{/if}
<Gizmo horizontalPlacement="left" size={100} paddingX={20} paddingY={20} />
<T.DirectionalLight color={0xffffff} position={[0, 0, 2]} />
<T.AmbientLight intensity={0.3} />
