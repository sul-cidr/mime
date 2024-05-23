<script>
	import { PoseLandmarker, FilesetResolver, DrawingUtils } from '@mediapipe/tasks-vision';
	import { NumberInput, Button, Loading } from 'carbon-components-svelte';
	import Camera from 'carbon-icons-svelte/lib/Camera.svelte';
	import CloseLarge from 'carbon-icons-svelte/lib/CloseLarge.svelte';
	import Search from 'carbon-icons-svelte/lib/Search.svelte';

	import {
		BLAZE_33_TO_COCO_13,
		COCO_13_SKELETON,
		COCO_COLORS,
		segmentKeypoints,
		shiftNormalizeRescalePoseCoords
	} from '$lib/pose-utils';

	/**
	 * @typedef {Object} WebcamPoseInputProps
	 * @property {function} setSourcePose Function to set the selected pose in the parent component
	 */

	/** @type {WebcamPoseInputProps} */
	let { setSourcePose } = $props();

	let /** @type HTMLVideoElement */ videoElement;
	let /** @type HTMLCanvasElement */ canvasElement;
	let /** @type CanvasRenderingContext2D */ canvasCtx;

	let /** @type PoseLandmarker */ poseLandmarker;
	let /** @type DrawingUtils */ drawingUtils;

	let capturedPose = $state();

	const scaleFactor = 1;
	const normalizedPose = true;
	const width = 290;
	const normalizationFactor = normalizedPose ? width / 100 : 1;

	/**
	 * @param {CanvasRenderingContext2D} context
	 * @param {Array<Array<number>>} segments
	 * @returns {void}
	 */
	const draw = (context, segments) => {
		COCO_13_SKELETON.forEach(([from, to], i) => {
			let fromX, fromY, toX, toY, fromConfidence, toConfidence;
			[fromX, fromY, fromConfidence = null] = segments[from - 1];
			[toX, toY, toConfidence = null] = segments[to - 1];
			if (fromConfidence === 0 || toConfidence === 0) return;
			if ([fromX, fromY, toX, toY].some((x) => x === -1)) return;

			context.lineWidth = scaleFactor > 0.8 ? 3 : 2;
			context.strokeStyle = COCO_COLORS[i];

			context.beginPath();
			context.moveTo(
				fromX * normalizationFactor * scaleFactor,
				fromY * normalizationFactor * scaleFactor
			);
			context.lineTo(
				toX * normalizationFactor * scaleFactor,
				toY * normalizationFactor * scaleFactor
			);
			context.stroke();
		});
	};

	/**
	 * @param {Coco13Pose[]} landmarks
	 * @returns {MinimalPose}
	 */
	const landmarksToCoco13 = (landmarks) => {
		const coco13Pose = BLAZE_33_TO_COCO_13.map((i) => landmarks[0][i]);

		// Project the pose coords into the image space for 2D and view-invariant searching.
		const bbox = videoElement.getBoundingClientRect();
		const projCoco13Pose = coco13Pose.map((c) => ({ x: c.x * bbox.width, y: c.y * bbox.height }));
		const searchPose = shiftNormalizeRescalePoseCoords(projCoco13Pose);
		return searchPose;
	};

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

		const webcamReady = new Promise((resolve) => {
			videoElement.addEventListener('loadeddata', () => {
				runWebcamPosePrediction();
				resolve(true);
			});
		});

		navigator.mediaDevices
			.getUserMedia({ video: true, audio: false })
			.then((stream) => (videoElement.srcObject = stream))
			.catch((err) => {
				console.error(`Error during webcam setup: ${err}`);
			});

		return webcamReady;
	};

	const runWebcamPosePrediction = async () => {
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

		if (!capturedPose) videoElement.requestVideoFrameCallback(runWebcamPosePrediction);
	};

	const grab = () => {
		const captureCanvas = document.createElement('canvas');
		const captureContext = /** @type CanvasRenderingContext2D */ (captureCanvas.getContext('2d'));
		const { width, height } = videoElement.getBoundingClientRect();
		captureCanvas.width = width;
		captureCanvas.height = height;
		captureContext.drawImage(videoElement, 0, 0, width, height);

		poseLandmarker.detectForVideo(videoElement, performance.now(), (result) => {
			const poseData = landmarksToCoco13(result.landmarks).keypoints;
			capturedPose = [...poseData];
			const segments = segmentKeypoints(poseData, 2);
			draw(captureContext, segments);
			/** @type {HTMLImageElement} */ (document.getElementById('captured')).src =
				captureCanvas.toDataURL('image/png');
		});
	};
</script>

<section>
	{#await init()}
		<div class="loading">
			<Loading withOverlay={false} />
			Loading Webcam...
		</div>
	{:then}
		<div class="controls">
			<NumberInput label="Delay" size="sm" value={0} min={0} max={10} />
			<Button size="small" icon={Camera} onclick={grab}>Grab</Button>
		</div>
	{/await}
	<!-- svelte-ignore a11y_media_has_caption -->
	<div class="live">
		<video bind:this={videoElement} autoplay playsinline></video>
		<canvas bind:this={canvasElement} class="output_canvas"></canvas>
	</div>

	<div class="captured" class:ready={capturedPose}>
		<div class="controls">
			<Button size="small" icon={Search} class="search" onclick={() => setSourcePose(capturedPose)}>
				Search
			</Button>
			<Button
				size="small"
				kind="secondary"
				icon={CloseLarge}
				class="clear"
				onclick={() => {
					capturedPose = false;
					runWebcamPosePrediction();
				}}>Clear</Button
			>
		</div>
		<img id="captured" alt="Captured Pose" />
	</div>
</section>

<style>
	section,
	section > div {
		position: relative;
	}

	.loading {
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

	.live {
		margin-top: 1rem;
	}

	video,
	canvas,
	img {
		transform: rotateY(180deg);
		width: 100%;
	}

	canvas {
		height: 100%;
		left: 0;
		position: absolute;
		top: 0;
	}

	.captured {
		display: none;
		position: absolute;
		top: 0;
		background: white;
	}

	.captured.ready {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.controls {
		align-items: center;
		display: flex;
		gap: 1rem;
		justify-content: space-between;

		& :global(.bx--number) {
			align-items: center;
			flex-direction: row;
			gap: 1rem;
		}

		& :global(.bx--number--sm.bx--number input[type='number']) {
			padding-right: 6rem;
		}

		& :global(.bx--number input[type='number']) {
			min-width: unset;
			padding-left: 1rem;
		}
	}
</style>
