<script>
	import { PoseLandmarker, FilesetResolver, DrawingUtils } from '@mediapipe/tasks-vision';
	import { Loading } from 'carbon-components-svelte';

	let /** @type HTMLVideoElement */ videoElement;
	let /** @type HTMLCanvasElement */ canvasElement;

	let /** @type PoseLandmarker */ poseLandmarker;
	let /** @type CanvasRenderingContext2D */ canvasCtx;
	let /** @type DrawingUtils */ drawingUtils;

	const init = async () => {
		const vision = await FilesetResolver.forVisionTasks('src/lib/wasm');
		poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
			baseOptions: {
				modelAssetPath: 'src/lib/pose_landmarker_full.task',
				delegate: 'GPU'
			},
			runningMode: 'VIDEO',
			numPoses: 1
		});

		canvasCtx = /** @type {CanvasRenderingContext2D} */ (canvasElement.getContext('2d'));
		drawingUtils = new DrawingUtils(canvasCtx);
		videoElement.addEventListener('loadeddata', predictWebcam);

		return await navigator.mediaDevices
			.getUserMedia({ video: true, audio: false })
			.then((stream) => (videoElement.srcObject = stream))
			.catch((err) => {
				console.error(`Error during webcam setup: ${err}`);
			});
	};

	const predictWebcam = async () => {
		poseLandmarker.detectForVideo(videoElement, performance.now(), (result) => {
			canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
			for (const landmark of result.landmarks) {
				drawingUtils.drawLandmarks(landmark, {
					radius: 3,
					lineWidth: 1,
					fillColor: 'transparent'
				});
				drawingUtils.drawConnectors(landmark, PoseLandmarker.POSE_CONNECTIONS, {
					lineWidth: 1
				});
			}
		});

		videoElement.requestVideoFrameCallback(predictWebcam);
	};
</script>

<section>
	<!-- svelte-ignore a11y_media_has_caption -->
	<video bind:this={videoElement} autoplay playsinline></video>
	<canvas bind:this={canvasElement} class="output_canvas"></canvas>
	{#await init()}
		<div>
			<Loading withOverlay={false} />
			Loading Webcam...
		</div>
	{/await}
</section>

<style>
	section {
		position: relative;

		div {
			align-items: center;
			display: flex;
			flex-direction: column;
			gap: 1rem;
			left: 0;
			position: absolute;
			top: 50%;
			translate: 0 -50%;
			width: 100%;
		}
	}

	video,
	canvas {
		width: 100%;
	}

	canvas {
		height: 100%;
		left: 0;
		position: absolute;
		top: 0;
	}
</style>
