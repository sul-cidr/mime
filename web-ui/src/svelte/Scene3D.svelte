<script lang="ts">
  import * as THREE from "three";
  import { T } from "@threlte/core";
  import { Gizmo, Grid, interactivity, OrbitControls } from "@threlte/extras";
  import { currentPose, currentHandPose } from "@svelte/stores";

  import {
    COCO_13_SKELETON,
    HAND_21_SKELETON,
    COCO_COLORS,
    get3DPoseExtent,
  } from "../lib/poseutils";

  export let poses: Array<PoseRecord>;
  export let hands: Array<HandRecord>;
  export let hoveredPoseIdx: number | undefined;

  let minCoords = [null, null, null];
  let maxCoords = [null, null, null];

  let sceneMidpoint = [0, 0, 0];

  let allPosePoints: { [pose_idx: number]: number[][] } = {};

  let allPoseLines: THREE.BufferGeometry[][] = [];
  let allPoseExtents: { [pose_idx: number]: number[][] } = {};
  let posePointColors: { [pose_idx: number]: number } = {};

  let allHandPoints: number[][][] = [];
  let handPointsToHand: { [handPointIdx: number]: number } = {};
  let allHandLines: THREE.BufferGeometry[][] = [];
  let allHandExtents: number[][][] = [];
  let handPointColors: number[] = [];

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

  const setSearchHandPose = (hr: HandRecord) => {
    poses.every((pr: PoseRecord) => {
      if (hr.pose_idx === pr.pose_idx) {
        pr.search_is_right = hr.is_right;
        pr.search_hand_keypoints2d = hr.keypoints2d;
        pr.rh_keypoints_2d = hr.is_right ? hr.keypoints2d : undefined;
        pr.rh_keypoints_3d = hr.is_right ? hr.keypoints3d : undefined;
        pr.lh_keypoints_2d = hr.is_right ? undefined : hr.keypoints2d;
        pr.lh_keypoints_3d = hr.is_right ? undefined : hr.keypoints3d;
        pr.hand_global_orient = hr.global_orient;
        $currentHandPose = pr;
        return false;
      }
      return true;
    });
  };

  const updatePoseData = (data: Array<PoseRecord>) => {
    if (data && data.length) {
      let zAdjust = 0;

      allPosePoints = {};
      allPoseExtents = {};
      minCoords = [null, null, null];
      maxCoords = [null, null, null];
      sceneMidpoint = [0, 0, 0];

      let newPosePoints: { [pose_idx: number]: number[][] } = {};
      posePointColors = {};

      data.forEach((pr: PoseRecord) => {
        if (!pr.keypoints3d || pr.hidden === true) return;

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
        posePointColors[pr.pose_idx] = 0x00ff00;
        newPosePoints[pr.pose_idx] = projCoords;
      });

      for (const posePoints of Object.values(newPosePoints)) {
        [minCoords, maxCoords] = get3DPoseExtent(
          posePoints,
          minCoords,
          maxCoords,
        );
      }

      zAdjust = -(maxCoords[2] + minCoords[2]);
      minCoords[2] += zAdjust;
      maxCoords[2] += zAdjust;

      let reprojCoords: number[][] = [];
      for (const [pose_idx, posePoints] of Object.entries(newPosePoints)) {
        reprojCoords = [];
        for (let r = 0; r < posePoints.length; r += 1) {
          reprojCoords.push([
            posePoints[r][0],
            posePoints[r][1],
            posePoints[r][2] + zAdjust,
          ]);
        }
        allPosePoints[pose_idx] = reprojCoords;
      }

      for (const [pose_idx, posePoints] of Object.entries(allPosePoints)) {
        allPoseExtents[pose_idx] = get3DPoseExtent(posePoints);
      }

      sceneMidpoint = [
        (minCoords[0] + maxCoords[0]) / 2,
        minCoords[1],
        (minCoords[2] + maxCoords[2]) / 2,
      ];
    }
    updateHandData(hands);
  };

  const updateHandData = (data: Array<HandRecord>) => {
    if (data && data.length) {
      allHandPoints = [];
      allHandExtents = [];
      handPointsToHand = {};

      const newHandPoints: number[][][] = [];
      handPointColors = [];
      data.forEach((hr: HandRecord, h: number) => {
        if (!hr.keypoints3d) return;
        let projCoords: number[][] = [];
        let wristCoords = null;

        poses.forEach((pr: PoseRecord) => {
          if (hr.pose_idx === pr.pose_idx) {
            if (pr.hidden === true) return;

            const w = hr.is_right ? 6 : 5; // * 3;
            wristCoords = [
              allPosePoints[hr.pose_idx][w][0],
              allPosePoints[hr.pose_idx][w][1],
              allPosePoints[hr.pose_idx][w][2],
            ];
            return;
          }
        });

        if (wristCoords === null) return;

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

        handPointsToHand[newHandPoints.length - 1] = h;
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

  const updatePointColors = (hoveredPoseIdx: number) => {
    for (const pose_idx of Object.keys(posePointColors)) {
      posePointColors[pose_idx] =
        hoveredPoseIdx === parseInt(pose_idx) ? 0xff00ff : 0x00ff00;
    }
  };

  const updatePoseLines = (thesePosePoints: {
    [pose_idx: number]: number[][];
  }) => {
    // Given a set of pose points, make lines connecting the armature points.
    // Drawing these declaratively/reactively, as is done for the actual
    // armature points, doesn't seem to work well with threlte.
    allPoseLines = [];
    for (const [_, posePoints] of Object.entries(thesePosePoints)) {
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
    for (let h = 0; h < theseHandPoints.length; h += 1) {
      const handPoints: number[][] = theseHandPoints[h];
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

  $: updatePoseData(poses);
  $: updateHandData(hands);

  $: updatePoseLines(allPosePoints);
  $: updateHandLines(allHandPoints);

  $: updatePointColors(hoveredPoseIdx);
</script>

{#each Object.entries(allPosePoints) as [pose_idx, posePoints], pp}
  <T.Mesh
    position.x={(allPoseExtents[pose_idx][0][0] +
      allPoseExtents[pose_idx][1][0]) /
      2}
    position.y={(allPoseExtents[pose_idx][0][1] +
      allPoseExtents[pose_idx][1][1]) /
      2}
    position.z={(allPoseExtents[pose_idx][0][2] +
      allPoseExtents[pose_idx][1][2]) /
      2}
    on:click={() => {
      poses.every((pose) => {
        if (pose.pose_idx === parseInt(pose_idx)) {
          $currentPose = pose;
          return false;
        }
        return true;
      });
    }}
    on:pointerover={() => {
      hoveredPoseIdx = parseInt(pose_idx);
    }}
    on:pointerout={() => {
      hoveredPoseIdx = undefined;
    }}
  >
    <T.BoxGeometry
      args={[
        2 +
          Math.abs(
            allPoseExtents[pose_idx][0][0] - allPoseExtents[pose_idx][1][0],
          ),
        2 +
          Math.abs(
            allPoseExtents[pose_idx][0][1] - allPoseExtents[pose_idx][1][1],
          ),
        2 +
          Math.abs(
            allPoseExtents[pose_idx][0][2] - allPoseExtents[pose_idx][1][2],
          ),
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
      <T.MeshPhongMaterial color={posePointColors[pose_idx]} />
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
      setSearchHandPose(hands[handPointsToHand[hp]]);
    }}
    on:pointerover={() => {
      handPointColors[hp] = 0xff00ff;
    }}
    on:pointerout={() => {
      handPointColors[hp] = hands[hp].is_right ? 0x00ff00 : 0xff0000;
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
<T.DirectionalLight color={0xffffff} position={[0, 0, 1]} />
<T.AmbientLight intensity={0.3} />
