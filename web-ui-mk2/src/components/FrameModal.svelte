<script>
	import CloseFilled from 'carbon-icons-svelte/lib/CloseFilled.svelte';
	import { getPoseData } from '$lib/data-fetching';
	import Frame from './Frame.svelte';
	import Modal from '../ui-components/Modal.svelte';

	let modal = $state();

	/** @type {VideoRecord|undefined} */
	let video = $state();
	let frame = $state();
	let framePoseData = $state();
	let selectedPoseIdx = $state();

	/**
	 * @param {VideoRecord} _video
	 * @param {number} _frame
	 * @param {number} _selectedPoseIdx
	 */
	export const show = async (_video, _frame, _selectedPoseIdx) => {
		video = _video;
		frame = _frame;
		selectedPoseIdx = _selectedPoseIdx;
		framePoseData = await getPoseData(video.id, frame);
		modal.show();
	};
</script>

{#snippet body()}
	{#if video}
		<Frame {video} {frame} poseData={framePoseData} {selectedPoseIdx} />
		<div class="overlay">
			<span>
				{video.video_name}, Frame {frame}
			</span>
			<div class="controls">
				<button onclick={modal.close}><CloseFilled /></button>
			</div>
		</div>
	{/if}
{/snippet}

<Modal bind:this={modal} {body} class="frame-modal" />

<style>
	:global(dialog.frame-modal) {
		/* override the default max-width defined in Modal.svelte */
		max-width: fit-content;
		overflow: hidden;

		:global(&:hover) .overlay {
			opacity: 1;
		}
	}

	.overlay {
		color: white;
		height: 100%;
		left: 0;
		opacity: 0;
		pointer-events: none;
		position: absolute;
		top: 0;
		transition: opacity 0.3s;
		width: 100%;
		z-index: 100;

		span,
		.controls {
			background-color: rgba(0, 0, 0, 0.5);
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
			font-size: 1.3rem;
			padding: 10px;
			pointer-events: all;
		}
		span {
			left: 0;
			position: absolute;
			top: 0;
		}

		.controls {
			position: absolute;
			right: 0;
			top: 0;
		}

		button {
			background: none;
			border: none;
			color: white;
			cursor: pointer;
			font-size: 12px;
			transform-origin: center;
			transition: scale 0.1s;

			&:hover {
				scale: 1.3;
			}
		}
	}
</style>
