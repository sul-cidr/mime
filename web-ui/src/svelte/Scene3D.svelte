<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, Grid, interactivity, OrbitControls } from "@threlte/extras";
  import { currentVideo, currentFrame, currentPose } from "@svelte/stores";
  import { API_BASE } from "@config";

  import {
    COCO_13_SKELETON,
    HAND_21_SKELETON,
    COCO_COLORS,
  } from "../lib/poseutils";

  let poseData: PoseRecord[];
  let handData: HandRecord[];

  let minCoords = [null, null, null];
  let maxCoords = [null, null, null];

  let sceneMidpoint = [0, 0, 0];

  let allPosePoints: number[][][] = [];
  let allPoseLines: THREE.BufferGeometry[][] = [];
  let allPoseExtents: number[][] = [];
  let posePointColors: number[] = [];

  let allHandPoints: number[][][] = [];
  let allHandLines: THREE.BufferGeometry[][] = [];
  let allHandExtents: number[][] = [];
  let handPointColors: number[] = [];

  let zAdjust = 0;

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

  async function getHandData(videoId: string, frame: number) {
    if (!frame) {
      return null;
    }
    const response = await fetch(`${API_BASE}/hands/${videoId}/${frame}/`);
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
      allPosePoints = [];
      allPoseExtents = [];
      minCoords = [null, null, null];
      maxCoords = [null, null, null];
      sceneMidpoint = [0, 0, 0];

      poseData = data;
      const newPosePoints: number[][][] = [];
      posePointColors = [];
      data.forEach((pr: PoseRecord) => {
        if (!pr.keypoints3d) return;
        let projCoords: number[][] = [];
        for (let k = 0; k < pr.keypoints3d?.length; k += 3) {
          const kp = [
            pr.keypoints3d[k],
            pr.keypoints3d[k + 1],
            pr.keypoints3d[k + 2],
          ];
          projCoords.push([
            (kp[0] + pr.camera[0]) * 10,
            (kp[1] + pr.camera[1]) * -10,
            (kp[2] + pr.camera[2]) * -1,
          ]);
        }
        posePointColors.push(0x00ff00);
        newPosePoints.push(projCoords);
      });

      for (let l = 0; l < newPosePoints.length; l += 1) {
        [minCoords, maxCoords] = get3DPoseExtent(
          newPosePoints[l],
          minCoords,
          maxCoords,
        );
      }

      zAdjust = -(maxCoords[2] + minCoords[2]);
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
      //allPosePoints = newPosePoints;

      for (let a = 0; a < allPosePoints.length; a += 1) {
        allPoseExtents.push(get3DPoseExtent(allPosePoints[a]));
      }

      sceneMidpoint = [
        (minCoords[0] + maxCoords[0]) / 2,
        minCoords[1],
        (minCoords[2] + maxCoords[2]) / 2,
      ];
    }
  };

  const updateHandData = (data: Array<HandRecord>) => {
    if (data && data.length) {
      allHandPoints = [];
      allHandExtents = [];

      handData = data;
      const newHandPoints: number[][][] = [];
      handPointColors = [];
      let wristCoords = null;
      data.forEach((hr: HandRecord) => {
        if (!hr.keypoints3d) return;
        let projCoords: number[][] = [];

        poseData.forEach((pr: PoseRecord, p) => {
          if (hr.pose_idx === pr.pose_idx) {
            const w = hr.is_right ? 6 : 5; // * 3;
            wristCoords = [
              allPosePoints[p][w][0],
              allPosePoints[p][w][1],
              allPosePoints[p][w][2],
            ];
            return;
          }
        });

        for (let k = 0; k < hr.keypoints3d?.length; k += 3) {
          const kp = [
            hr.keypoints3d[k] - hr.keypoints3d[0],
            hr.keypoints3d[k + 1] - hr.keypoints3d[1],
            hr.keypoints3d[k + 2] - hr.keypoints3d[2],
          ];
          projCoords.push([
            wristCoords[0] + kp[0] * 10,
            wristCoords[1] + kp[1] * -10,
            wristCoords[2] + kp[2] * -1,
          ]);
        }
        if (hr.is_right) {
          handPointColors.push(0x00ff00);
        } else {
          handPointColors.push(0xff0000);
        }
        newHandPoints.push(projCoords);
      });

      for (let l = 0; l < newHandPoints.length; l += 1) {
        [minCoords, maxCoords] = get3DPoseExtent(
          newHandPoints[l],
          minCoords,
          maxCoords,
        );
      }

      allHandPoints = newHandPoints;

      for (let a = 0; a < allHandPoints.length; a += 1) {
        allHandExtents.push(get3DPoseExtent(allHandPoints[a]));
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

  const updateHandLines = (theseHandPoints: number[][][]) => {
    // Given a set of hand points, make lines connecting the armature points.
    // Drawing these declaratively/reactively, as is done for the actual
    // armature points, doesn't seem to work well with threlte.
    allHandLines = [];
    for (let h = 0; h < allHandPoints.length; h += 1) {
      const handPoints: number[] = theseHandPoints[h];
      let theseHandLines: THREE.BufferGeometry[] = [];
      for (let hh = 0; hh < HAND_21_SKELETON.length; hh += 1) {
        let [from, to] = HAND_21_SKELETON[hh];
        let fromX, fromY, fromZ, toX, toY, toZ;
        [fromX, fromY, fromZ] = handPoints[from! - 1]!;
        [toX, toY, toZ] = handPoints[to! - 1]!;
        let thisGeom = new THREE.BufferGeometry();
        const points = new Float32Array([fromX, fromY, fromZ, toX, toY, toZ]);
        thisGeom.setAttribute("position", new THREE.BufferAttribute(points, 3));
        theseHandLines.push(thisGeom);
      }
      allHandLines.push(theseHandLines);
    }
  };

  $: updatePoseLines(allPosePoints);
  $: updateHandLines(allHandPoints);

  $: getPoseData($currentVideo.id, $currentFrame!).then((data) =>
    updatePoseData(data),
  );

  $: getHandData($currentVideo.id, $currentFrame!).then((data) =>
    updateHandData(data),
  );
</script>

{#each allPosePoints as posePoints, pp}
  <T.Mesh
    position.x={(allPoseExtents[pp][0][0] + allPoseExtents[pp][1][0]) / 2}
    position.y={(allPoseExtents[pp][0][1] + allPoseExtents[pp][1][1]) / 2}
    position.z={(allPoseExtents[pp][0][2] + allPoseExtents[pp][1][2]) / 2}
    on:click={() => {
      $currentPose = poseData[pp];
    }}
    on:pointerover={() => {
      posePointColors[pp] = 0xff0000;
    }}
    on:pointerout={() => {
      posePointColors[pp] = 0x00ff00;
    }}
  >
    <T.BoxGeometry
      args={[
        2 + Math.abs(allPoseExtents[pp][0][0] - allPoseExtents[pp][1][0]),
        2 + Math.abs(allPoseExtents[pp][0][1] - allPoseExtents[pp][1][1]),
        2 + Math.abs(allPoseExtents[pp][0][2] - allPoseExtents[pp][1][2]),
      ]}
    />
    <T.MeshBasicMaterial visible={false} />
  </T.Mesh>
  {#each posePoints as armaturePoint}
    <T.Mesh
      position.x={armaturePoint[0]}
      position.y={armaturePoint[1]}
      position.z={armaturePoint[2]}
    >
      <T.BoxGeometry args={[0.5, 0.5, 0.5]} />
      <T.MeshPhongMaterial color={posePointColors[pp]} />
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

{#each allHandPoints as handPoints, hp}
  <T.Mesh
    position.x={(allHandExtents[hp][0][0] + allHandExtents[hp][1][0]) / 2}
    position.y={(allHandExtents[hp][0][1] + allHandExtents[hp][1][1]) / 2}
    position.z={(allHandExtents[hp][0][2] + allHandExtents[hp][1][2]) / 2}
    on:click={() => {
      //$currentHand = handData[hp];
    }}
    on:pointerover={() => {
      handPointColors[hp] = 0xffff00;
    }}
    on:pointerout={() => {
      handPointColors[hp] = handData[hp].is_right ? 0x00ff00 : 0xff0000;
    }}
  >
    <T.BoxGeometry
      args={[
        2 + Math.abs(allHandExtents[hp][0][0] - allHandExtents[hp][1][0]),
        2 + Math.abs(allHandExtents[hp][0][1] - allHandExtents[hp][1][1]),
        2 + Math.abs(allHandExtents[hp][0][2] - allHandExtents[hp][1][2]),
      ]}
    />
    <T.MeshBasicMaterial visible={false} />
  </T.Mesh>
  {#each handPoints as armaturePoint}
    <T.Mesh
      position.x={armaturePoint[0]}
      position.y={armaturePoint[1]}
      position.z={armaturePoint[2]}
    >
      <T.BoxGeometry args={[0.1, 0.1, 0.1]} />
      <T.MeshPhongMaterial color={handPointColors[hp]} />
    </T.Mesh>
  {/each}
{/each}
{#each allHandLines as handLines}
  {#each handLines as handLine, h}
    <T.Line geometry={handLine}>
      <T.LineBasicMaterial color="black" attach="material" />
    </T.Line>
  {/each}
{/each}

<T.PerspectiveCamera
  makeDefault
  aspect={1}
  fov={75}
  near={1}
  far={400}
  position={[sceneMidpoint[0], maxCoords[1], sceneMidpoint[2] + 50]}
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
  cellSize={5}
  cellThickness={1}
  cellColor="#cccccc"
  gridSize={[150, 150]}
  fadeDistance={200}
  sectionSize={10}
  sectionColor="#777777"
  sectionThickness={2}
/>
<Gizmo horizontalPlacement="left" size={56} paddingX={10} paddingY={10} />
<T.DirectionalLight
  color={0xffffff}
  position={[sceneMidpoint[0], maxCoords[1], sceneMidpoint[2] + 50]}
/>
<T.AmbientLight intensity={0.3} />
