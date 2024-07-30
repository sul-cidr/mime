<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html } from 'layercake';
	import { getKeypointsBounds } from '$lib/pose-utils';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {PoseRecord} sourcePose Pose to be presented
	 * @property {boolean} showPose
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose, showPose } = $props();
</script>

<div>
	<LayerCake>
		<Html zIndex={0}>
			{@const { video_id, frame, norm, keypoints, pose_idx } = sourcePose}
			{@const dims = getKeypointsBounds(keypoints).join(',')}
			{@const [, , h, w] = getKeypointsBounds(norm, false)}
			<img
				src={`${$page.data.apiBase}/frame/resize/${video_id}/${frame}/${dims}|${h},${w}/`}
				alt={`Frame ${frame}, Pose: ${pose_idx + 1}`}
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
	</aside>
</div>

<style>
	div {
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;
	}

	aside {
		display: flex;
		padding: 0.5rem;
		background: aliceblue;
		flex-direction: column;
		gap: 0.5rem;
	}

	img {
		height: 100%;
		width: 100%;
		object-fit: contain;
		opacity: 0;
		transform: scale(1.1);
		transform-origin: center;
		transition:
			opacity 0.5s,
			transform 0.7s;
	}
</style>
