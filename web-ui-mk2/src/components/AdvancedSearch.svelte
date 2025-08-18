<script>
	import { fade } from 'svelte/transition';
	import {
		Button,
		Loading,
		MultiSelect,
		Select,
		SelectItem,
		Toggle
	} from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';
	import localStorageState from '$lib/localstorage.svelte';
	import PosePrevalence from './PosePrevalence.svelte';

	/**
	 * @typedef {Object} SearchResultsProps
	 * @property {MinimalPose|PoseRecord} sourcePose Source pose to be searched
	 */

	/** @type {SearchResultsProps} */
	let { sourcePose } = $props();

	/** @type {{value: 'cosine'|'view_invariant'|'3d'}}} */
	let searchType = localStorageState('pose-search-type', 'view_invariant');

	let selectedVideoIds = $state([]);

	// Some extra state to signal that running with "All" toggled on is a Big Deal
	let allSelected = $state(false);
	let runWithAll = $state(false);

	let /** @type {Object.<string, VideoRecord>} */ videoDataById = {};

	const formatVideoData = async () =>
		await getVideoData().then((data) =>
			data.map((/** @type {VideoRecord} */ video) => {
				videoDataById[video.id] = video;
				return {
					id: video.id,
					text: video.video_name
				};
			})
		);

	const formatSourcePose = (/** @type MinimalPose */ sourcePose) =>
		searchType.value === '3d' && !sourcePose.fromWebcam
			? sourcePose.global3d_coco13.toString()
			: sourcePose.norm.toString();

	const toggleAllVideos = (/** @type CustomEvent */ e) => {
		const toggledOn = e.detail.toggled;
		if (toggledOn) {
			selectedVideoIds = Object.keys(videoDataById);
			allSelected = true;
			runWithAll = false;
		} else {
			selectedVideoIds = [];
			allSelected = false;
			runWithAll = false;
		}
	};
</script>

<div class="controls">
	{#await formatVideoData()}
		<div class="loading"><Loading small withOverlay={false} />Loading performances...</div>
	{:then videos}
		<label class="selector-box">
			<div>All</div>
			<Toggle
				labelA=""
				labelB=""
				hideLabel
				labelText="All"
				bind:allSelected
				on:toggle={(/** @type CustomEvent */ e) => toggleAllVideos(e)}
			/>
		</label>
		<label>
			<div class="selector-box">
				<span>Performances: </span>
				<div class="selector" transition:fade>
					<MultiSelect
						titleText="Performances"
						label="Select performances..."
						disabled={allSelected}
						hideLabel
						placeholder="Type to filter..."
						filterable
						items={videos}
						bind:selectedIds={selectedVideoIds}
					/>
				</div>
			</div>
		</label>
	{/await}
	<label>
		<Select
			inline
			labelText="Search Type:"
			selected={searchType.value}
			on:change={(/** @type CustomEvent */ e) => (searchType.value = e.target?.value)}
		>
			<SelectItem value="cosine" text="Cosine" />
			<SelectItem value="view_invariant" text="View Invariant" />
			<SelectItem value="3d" text="Global 3D" />
		</Select>
	</label>
	{#if sourcePose && allSelected && !runWithAll}
		<Button
			iconDescription="Run All"
			kind="danger-tertiary"
			size="sm"
			on:click={() => (runWithAll = true)}>Run All (careful!)</Button
		>
	{/if}
</div>

{#if sourcePose && (!allSelected || (allSelected && runWithAll))}
	<div class="results">
		{#each selectedVideoIds as videoId, v}
			<PosePrevalence
				{videoId}
				video={videoDataById[videoId]}
				sourcePose={formatSourcePose(sourcePose)}
				searchType={sourcePose.fromWebcam && searchType.value === '3d'
					? 'view_invariant'
					: searchType.value}
				itemSequence={v}
			/>
		{/each}
	</div>
{/if}

<style>
	.controls,
	.results {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		padding: 1rem;
		gap: 1rem;
	}

	.loading {
		display: flex;
		flex-direction: column;
		padding: 1rem;
		gap: 1rem;
		text-align: center;
	}

	.selector {
		width: 30rem;
	}

	.selector-box {
		display: flex;
		flex-direction: row;
		align-items: center;
		font-size: 0.75rem;
		color: #525252;
		font-weight: 400;
		letter-spacing: 0.32px;
		line-height: 1rem;
	}

	.search-type {
		width: 20rem;
	}

	label {
		align-items: flex-start;
		display: flex;
		gap: 0.5rem;
		line-height: 24px;
		background-color: #f4f4f4;
	}

	input[type='number'] {
		width: 5rem;
	}
</style>
