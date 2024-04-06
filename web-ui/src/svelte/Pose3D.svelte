<script lang="ts">
  import * as THREE from "three";
  import { onMount } from "svelte";

  import { COCO_13_SKELETON, COCO_COLORS } from "../lib/poseutils";

  export let pose: PoseRecord;

  let canvas: HTMLCanvasElement;
  let renderer: THREE.WebGLRenderer;
  let camera: THREE.PerspectiveCamera;
  let scene: THREE.Scene;
  let poseGroup: THREE.Group;

  let dummyobject: THREE.Group;
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
    dummyobject.rotation.setFromQuaternion(poseGroup.quaternion);

    zAxis.set(1, 0, 0).applyQuaternion(poseGroup.quaternion);
    yAxis.set(0, 1, 0).applyQuaternion(poseGroup.quaternion);

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

  const drawPose = (pose: PoseRecord) => {
    const poseCoords = pose.global3d_coco13;
    let pose3D = [];

    for (let i = 0; i < poseCoords.length; i += 3) {
      pose3D.push(
        poseCoords.slice(i, i + 3).map((point) => Math.round(point * 100)),
      );
    }

    const allX = pose3D.map((point) => point[0]);
    const allY = pose3D.map((point) => point[1]);
    const allZ = pose3D.map((point) => point[2]);

    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);

    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);

    const minZ = Math.min(...allZ);
    const maxZ = Math.max(...allZ);

    renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
      canvas,
    });
    scene = new THREE.Scene();

    const poseWidth = maxX - minX;
    const poseHeight = maxY - minY;
    const poseDepth = maxZ - minZ;

    const fov = 90;
    const aspect = 1;
    const near = 1;
    const far = poseDepth * 8;
    camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
    camera.position.z = poseDepth * 3;

    const color = 0xffffff;
    const intensity = 3;
    const light = new THREE.DirectionalLight(color, intensity);
    light.position.set(0, 0, poseDepth * 4);
    scene.add(light);

    poseGroup = new THREE.Group();

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

      poseGroup.add(cube);
    }

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
      poseGroup.add(line);
    });

    scene.add(poseGroup);

    renderer.render(scene, camera);

    function render() {
      if (
        mouseIsClicked &&
        lastMousePosition.x !== mouseX &&
        lastMousePosition.y !== mouseY
      ) {
        // Calculate the change in mouse position
        const dx = mouseX - lastMousePosition.x;
        const dy = mouseY - lastMousePosition.y;

        dummyobject.rotation.z += -dy * 0.01;
        dummyobject.rotation.y += dx * 0.01;

        quaternion.setFromEuler(dummyobject.rotation);

        poseGroup.quaternion.copy(quaternion);

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
    dummyobject = poseGroup.clone();
    quaternion = new THREE.Quaternion();
    zAxis = new THREE.Vector3(0, 0, 1);
    yAxis = new THREE.Vector3(0, 1, 0);

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mousemove", handleMouseMove);

    drawPose(pose);
  });

  $: drawPose(pose);
</script>

<div class="card stretch-vert variant-ghost-tertiary drop-shadow-lg">
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
