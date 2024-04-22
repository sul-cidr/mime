<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { currentPose, currentVideo, webcamImage } from "@svelte/stores";
  import {
    blaze33ToCoco13Coords,
    getPoseExtent,
    shiftNormalizeRescalePoseCoords,
  } from "../lib/poseutils";
  import {
    PoseLandmarker,
    FilesetResolver,
    DrawingUtils,
  } from "@mediapipe/tasks-vision";
  import Pose from "./Pose.svelte";

  export let parent: any;

  let poseLandmarker = null;

  const videoWidth = 1024;
  let videoHeight = 0; // Determined by the input stream

  let webcamRunning = false;

  let videoElement = null;
  let canvasElement = null;
  let canvasCtx = null;
  let drawingUtils = null;

  let currentPoseLandmarks = null;
  let timerButtonClass = "";
  let cameraFlashClass = "";
  let timerCountdown = 5;

  let croppedImage = null;

  const startup = async () => {
    videoElement = document.getElementById("webcam") as HTMLVideoElement;
    canvasElement = document.getElementById(
      "output_canvas",
    ) as HTMLCanvasElement;

    if (!!navigator.mediaDevices?.getUserMedia === false) {
      videoElement.addEventListener("canplay", startup);
      return;
    }

    const vision = await FilesetResolver.forVisionTasks(
      // path/to/wasm/root
      //"https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm",
      "src/lib/wasm",
    );

    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "src/lib/pose_landmarker_full.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numPoses: 1,
    });

    canvasCtx = canvasElement.getContext("2d");
    drawingUtils = new DrawingUtils(canvasCtx);

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then(async (stream) => {
        videoElement.srcObject = stream;
        if (!webcamRunning) {
          let { width, height } = stream.getTracks()[0].getSettings();
          videoHeight = videoWidth / (width / height);
          if (isNaN(videoHeight)) {
            // If getTracks() doesn't work, try to get the webcam image
            // dimensions using this method for older browsers, from
            // https://stackoverflow.com/questions/47593336/how-can-i-detect-width-and-height-of-the-webcamera
            await new Promise(
              (resolve) => (videoElement.onloadedmetadata = resolve),
            );

            videoHeight =
              videoWidth / (videoElement.videoWidth / videoElement.videoHeight);
            // Finally if the height still can't be read from the camera,
            // just assume it's a 4:3 input
            if (isNaN(videoHeight)) {
              videoHeight = videoWidth / (4 / 3);
            }
          }

          videoElement.setAttribute("width", videoWidth);
          videoElement.setAttribute("height", videoHeight);
          canvasElement.setAttribute("width", videoWidth);
          canvasElement.setAttribute("height", videoHeight);
          webcamRunning = true;
        }
        videoElement.addEventListener("loadeddata", predictWebcam);
      })
      .catch((err) => {
        console.error(`Error during webcam setup: ${err}`);
      });
  };

  const shutdown = (triggerClose = false) => {
    videoElement.srcObject?.getTracks().forEach((track) => {
      track.stop();
    });
    if (triggerClose) {
      parent.onClose();
    }
  };

  let lastVideoTime = -1;
  const predictWebcam = async () => {
    if (videoWidth && videoHeight && poseLandmarker) {
      if (poseLandmarker.runningMode === "IMAGE") {
        await poseLandmarker.setOptions({ runningMode: "VIDEO" });
      }
      let startTimeMs = performance.now();
      if (lastVideoTime !== videoElement.currentTime) {
        lastVideoTime = videoElement.currentTime;
        poseLandmarker.detectForVideo(videoElement, startTimeMs, (result) => {
          currentPoseLandmarks = result.landmarks;
          canvasCtx.save();
          canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
          for (const landmark of result.landmarks) {
            drawingUtils.drawLandmarks(landmark, {
              radius: (data) =>
                DrawingUtils.lerp(data.from!.z, -0.15, 0.1, 5, 1),
            });
            drawingUtils.drawConnectors(
              landmark,
              PoseLandmarker.POSE_CONNECTIONS,
            );
          }
          canvasCtx.restore();
        });
      }
    }

    // Run prediction on the next frame
    if (webcamRunning === true) {
      if ("requestVideoFrameCallback" in HTMLVideoElement.prototype) {
        videoElement.requestVideoFrameCallback(predictWebcam);
      } else {
        window.requestAnimationFrame(predictWebcam);
      }
    }
  };

  const startStopWebcam = () => {
    webcamRunning = !webcamRunning;
    if (webcamRunning) {
      predictWebcam();
    }
  };

  const setSearchPose = () => {
    cameraFlashClass = "webcam_capturing";

    const coco13Pose = blaze33ToCoco13Coords.map(
      (i) => currentPoseLandmarks[0][i],
    );

    // Project the pose coords into the image space for 2D and view-
    // invariant searching.
    let projCoco13Pose = [];
    coco13Pose.forEach((c) => {
      projCoco13Pose.push({ x: c.x * videoWidth, y: c.y * videoHeight });
    });

    let projExtent = getPoseExtent(projCoco13Pose);

    const widthScaleFactor = videoElement.videoWidth / videoElement.width;
    const heightScaleFactor = videoElement.videoHeight / videoElement.height;

    // Crop the image to contain just the pose
    let cropCanvas = document.createElement("canvas");
    let cropCtx = cropCanvas.getContext("2d");
    cropCanvas.width = projExtent.w;
    cropCanvas.height = projExtent.h;

    cropCtx.drawImage(
      videoElement,
      projExtent.x * widthScaleFactor,
      projExtent.y * heightScaleFactor,
      projExtent.w * widthScaleFactor,
      projExtent.h * heightScaleFactor,
      0,
      0,
      projExtent.w,
      projExtent.h,
    );

    croppedImage = cropCanvas.toDataURL("image/png");
    $webcamImage = croppedImage;

    const searchPose = shiftNormalizeRescalePoseCoords(
      projCoco13Pose,
      $currentVideo.id,
      projExtent.x,
      projExtent.y,
      projExtent.w,
      projExtent.h,
    );

    let globalExtent = getPoseExtent(coco13Pose);

    // For 3D searching, the coordinates should be adjusted so that 0,0,0 is
    // roughly in the middle of the cuboid defined by the pose
    const cuboidScaleFactor =
      1 / Math.max(...[globalExtent.w, globalExtent.h, globalExtent.d]);

    let positive3dPose = [];
    coco13Pose.forEach((p) => {
      positive3dPose.push({
        x: p.x - globalExtent.x,
        y: p.y - globalExtent.y,
        z: p.z - globalExtent.z,
      });
    });

    let rescaled3dPose = [];
    positive3dPose.forEach((p) => {
      rescaled3dPose.push({
        x: p.x * cuboidScaleFactor,
        y: p.y * cuboidScaleFactor,
        z: p.z * cuboidScaleFactor,
      });
    });

    const midX = (globalExtent.w * cuboidScaleFactor) / 2;
    const midY = (globalExtent.h * cuboidScaleFactor) / 2;
    const midZ = (globalExtent.d * cuboidScaleFactor) / 2;

    let proj3dCoords = [];
    rescaled3dPose.forEach((p) => {
      proj3dCoords.push(p.x - midX, midY - p.y, midZ - p.z);
    });

    searchPose.global3d_coco13 = proj3dCoords;

    $currentPose = searchPose;

    setTimeout(() => {
      cameraFlashClass = "";
    }, 1000);
  };

  const waitThenCapture = () => {
    timerButtonClass = "timer_button_flash";
    setTimeout(() => {
      if (timerCountdown === 0) {
        setSearchPose();
        timerCountdown = 5;
        timerButtonClass = "";
      } else {
        timerCountdown -= 1;
        waitThenCapture();
      }
    }, 1000);
  };

  onMount(async () => {
    startup();
  });
  onDestroy(async () => {
    shutdown();
  });
</script>

<div
  class="w-modal-wide card variant-glass-primary pb-4 flex flex-row items-center"
>
  <div class="flex flex-col items-center w-full">
    <header class="card-header font-bold">
      <h3>Use the webcam to search for a pose</h3>
    </header>
    <div class="flex flex-row justify-center">
      <div class="flex">
        <button
          type="button"
          title="Pause/resume pose estimation on webcam"
          class="btn-sm px-2 variant-ghost"
          on:click={startStopWebcam}>Pause/Unpause</button
        >
        <span class="divider-vertical !border-l-8 !border-double"></span>
        <button
          type="button"
          title="Use current pose for search"
          class="btn-sm px-2 variant-ghost"
          disabled={!currentPoseLandmarks}
          on:click={setSearchPose}>Search pose</button
        >
        <button
          type="button"
          title="Capture search pose after 5 seconds"
          class="btn-sm px-2 variant-ghost {timerButtonClass}"
          disabled={!currentPoseLandmarks}
          on:click={waitThenCapture}>⏲ {timerCountdown} sec</button
        >
      </div>
      <span class="divider-vertical !border-l-8 !border-double"></span>
      <button
        type="button"
        title="Close the camera controls"
        class="btn-sm px-2 variant-ghost"
        on:click={() => {
          shutdown(true);
        }}>Close</button
      >
    </div>
    <div class="vidcontainer {cameraFlashClass}">
      {#if !webcamRunning && !currentPoseLandmarks}
        <div class="waiting-msg">Waiting for webcam...</div>
      {/if}
      <video id="webcam" autoplay playsinline />
      <canvas class="output_canvas" id="output_canvas" />
    </div>
  </div>
</div>

<style>
  .vidcontainer {
    position: relative;
    border: 5px solid #aaaaaa00;
  }

  .vidcontainer canvas,
  #webcam {
    position: absolute;
  }

  #webcam {
    transform: rotateY(180deg);
    -webkit-transform: rotateY(180deg);
    -moz-transform: rotateY(180deg);
    border: 1px solid black;
  }

  .webcam_capturing {
    border: 5px solid red;
  }

  #output_canvas {
    position: relative;
    transform: rotateY(180deg);
    -webkit-transform: rotateY(180deg);
    -moz-transform: rotateY(180deg);
  }

  .timer_button_flash {
    background: red;
  }
</style>
