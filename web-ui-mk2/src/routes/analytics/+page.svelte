<script>
	import { page } from '$app/stores';
	import { Button, DataTable, MultiSelect } from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';

	let selectedVideoIds = $state([]);
	let /** @type Number[] */ selectedMetricIds = [];
	let videoNameById = {};
	let analysisResults = $state([]);

	const analysisMetrics = [
		{ id: 0, text: 'Movement (m/s)', endpoint: 'video_motion' },
		{ id: 1, text: 'Distance between people', endpoint: 'video_spacing' }
	];

	const selectMetrics = (/** @type {CustomEvent} */ multiSelectEvent) => {
		selectedMetricIds = multiSelectEvent.detail.selectedIds;
	};

	const runAnalyses = async () => {
		if (selectedVideoIds.length === 0) return [];
		analysisResults = [];
		selectedMetricIds.forEach(async (/** @type Number */ metricId) => {
			const endpoint = analysisMetrics.filter((item) => item.id === metricId)[0]['endpoint'];
			const videoIds = selectedVideoIds.join('|');
			const analyticData = await fetch(
				`${$page.data.apiBase}/analyze_${endpoint}/${videoIds}/`
			).then((data) => data.json());
			analysisResults.push({ metric: metricId, data: analyticData });
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

	const getHeaders = (metricData) =>
		metricData.length < 1
			? []
			: Object.keys(metricData[0]).map((key) =>
					key === 'video_id'
						? { key: 'video', value: 'Performance' }
						: { key: key, value: String(key).charAt(0).toUpperCase() + String(key).slice(1) }
				);

	const getRows = (metricData) =>
		metricData.map((metricRowData) => {
			let rowDict = {};
			Object.entries(metricRowData).map(([key, value]) => {
				if (key === 'video_id') {
					rowDict['id'] = value;
					rowDict['video'] = videoNameById[value];
				} else {
					rowDict[key] = value;
				}
			});
			return rowDict;
		});
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
	{#each analysisResults as tableData}
		<DataTable
			title={analysisMetrics.filter((item) => item.id === tableData.metric)[0]['text']}
			useStaticWidth
			zebra
			sortable
			headers={getHeaders(tableData.data)}
			rows={getRows(tableData.data)}
		/>
	{/each}
</div>

<style>
	.control-board {
		display: flex;
		flex-direction: row;
		column-gap: 1rem;
	}
	.results-board {
		padding: 1rem 0 0 0;
	}
	h1 {
		margin: 2rem 0;
	}
	pre {
		margin: 2rem;
		padding: 1rem;
		font-family: monospace;
		font-size: 1rem;
		line-height: 1.5;
		background: #eee;
	}
</style>
