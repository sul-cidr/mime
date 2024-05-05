<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, Grid, interactivity, OrbitControls } from "@threlte/extras";

  import {
    COCO_13_DEFAULT,
    COCO_13_SKELETON,
    COCO_COLORS,
  } from "../lib/poseutils";

  export let posePoints = [...COCO_13_DEFAULT];
  export let viewPoint = "free";
  export const resetPose = () => {
    posePoints = [...COCO_13_DEFAULT];
    if (viewPoint === "side") {
      let rotatedCoords = [];
      posePoints.forEach((p) => {
        rotatedCoords.push([-p[2], p[1], p[0]]);
      });
      posePoints = [...rotatedCoords];
    }
  };

  let prevViewpoint = "free";

  let cameraPosition = [0, 0, 200];
  let gridPosition = [0, 0, 0];

  let poseLines = [];
  let activePoint = null;

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

  const updateView = (viewPoint: string) => {
    cameraPosition = [0, 0, 200];
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
    gridSize={[150, 150]}
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
