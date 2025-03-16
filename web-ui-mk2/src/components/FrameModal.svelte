<script>
	import CloseFilled from 'carbon-icons-svelte/lib/CloseFilled.svelte';
	import { getPoseData } from '$lib/data-fetching';
	import Frame from './Frame.svelte';
	import Modal from '../ui-components/Modal.svelte';
	import Overlay from '../ui-components/Overlay.svelte';

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
		<Overlay>
			{#snippet topLeft()}
				{video?.video_name}, Frame {frame}
			{/snippet}
			{#snippet topRight()}
				<button onclick={modal.close}><CloseFilled /></button>
			{/snippet}
		</Overlay>
	{/if}
{/snippet}

<Modal bind:this={modal} {body} class="frame-modal" />

<style>
	:global(dialog.frame-modal) {
		/* override the default max-width defined in Modal.svelte */
		max-width: fit-content;
		overflow: hidden;
	}

	:global(dialog.frame-modal:hover .overlay) {
		opacity: 1;
	}
</style>
