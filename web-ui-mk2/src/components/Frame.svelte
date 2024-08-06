<script>
	import { page } from '$app/stores';
	import { LayerCake, Canvas, Html, Svg } from 'layercake';
	import Pose from './Pose.svelte';

	/**
	 * @typedef {Object} FrameProps
	 * @property {VideoRecord} video
	 * @property {number} frame
	 * @property {PoseRecord[]} poseData
	 * @property {number} selectedPoseIdx
	 */

	/** @type {FrameProps} */
	let { video, frame, poseData, selectedPoseIdx } = $props();
	const { id: videoId, width: frameWidth, height: frameHeight } = video;

	let displayWidthPx = $state();
	let scaleFactor = $derived(displayWidthPx / frameWidth);
</script>

<div
	bind:clientWidth={displayWidthPx}
	class="frame-display"
	style="
	  aspect-ratio: {frameWidth}/{frameHeight};
		width: min(80vw, {frameWidth}px, calc(80vh * ({frameWidth}/{frameHeight})) 
	"
>
	<LayerCake>
		<Html zIndex={0}>
			<img
				src="{$page.data.apiBase}/frame/{videoId}/{frame}/"
				alt="Frame {frame}"
				style="width: 100%; aspect-ratio: {frameWidth}/{frameHeight}"
			/>
		</Html>
		{#if poseData && poseData.length}
			{#each poseData as pose}
				<Canvas zIndex={1}>
					<Pose
						poseData={pose.keypoints}
						pose4dhData={pose.keypoints4dh}
						faceData={pose.face_landmarks}
						{scaleFactor}
						fitToCanvas={false}
					/>
				</Canvas>
			{/each}
			<Svg viewBox="0 0 {frameWidth} {frameHeight}" zIndex={2}>
				<defs>
					<filter x="0" y="0" width="1" height="1" id="solid">
						<feFlood flood-color="white" result="bg" />
						<feMerge>
							<feMergeNode in="bg" />
							<feMergeNode in="SourceGraphic" />
						</feMerge>
					</filter>
				</defs>
				{#each poseData as pose, i}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_mouse_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<rect
						data-id={i}
						x={pose.bbox[0]}
						y={pose.bbox[1]}
						height={pose.bbox[3]}
						width={pose.bbox[2]}
						class:selected={selectedPoseIdx === pose.pose_idx}
					/>
					{#if pose.face_bbox}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<rect
							x={pose.face_bbox[0]}
							y={pose.face_bbox[1]}
							height={pose.face_bbox[3]}
							width={pose.face_bbox[2]}
							class:face={true}
							class:selected={selectedPoseIdx === pose.pose_idx}
						/>
					{/if}
					<text x={pose.bbox[0] + 2} y={pose.bbox[1] + 5}>
						#{pose.pose_idx + 1}
					</text>
				{/each}
			</Svg>
		{/if}
	</LayerCake>
</div>

<style>
	rect {
		cursor: pointer;
		fill: none;
		pointer-events: visible;
		stroke-width: 4;
		stroke: white;

		&.selected,
		&:hover {
			fill-opacity: 0.2;
			fill: white;
			stroke-width: 10;
			stroke: red;
		}
	}

	text {
		dominant-baseline: hanging;
		fill: white;
		font-size: 100px;
		stroke: white;
	}

	.frame-display {
		background: radial-gradient(circle at 50% -250%, #333, #111827, #333);
		box-shadow: inset 0px 0px 30px 0px #666;
	}
</style>
