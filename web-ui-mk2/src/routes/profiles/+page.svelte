<script>
	import { page } from '$app/state';
	import { fade } from 'svelte/transition';
	import {
		Button,
		DataTable,
		ImageLoader,
		Loading,
		MultiSelect,
		ProgressBar,
		TileGroup,
		RadioTile
	} from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';

	let selectedVideoIds = $state([]);
	let /** @type Number */ selectedProfile = $state(0);
	let videoNameById = {};
	let profileResults = $state([]);
	let videosToProcess = $state(0);
	let videosProcessed = $state(0);

	const profileTypes = [
		{ id: 0, text: 'Pose embeddings', endpoint: 'profile/poses/poem' },
		{ id: 1, text: 'Pose coordinates', endpoint: 'profile/poses/global3d' },
		{ id: 2, text: 'Hand embeddings', endpoint: 'profile/hands/weights' },
		{ id: 3, text: 'Hand joint angles', endpoint: 'profiles/hands/angles' }
	];

	const runProfiles = async () => {
		if (selectedVideoIds.length === 0) return [];
		profileResults = [];
		videosProcessed = 0;
		videosToProcess = selectedVideoIds.length;
		selectedVideoIds.forEach(async (/** @type Number */ videoId) => {
			const endpoint = profileTypes.filter((item) => item.id === selectedProfile)[0]['endpoint'];
			const videoIds = selectedVideoIds.join('|');
			const profileData = await fetch(`${page.data.apiBase}/${endpoint}/${videoIds}/`).then(
				(data) => data.json()
			);
			profileResults.push({ data: profileData });
			videosProcessed += 1;
		});
	};

	const formatVideoData = async () =>
		await getVideoData().then((data) =>
			data.map((/** @type {VideoRecord} */ video) => {
				videoNameById[video.id] = video.video_name;
				return {
					id: video.id,
					text: video.video_name
				};
			})
		);

	// const getHeaders = (/** @type {[Object]} */ metricData) => {
	// 	return metricData === undefined || metricData.length < 1
	// 		? []
	// 		: Object.keys(metricData[0])
	// 				.map((key) =>
	// 					key === 'video_id'
	// 						? { key: 'video', value: 'Performance' }
	// 						: { key: key, value: String(key).charAt(0).toUpperCase() + String(key).slice(1) }
	// 				)
	// 				.concat([{ key: 'histogram', value: 'Histogram' }]);
	// };

	// const getRows = ({ metric: metricId, data: metricData }) => {
	// 	const endpoint = analysisMetrics.filter((item) => item.id === metricId)[0]['endpoint'];
	// 	return metricData.map((/** @type {Object} */ metricRowData) => {
	// 		let rowDict = {};
	// 		Object.entries(metricRowData).map(([key, value]) => {
	// 			if (key === 'video_id') {
	// 				rowDict['id'] = value;
	// 				rowDict['video'] = videoNameById[value];
	// 				rowDict['histogram'] = `${page.data.apiBase}/viz_${endpoint}/${value}/`;
	// 			} else {
	// 				rowDict[key] = value;
	// 			}
	// 		});
	// 		return rowDict;
	// 	});
	// };
</script>

<h1>Performance Profiling</h1>

<div class="control-board">
	{#await formatVideoData()}
		<div class="loading"><Loading small withOverlay={false} />Loading performances...</div>
	{:then videos}
		<div transition:fade>
			<MultiSelect
				titleText="Performances"
				label="Select performances..."
				direction="top"
				open="true"
				hideLabel
				placeholder="Select performances..."
				filterable
				items={videos}
				bind:selectedIds={selectedVideoIds}
			/>
		</div>
	{/await}
	<TileGroup legend="Select a profile to calculate" name="profiles" bind:selectedProfile>
		{#each profileTypes as pType}
			<RadioTile light value={pType.id} checked={selectedProfile === pType.id}
				>{pType.text}</RadioTile
			>
		{/each}
	</TileGroup>
	<Button onclick={runProfiles} size="field" disabled={selectedVideoIds.length === 0}
		>Profile</Button
	>
</div>

<div class="results-board">
	{#if videosToProcess > 0 && videosProcessed < videosToProcess}
		<ProgressBar
			labelText="Processing status"
			helperText={`Profiling performance ${videosProcessed + 1} of ${videosToProcess}`}
			bind:value={videosProcessed}
			bind:max={videosToProcess}
		/>
	{/if}
	{#each profileResults as profileData}{/each}
</div>

<style>
	.control-board {
		display: flex;
		flex-direction: row;
		column-gap: 1rem;
		align-items: end;

		:global(& > *) {
			width: 25%;
		}

		:global(button) {
			width: auto;
		}
	}

	.results-board {
		display: flex;
		flex-direction: column;
		padding: 1rem 0 0 0;
		row-gap: 1rem;
	}

	h1 {
		margin: 2rem 0;
	}

	:global(td > img) {
		max-height: 200px;
		max-width: 300px;
		mix-blend-mode: multiply;
	}

	.loading {
		align-self: center;
		display: flex;
		gap: 1rem;
	}

	:global(.bx--data-table-container, .bx--data-table--static) {
		width: 100%;
	}
</style>
