<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html } from 'layercake';
	import { getVideoData } from '$lib/data-fetching';
	import { getKeypointsBounds } from '$lib/pose-utils';
	import FrameModal from './FrameModal.svelte';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {PoseRecord} sourcePose Pose to be presented
	 * @property {boolean} showPose
	 * @property {string} [class]
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose, showPose, ...props } = $props();

	let frameModal = $state();

	const showFrameModal = async () => {
		const video = (await getVideoData()).find(
			(/** @type {VideoRecord} */ video) => video.id === sourcePose.video_id
		);
		frameModal.show(video, sourcePose.frame, sourcePose.pose_idx);
	};

	const getBboxOffset = (bbox, keypoints) => {
		const kpBB = getKeypointsBounds(sourcePose.keypoints);

		const [x, y, w, h] = bbox;
		const [x1, y1, x2, y2] = kpBB;

		const POSE_MAX_DIM = 100;

		const scaleFactor = 100 / 2160;

		let y_recenter;
		let x_recenter;

		if (w >= h) {
			x_recenter = 0;
			y_recenter = Math.round((POSE_MAX_DIM - h * scaleFactor) / 2);
		} else {
			x_recenter = Math.round((POSE_MAX_DIM - w * scaleFactor) / 2);
			y_recenter = 0;
		}

		// for i, coords in enumerate(pose_coords):
		//     # Coordinates with confidence values of 0 are not modified; these should not
		//     # be used in any pose representations or calculations, and often (but not
		//     # always) already have 0,0 coordinates.
		//     if coords[2] == 0:
		//         continue
		//     pose_coords[i] = [
		//         round(coords[0] * scale_factor + x_recenter),
		//         round(coords[1] * scale_factor + y_recenter),
		//         coords[2],
		//     ]

		return [x_recenter, y_recenter];
	};

	console.log(sourcePose.keypoints);
	console.log(sourcePose.bbox);
	console.log(getKeypointsBounds(sourcePose.keypoints));
</script>

<div {...props}>
	<LayerCake>
		<Html zIndex={0}>
			{@const { video_id, frame, pose_idx, bbox } = sourcePose}
			{@const dims = bbox.join(',')}
			<img
				src="{$page.data.apiBase}/frame/excerpt/{video_id}/{frame}/{dims}/"
				alt="Frame {frame}, Pose: {pose_idx + 1}"
				onload={({ target }) => {
					/** @type {HTMLImageElement} */ (target).style.opacity = '1';
					/** @type {HTMLImageElement} */ (target).style.transform = 'scale(1)';
				}}
			/>
		</Html>
		{#if showPose}
			<Canvas zIndex={1}>
				<Pose
					poseData={sourcePose.norm}
					normalizedPose={true}
					bboxOffset={getBboxOffset(sourcePose.bbox, sourcePose.keypoints)}
				/>
			</Canvas>
		{/if}
	</LayerCake>
	<aside>
		<span>{sourcePose.video_name}</span>
		<span>Frame {sourcePose.frame} (#{sourcePose.pose_idx + 1})</span>
		<!-- <span>Time: {formatSeconds(sourcePose.frame / sourcePose.video.fps)}</span> -->
		<button onclick={() => showFrameModal()}>Show Frame</button>
	</aside>
</div>

<FrameModal bind:this={frameModal} />

<style>
	div {
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		flex-direction: column;
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;
	}

	aside {
		background: var(--panel-background);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.5rem;
	}

	img {
		height: 100%;
		object-fit: contain;
		opacity: 0;
		transform-origin: center;
		transform: scale(1.1);
		transition:
			opacity 0.5s,
			transform 0.7s;
		width: 100%;
	}
</style>
