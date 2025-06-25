<script>
	import { page } from '$app/stores';
	import {
		Button,
		DataTable,
		ImageLoader,
		ProgressBar,
		MultiSelect
	} from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';

	let selectedVideoIds = $state([]);
	let /** @type Number[] */ selectedMetricIds = [];
	let videoNameById = {};
	let analysisResults = $state([]);
	let metricsToProcess = $state(0);
	let metricsProcessed = $state(0);

	const analysisMetrics = [
		{ id: 0, text: '3D movement (m/s)', endpoint: 'video_motion/3d' },
		{ id: 1, text: '2D movement (norm px/s)', endpoint: 'video_motion/2d' },
		{ id: 2, text: 'Sidereal motion (m/s)', endpoint: 'video_sidereal' },
		{ id: 3, text: 'Interpersonal distance (m)', endpoint: 'video_spacing' }
	];

	const selectMetrics = (/** @type {CustomEvent} */ multiSelectEvent) => {
		selectedMetricIds = multiSelectEvent.detail.selectedIds;
	};

	const runAnalyses = async () => {
		if (selectedVideoIds.length === 0) return [];
		analysisResults = [];
		metricsProcessed = 0;
		metricsToProcess = selectedMetricIds.length;
		selectedMetricIds.forEach(async (/** @type Number */ metricId) => {
			const endpoint = analysisMetrics.filter((item) => item.id === metricId)[0]['endpoint'];
			const videoIds = selectedVideoIds.join('|');
			const analyticData = await fetch(
				`${$page.data.apiBase}/analyze_${endpoint}/${videoIds}/`
			).then((data) => data.json());
			analysisResults.push({ metric: metricId, data: analyticData });
			metricsProcessed += 1;
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

	const getHeaders = (/** @type {[Object]} */ metricData) => {
		return metricData === undefined || metricData.length < 1
			? []
			: Object.keys(metricData[0])
					.map((key) =>
						key === 'video_id'
							? { key: 'video', value: 'Performance' }
							: { key: key, value: String(key).charAt(0).toUpperCase() + String(key).slice(1) }
					)
					.concat([{ key: 'histogram', value: 'Histogram' }]);
	};

	const getRows = ({ metric: metricId, data: metricData }) => {
		const endpoint = analysisMetrics.filter((item) => item.id === metricId)[0]['endpoint'];
		return metricData.map((/** @type {Object} */ metricRowData) => {
			let rowDict = {};
			Object.entries(metricRowData).map(([key, value]) => {
				if (key === 'video_id') {
					rowDict['id'] = value;
					rowDict['video'] = videoNameById[value];
					rowDict['histogram'] = `${$page.data.apiBase}/viz_${endpoint}/${value}/`;
				} else {
					rowDict[key] = value;
				}
			});
			return rowDict;
		});
	};
</script>

<h1>Analytics</h1>

<div class="control-board">
	{#await formatVideoData() then videos}
		<MultiSelect
			titleText="Performances"
			label="Select performances..."
			filterable
			items={videos}
			bind:selectedIds={selectedVideoIds}
		/>
	{/await}
	<MultiSelect
		titleText="Metrics"
		label="Choose analyses to run on the performances"
		filterable
		items={analysisMetrics}
		on:select={selectMetrics}
		selectedIds={selectedMetricIds}
	/>
	<Button on:click={runAnalyses}>Analyze</Button>
</div>

<div class="results-board">
	{#if metricsToProcess > 0 && metricsProcessed < metricsToProcess}
		<ProgressBar
			labelText="Processing status"
			helperText={`Calculating metric ${metricsProcessed + 1} of ${metricsToProcess}`}
			bind:value={metricsProcessed}
			bind:max={metricsToProcess}
		/>
	{/if}
	{#each analysisResults as tableData}
		<DataTable
			title={analysisMetrics.filter((item) => item.id === tableData.metric)[0]['text']}
			useStaticWidth
			zebra
			sortable
			headers={getHeaders(tableData.data)}
			rows={getRows(tableData)}
		>
			<svelte:fragment slot="cell" let:cell>
				{#if cell.key === 'histogram'}
					<ImageLoader src={cell.value} />
				{:else}
					{cell.value}
				{/if}
			</svelte:fragment>
		</DataTable>
	{/each}
</div>

<style>
	.control-board {
		display: flex;
		flex-direction: row;
		column-gap: 1rem;
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
</style>
