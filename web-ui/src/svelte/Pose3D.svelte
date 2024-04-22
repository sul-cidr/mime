<script lang="ts">
  import * as THREE from "three";
  import { onMount } from "svelte";

  import { COCO_13_SKELETON, COCO_COLORS } from "../lib/poseutils";

  export let pose: PoseRecord;

  let canvas: HTMLCanvasElement;
  let renderer: THREE.WebGLRenderer;
  let camera: THREE.PerspectiveCamera;
  let scene: THREE.Scene;
  let poseObject: THREE.Group;

  let dummyObject: THREE.Group;
  let quaternion: THREE.Quaternion;
  let zAxis: THREE.Vector3;
  let yAxis: THREE.Vector3;

  let mouseIsClicked = false;
  let mouseX = 0;
  let mouseY = 0;
  let lastMousePosition = { x: 0, y: 0 };

  const handleMouseDown = (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dummyObject.rotation.setFromQuaternion(poseObject.quaternion);

    zAxis.set(1, 0, 0).applyQuaternion(poseObject.quaternion);
    yAxis.set(0, 1, 0).applyQuaternion(poseObject.quaternion);

    mouseIsClicked = true;
    lastMousePosition = { x: mouseX, y: mouseY };
  };

  const handleMouseUp = () => {
    mouseIsClicked = false;
  };

  const handleMouseMove = (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  };

  const drawPose = (pose: PoseRecord, canvas: HTMLCanvasElement) => {
    if (canvas === undefined) return;

    const poseCoords = pose.global3d_coco13;
    let pose3D = [];

    for (let i = 0; i < poseCoords.length; i += 3) {
      pose3D.push(
        poseCoords.slice(i, i + 3).map((point) => Math.round(point * 100)),
      );
    }

    const aspect = 1; // The canvas element will be stretched arbitrarily...

    renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
      canvas,
    });
    scene = new THREE.Scene();

    poseObject = new THREE.Group();
    const fov = 75;

    // Draw a cube at each armature point
    for (let p = 0; p < pose3D.length; p += 1) {
      const geometry = new THREE.BoxGeometry(10, 10, 10);
      const material = new THREE.MeshPhongMaterial({ color: 0x00ff00 });
      const cube = new THREE.Mesh(geometry, material);
      const centerPt = new THREE.Vector3(
        pose3D[p][0],
        pose3D[p][1],
        pose3D[p][2],
      );
      cube.position.copy(centerPt);

      poseObject.add(cube);
    }

    // Draw lines connecting the armature points
    COCO_13_SKELETON.forEach(([from, to], i) => {
      let fromX, fromY, fromZ, toX, toY, toZ;
      [fromX, fromY, fromZ] = pose3D[from! - 1]!;
      [toX, toY, toZ] = pose3D[to! - 1]!;

      let lineMaterial = new THREE.LineBasicMaterial({
        color: COCO_COLORS[i],
      });
      let linePoints = [];
      linePoints.push(new THREE.Vector3(fromX, fromY, fromZ));
      linePoints.push(new THREE.Vector3(toX, toY, toZ));
      let lineGeometry = new THREE.BufferGeometry().setFromPoints(linePoints);
      let line = new THREE.Line(lineGeometry, lineMaterial);
      poseObject.add(line);
    });

    // Shrink the 3D pose proportionally to fit in a 1x1x1 cube (where 1 is
    // the length of the longest side of the pose's bounding box/cuboid); the
    // cube is guaranteed to be visible within the 3D scene.
    const boundingBox = new THREE.Box3();
    boundingBox.setFromObject(poseObject);
    const sizeObj = new THREE.Vector3();
    boundingBox.getSize(sizeObj);
    const maxDim = Math.max(sizeObj.x, sizeObj.y, sizeObj.z);

    poseObject.scale.set(1 / maxDim, 1 / maxDim, 1 / maxDim);

    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(0, 0, 2);
    scene.add(light);

    camera = new THREE.PerspectiveCamera(fov, aspect, 0.1, 2);
    camera.position.z = 1.25;

    scene.add(poseObject);

    renderer.render(scene, camera);

    function render() {
      if (
        mouseIsClicked &&
        (lastMousePosition.x !== mouseX || lastMousePosition.y !== mouseY)
      ) {
        // Calculate the change in mouse position
        const dx = mouseX - lastMousePosition.x;
        const dy = mouseY - lastMousePosition.y;

        dummyObject.rotation.z += -dy * 0.01;
        dummyObject.rotation.y += dx * 0.01;

        quaternion.setFromEuler(dummyObject.rotation);

        poseObject.quaternion.copy(quaternion);

        // Update the last mouse position
        lastMousePosition.x = mouseX;
        lastMousePosition.y = mouseY;
      }

      renderer.render(scene, camera);

      requestAnimationFrame(render);
    }
    requestAnimationFrame(render);
  };

  onMount(() => {
    drawPose(pose, canvas);

    dummyObject = poseObject.clone();
    quaternion = new THREE.Quaternion();
    zAxis = new THREE.Vector3(0, 0, 1);
    yAxis = new THREE.Vector3(0, 1, 0);

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mousemove", handleMouseMove);
  });

  $: drawPose(pose, canvas);
</script>

<div class="card stretch-vert variant-ghost-tertiary drop-shadow-lg">
  <header class="p-2">3D Pose</header>
  <canvas bind:this={canvas} class="pose-canvas" />
</div>

<!-- 
  @component
  Render an individual pose as a canvas element.
  
  Usage:
    ```tsx
  <Pose3D pose={PoseRecord} />
  ```
-->

<style>
  .pose-canvas {
    width: 100%;
    height: 100%;
  }
</style>
