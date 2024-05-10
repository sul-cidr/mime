<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, Grid, interactivity, OrbitControls } from "@threlte/extras";
  import { currentVideo, currentFrame, currentPose } from "@svelte/stores";
  import { API_BASE } from "@config";

  import { COCO_13_SKELETON, COCO_COLORS } from "../lib/poseutils";

  let poseData: PoseRecord[];

  let minCoords = [null, null, null];
  let maxCoords = [null, null, null];

  let sceneMidpoint = [0, 0, 0];

  let allPosePoints: number[][][] = [];
  let allPoseLines: THREE.BufferGeometry[][] = [];
  let allPoseExtents: number[][] = [];
  let allPoseWireOpacities: number[] = [];

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

  async function getPoseData(videoId: string, frame: number) {
    if (!frame) {
      return null;
    }
    const response = await fetch(`${API_BASE}/poses/${videoId}/${frame}/`);
    return await response.json();
  }

  const get3DPoseExtent = (
    pose: [],
    minsSoFar = [null, null, null],
    maxsSoFar = [null, null, null],
  ) => {
    const poseMin = pose.reduce(
      (poseMins, coords) => [
        poseMins[0] === null ? coords[0] : Math.min(poseMins[0], coords[0]),
        poseMins[1] === null ? coords[1] : Math.min(poseMins[1], coords[1]),
        poseMins[2] === null ? coords[2] : Math.min(poseMins[2], coords[2]),
      ],
      minsSoFar,
    );
    const poseMax = pose.reduce(
      (poseMaxs, coords) => [
        poseMaxs[0] === null ? coords[0] : Math.max(poseMaxs[0], coords[0]),
        poseMaxs[1] === null ? coords[1] : Math.max(poseMaxs[1], coords[1]),
        poseMaxs[2] === null ? coords[2] : Math.max(poseMaxs[2], coords[2]),
      ],
      maxsSoFar,
    );
    return [poseMin, poseMax];
  };

  const updatePoseData = (data: Array<PoseRecord>) => {
    if (data && data.length) {
      minCoords = [null, null, null];
      maxCoords = [null, null, null];
      sceneMidpoint = [0, 0, 0];

      poseData = data;
      const newPosePoints: number[][][] = [];
      data.forEach((pr: PoseRecord) => {
        let projCoords: number[][] = [];
        for (let k = 0; k < pr.keypoints3d.length; k += 3) {
          const kp = [
            pr.keypoints3d[k],
            pr.keypoints3d[k + 1],
            pr.keypoints3d[k + 2],
          ];
          projCoords.push([
            (kp[0] + pr.camera[0]) * 10,
            (kp[1] + pr.camera[1]) * -10,
            (kp[2] - pr.camera[2]) * 1,
          ]);
        }
        newPosePoints.push(projCoords);
      });

      for (let l = 0; l < newPosePoints.length; l += 1) {
        [minCoords, maxCoords] = get3DPoseExtent(
          newPosePoints[l],
          minCoords,
          maxCoords,
        );
      }

      const zAdjust = -(maxCoords[2] + minCoords[2]);
      minCoords[2] += zAdjust;
      maxCoords[2] += zAdjust;

      let reprojCoords: number[][] = [];
      const shiftedPosePoints: number[][][] = [];
      for (let n = 0; n < newPosePoints.length; n += 1) {
        reprojCoords = [];
        for (let r = 0; r < newPosePoints[n].length; r += 1) {
          reprojCoords.push([
            newPosePoints[n][r][0],
            newPosePoints[n][r][1],
            newPosePoints[n][r][2] + zAdjust,
          ]);
        }
        shiftedPosePoints.push(reprojCoords);
      }
      allPosePoints = shiftedPosePoints;

      for (let a = 0; a < allPosePoints.length; a += 1) {
        allPoseExtents.push(get3DPoseExtent(allPosePoints[a]));
        allPoseWireOpacities.push(0);
      }

      sceneMidpoint = [
        (minCoords[0] + maxCoords[0]) / 2,
        minCoords[1],
        (minCoords[2] + maxCoords[2]) / 2,
      ];
    }
  };

  const updatePoseLines = (thesePosePoints: number[][][]) => {
    // Given a set of pose points, make lines connecting the armature points.
    // Drawing these declaratively/reactively, as is done for the actual
    // armature points, doesn't seem to work well with threlte.
    allPoseLines = [];
    for (let p = 0; p < allPosePoints.length; p += 1) {
      const posePoints: number[] = thesePosePoints[p];
      let thesePoseLines: THREE.BufferGeometry[] = [];
      for (let pp = 0; pp < COCO_13_SKELETON.length; pp += 1) {
        let [from, to] = COCO_13_SKELETON[pp];
        let fromX, fromY, fromZ, toX, toY, toZ;
        [fromX, fromY, fromZ] = posePoints[from! - 1]!;
        [toX, toY, toZ] = posePoints[to! - 1]!;
        let thisGeom = new THREE.BufferGeometry();
        const points = new Float32Array([fromX, fromY, fromZ, toX, toY, toZ]);
        thisGeom.setAttribute("position", new THREE.BufferAttribute(points, 3));
        thesePoseLines.push(thisGeom);
      }
      allPoseLines.push(thesePoseLines);
    }
  };

  $: updatePoseLines(allPosePoints);

  $: getPoseData($currentVideo.id, $currentFrame!).then((data) =>
    updatePoseData(data),
  );
</script>

{#each allPosePoints as posePoints, pp}
  <T.Mesh
    position.x={(allPoseExtents[pp][0][0] + allPoseExtents[pp][1][0]) / 2}
    position.y={(allPoseExtents[pp][0][1] + allPoseExtents[pp][1][1]) / 2}
    position.z={(allPoseExtents[pp][0][2] + allPoseExtents[pp][1][2]) / 2}
    on:pointerover={() => {
      allPoseWireOpacities[pp] = 1;
    }}
    on:pointerout={() => {
      allPoseWireOpacities[pp] = 0;
    }}
    on:click={() => {
      $currentPose = poseData[pp];
    }}
  >
    <T.BoxGeometry
      args={[
        5 + Math.abs(allPoseExtents[pp][0][0] - allPoseExtents[pp][1][0]),
        5 + Math.abs(allPoseExtents[pp][0][1] - allPoseExtents[pp][1][1]),
        5 + Math.abs(allPoseExtents[pp][0][2] - allPoseExtents[pp][1][2]),
      ]}
    />
    <T.MeshBasicMaterial
      color={0x00ff00}
      wireframe={true}
      transparent={true}
      opacity={allPoseWireOpacities[pp]}
    />
  </T.Mesh>
  {#each posePoints as armaturePoint}
    <T.Mesh
      position.x={armaturePoint[0]}
      position.y={armaturePoint[1]}
      position.z={armaturePoint[2]}
    >
      <T.BoxGeometry args={[1, 1, 1]} />
      <T.MeshPhongMaterial color={0x00ff00} />
    </T.Mesh>
  {/each}
{/each}
{#each allPoseLines as poseLines}
  {#each poseLines as poseLine, p}
    <T.Line geometry={poseLine}>
      <T.LineBasicMaterial color={COCO_COLORS[p]} attach="material" />
    </T.Line>
  {/each}
{/each}

<T.PerspectiveCamera
  makeDefault
  aspect={1}
  fov={75}
  near={1}
  far={400}
  position={[sceneMidpoint[0], maxCoords[1], maxCoords[2] + 50]}
  target={sceneMidpoint}
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
<Grid
  position={sceneMidpoint}
  plane="xz"
  cellSize={1}
  cellThickness={1}
  cellColor="#cccccc"
  gridSize={[100, 100]}
  fadeDistance={100}
  sectionSize={5}
  sectionColor="#777777"
  sectionThickness={2}
/>
<Gizmo horizontalPlacement="left" size={56} paddingX={10} paddingY={10} />
<T.DirectionalLight color={0xffffff} position={[0, 0, 2]} />
<T.AmbientLight intensity={0.3} />
