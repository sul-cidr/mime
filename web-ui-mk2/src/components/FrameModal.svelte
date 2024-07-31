<script>
	import { getPoseData } from '$lib/data-fetching';
	import Frame from './Frame.svelte';
	import Modal from '../ui-components/Modal.svelte';

	let showModal = $state(false);

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
		showModal = true;
	};
</script>

{#snippet body()}
	{#if video}
		<Frame {video} {frame} poseData={framePoseData} {selectedPoseIdx} />
	{/if}
{/snippet}

<Modal bind:showModal {body} class="frame-modal" />

<style>
	:global(dialog.frame-modal) {
		/* override the default max-width defined in Modal.svelte */
		max-width: fit-content;
	}
</style>
