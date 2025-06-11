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

	let showPoses = $state(false);
	let showHands = $state(false);
	let showBboxes = $state(false);

	/**
	 * @param {VideoRecord} _video
	 * @param {number} _frame
	 * @param {number} _selectedPoseIdx
	 * @param {boolean} [_showPoses = false]
	 * @param {boolean} [_showHands = false]
	 */
	export const show = async (
		_video,
		_frame,
		_selectedPoseIdx,
		_showPoses = false,
		_showHands = false
	) => {
		video = _video;
		frame = _frame;
		selectedPoseIdx = _selectedPoseIdx;
		framePoseData = await getPoseData(video.id, frame);
		showPoses = _showPoses;
		showHands = _showHands;
		modal.show();
	};
</script>

{#snippet body()}
	{#if video}
		<Frame
			{video}
			{frame}
			poseData={framePoseData}
			{selectedPoseIdx}
			{showHands}
			{showPoses}
			{showBboxes}
		/>
		<Overlay>
			{#snippet topLeft()}
				{video?.video_name}, Frame {frame}
			{/snippet}
			{#snippet topRight()}
				<button onclick={modal.close}><CloseFilled /></button>
			{/snippet}
			{#snippet bottomRight()}
				<button onclick={() => (showPoses = !showPoses)}>
					{#if showPoses}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path
								d="M8.18 8.189a4.01 4.01 0 0 0 2.616 2.627m3.507 -.545a4 4 0 1 0 -5.59 -5.552"
							/>
							<path
								d="M6 21v-2a4 4 0 0 1 4 -4h4c.412 0 .81 .062 1.183 .178m2.633 2.618c.12 .38 .184 .785 .184 1.204v2"
							/>
							<path d="M3 3l18 18" />
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0" />
							<path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2" />
						</svg>
					{/if}
				</button>
				<button onclick={() => (showHands = !showHands)}>
					{#if showHands}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M3 3l18 18" />
							<path
								d="M8 13.5v-5.5m.44 -3.562a1.5 1.5 0 0 1 2.56 1.062v1.5m0 4.008v.992m0 -6.5v-2a1.5 1.5 0 1 1 3 0v6.5m0 -4.5a1.5 1.5 0 0 1 3 0v6.5m0 -4.5a1.5 1.5 0 0 1 3 0v8.5a6 6 0 0 1 -6 6h-2c-2.114 -.292 -3.956 -1.397 -5 -3l-2.7 -5.25a1.7 1.7 0 0 1 2.75 -2l.9 1.75"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M8 13v-7.5a1.5 1.5 0 0 1 3 0v6.5" />
							<path d="M11 5.5v-2a1.5 1.5 0 1 1 3 0v8.5" />
							<path d="M14 5.5a1.5 1.5 0 0 1 3 0v6.5" />
							<path
								d="M17 7.5a1.5 1.5 0 0 1 3 0v8.5a6 6 0 0 1 -6 6h-2h.208a6 6 0 0 1 -5.012 -2.7a69.74 69.74 0 0 1 -.196 -.3c-.312 -.479 -1.407 -2.388 -3.286 -5.728a1.5 1.5 0 0 1 .536 -2.022a1.867 1.867 0 0 1 2.28 .28l1.47 1.47"
							/>
						</svg>
					{/if}
				</button>
				<button onclick={() => (showBboxes = !showBboxes)}>
					{#if showBboxes}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M3.575 3.597a2 2 0 0 0 2.849 2.808" />
							<path d="M19 5m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M5 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M17.574 17.598a2 2 0 0 0 2.826 2.83" />
							<path d="M5 7v10" />
							<path d="M9 5h8" />
							<path d="M7 19h10" />
							<path d="M19 7v8" />
							<path d="M3 3l18 18" />
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M5 5m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M19 5m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M5 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M19 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0" />
							<path d="M5 7l0 10" />
							<path d="M7 5l10 0" />
							<path d="M7 19l10 0" />
							<path d="M19 7l0 10" />
						</svg>
					{/if}
				</button>
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
