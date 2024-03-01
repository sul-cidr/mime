<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { currentVideo, currentPose } from "@svelte/stores";
  import {
    PoseLandmarker,
    FilesetResolver,
    DrawingUtils,
  } from "@mediapipe/tasks-vision";

  // XXX This is shared between the Python and JS code, so should be set
  // somewhere accessible to both
  const POSE_MAX_DIM = 100;

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
    videoElement.srcObject.getTracks().forEach((track) => {
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
      window.requestAnimationFrame(predictWebcam);
    }
  };

  const startStopWebcam = () => {
    webcamRunning = !webcamRunning;
    if (webcamRunning) {
      predictWebcam();
    }
  };

  const setSearchPose = () => {
    // XXX Most of these conversions should be kept in a utils code file,
    // probably poseutils.tx.
    // Note that they're also a direct re-implementation of some of the Python
    // utils in pose_functions.py

    const blaze33ToCoco17Coords = [
      0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 26, 28,
    ];
    const blaze33ToCoco13Coords = [
      0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 26, 28,
    ];
    const coco13Pose = blaze33ToCoco13Coords.map(
      (i) => currentPoseLandmarks[0][i],
    );
    const coco17Pose = blaze33ToCoco17Coords.map(
      (i) => currentPoseLandmarks[0][i],
    );

    // It's easier to work with pose coords when they're re-projected into the
    // image space.
    let projCoco13Pose = [];
    coco13Pose.forEach((c) => {
      projCoco13Pose.push([c.x * videoWidth, c.y * videoHeight]);
    });

    let xmin = null;
    let xmax = null;
    let ymin = null;
    let ymax = null;

    projCoco13Pose.forEach((c) => {
      xmin = xmin === null ? c[0] : Math.min(xmin, c[0]);
      xmax = xmax === null ? c[0] : Math.max(xmax, c[0]);
      ymin = ymin === null ? c[1] : Math.min(ymin, c[1]);
      ymax = ymax === null ? c[1] : Math.max(ymax, c[1]);
    });
    const poseWidth = xmax - xmin;
    const poseHeight = ymax - ymin;

    const scaleFactor = POSE_MAX_DIM / Math.max(poseWidth, poseHeight);

    let xRecenter = 0;
    let yRecenter = 0;

    if (poseWidth >= poseHeight) {
      yRecenter = Math.round((POSE_MAX_DIM - scaleFactor * poseHeight) / 2);
    } else {
      xRecenter = Math.round((POSE_MAX_DIM - scaleFactor * poseWidth) / 2);
    }

    let normCoco13Pose = [];

    projCoco13Pose.forEach((c) => {
      normCoco13Pose.push([
        Math.round((c[0] - xmin) * scaleFactor + xRecenter),
        Math.round((c[1] - ymin) * scaleFactor + yRecenter),
      ]);
    });

    // XXX Next: try to use this data to create a PoseRecord that can be
    // assigned to $currentPose (without crashing the rest of the app) and
    // then used as the basis of a similar poses search.
  };

  onMount(async () => {
    startup();
  });
  onDestroy(async () => {
    shutdown();
  });
</script>

<div class="w-modal-wide card variant-glass-primary flex flex-row items-center">
  <div class="flex flex-col items-center w-full">
    <header class="card-header font-bold">
      <h3>Use the webcam to search for a pose</h3>
    </header>
    <div class="flex flex-row justify-center w-full">
      <button
        type="button"
        class="btn-sm px-2 variant-ghost"
        on:click={startStopWebcam}>Pause/Unpause</button
      >
      <button
        type="button"
        class="btn-sm px-2 variant-ghost"
        disabled={!currentPoseLandmarks}
        on:click={setSearchPose}>Search pose</button
      >
    </div>
    <div class="vidcontainer">
      {#if !webcamRunning && !currentPoseLandmarks}
        <div class="waiting-msg">Waiting for webcam...</div>
      {/if}
      <video id="webcam" autoplay playsinline />
      <canvas class="output_canvas" id="output_canvas" />
    </div>
    <div class="flex flex-row justify-center w-full">
      <button
        type="button"
        class="btn-sm px-2 variant-ghost"
        on:click={() => {
          shutdown(true);
        }}>Close</button
      >
    </div>
  </div>
</div>

<style>
  .vidcontainer {
    position: relative;
  }

  .vidcontainer canvas,
  #webcam {
    position: absolute;
  }

  #webcam {
    border: 1px solid black;
    transform: rotateY(180deg);
    -webkit-transform: rotateY(180deg);
    -moz-transform: rotateY(180deg);
  }

  #output_canvas {
    position: relative;
    transform: rotateY(180deg);
    -webkit-transform: rotateY(180deg);
    -moz-transform: rotateY(180deg);
  }
</style>
