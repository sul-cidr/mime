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
</script>

<div {...props}>
	<LayerCake>
		<Html zIndex={0}>
			{@const { video_id, frame, norm, keypoints, pose_idx } = sourcePose}
			{@const dims = getKeypointsBounds(keypoints).join(',')}
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
				<Pose poseData={sourcePose.norm} normalizedPose={true} />
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
