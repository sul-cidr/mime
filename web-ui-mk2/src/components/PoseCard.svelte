<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html } from 'layercake';
	import { getKeypointsBounds, getKeypointsDimensions } from '$lib/pose-utils';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose} sourcePose Pose to be presented
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();
</script>

<div>
	<LayerCake>
		<Html zIndex={0}>
			{@const { video_id, frame, norm, keypoints, pose_idx } = sourcePose}
			{@const dims = `${getKeypointsBounds(keypoints).join(',')}|${getKeypointsDimensions(norm).join(',')}`}
			<img
				src={`${$page.data.apiBase}/frame/resize/${video_id}/${frame}/${dims}/`}
				alt={`Frame ${frame}, Pose: ${pose_idx + 1}`}
			/>
		</Html>
		<Canvas zIndex={1}>
			<Pose poseData={sourcePose.norm} normalizedPose={true} />
		</Canvas>
	</LayerCake>
</div>

<style>
	div {
		aspect-ratio: 5 / 6;
		background-color: rgba(0, 0, 0, 0.5);
		outline: 1px solid var(--primary);
		position: relative;
		width: 180px;
	}

	img {
		height: 100%;
		width: 100%;
		object-fit: contain;
	}
</style>
