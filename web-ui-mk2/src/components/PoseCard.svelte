<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html } from 'layercake';
	import ImageReference from 'carbon-icons-svelte/lib/ImageReference.svelte';
	import { getVideoData } from '$lib/data-fetching';
	import Overlay from '../ui-components/Overlay.svelte';
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

<div class:pose-card={true} {...props}>
	<LayerCake>
		<Overlay>
			{#snippet bottomLeft()}
				Frame #{sourcePose.frame}
				<br />
				Pose #{sourcePose.pose_idx + 1}
			{/snippet}
			{#snippet topRight()}
				<button onclick={() => showFrameModal()}><ImageReference /></button>
			{/snippet}
		</Overlay>
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
				<Pose poseData={sourcePose.keypoints} bbox={sourcePose.bbox} />
			</Canvas>
		{/if}
	</LayerCake>
	<aside>
		<span>{sourcePose.video_name.split('.').slice(0, -1).join('.')}</span>
		<!-- <span>Time: {formatSeconds(sourcePose.frame / sourcePose.video.fps)}</span> -->
	</aside>
</div>

<FrameModal bind:this={frameModal} />

<style>
	.pose-card {
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		flex-direction: column;
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;

		&:hover :global(.overlay) {
			opacity: 1;
		}

		& :global(.bottom-left) {
			font-size: 0.8rem;
		}
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
