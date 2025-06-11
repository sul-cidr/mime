<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html } from 'layercake';
	import ImageReference from 'carbon-icons-svelte/lib/ImageReference.svelte';
	import { getVideoData } from '$lib/data-fetching';
	import Overlay from '../ui-components/Overlay.svelte';
	import FrameModal from './FrameModal.svelte';
	import Hands from './Hands.svelte';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {PoseRecord|MinimalPose|HandForDrawing} sourcePose Pose or hand to be presented
	 * @property {boolean} [showPose = false]
	 * @property {boolean} [showHands = false]
	 * @property {string} [class]
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose, showPose = false, showHands = false, ...props } = $props();

	let frameModal = $state();

	const showFrameModal = async () => {
		const video = (await getVideoData()).find(
			(/** @type {VideoRecord} */ video) =>
				video.id === /** @type {PoseRecord} */ (sourcePose).video_id
		);
		frameModal.show(
			video,
			/** @type {PoseRecord} */ (sourcePose).frame,
			/** @type {PoseRecord} */ (sourcePose).pose_idx,
			showPose,
			showHands
		);
	};
</script>

<div class="pose-card">
	<LayerCake>
		{#if 'frame' in sourcePose && 'pose_idx' in sourcePose}
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
		{/if}
		{#if 'keypoints' in sourcePose && showPose}
			<Canvas zIndex={1}>
				<Pose poseData={sourcePose.keypoints} bbox={sourcePose.bbox} />
			</Canvas>
		{/if}
		{#if showHands}
			<Canvas zIndex={1}>
				{#if ('rh_keypoints2d' in sourcePose && sourcePose.rh_keypoints2d) || ('lh_keypoints2d' in sourcePose && sourcePose.lh_keypoints2d)}
					<Hands
						handData={{
							rh_keypoints2d: sourcePose.rh_keypoints2d,
							lh_keypoints2d: sourcePose.lh_keypoints2d
						}}
						bbox={sourcePose.bbox}
					/>
				{/if}
			</Canvas>
		{/if}
	</LayerCake>
	{#if 'video_name' in sourcePose}
		<aside>
			<span>{sourcePose.video_name.split('.').slice(0, -1).join('.')}</span>
			<!-- <span>Time: {formatSeconds(sourcePose.frame / sourcePose.video.fps)}</span> -->
		</aside>
	{/if}
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
		height: 216px;

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
