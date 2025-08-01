<script>
	import { page } from '$app/stores';
	import { Loading } from 'carbon-components-svelte';
	import { LineChart } from '@carbon/charts-svelte';
	import '@carbon/charts-svelte/styles.css';

	/**
	 * @typedef {Object} PosePrevalenceProps
	 * @property {string} videoId
	 * @property {string} videoName
	 * @property {string} sourcePose Pose or hand to be searched
	 * @property {string} searchType
	 */

	/** @type {PosePrevalenceProps} */
	let { videoId, videoName, sourcePose, searchType } = $props();

	const formatPrevalenceData = async () =>
		await getPrevalenceData().then((data) =>
			data.map((frameData) => {
				return {
					group: videoName,
					value: frameData.similarity,
					frame: frameData.frame
				};
			})
		);

	const getPrevalenceData = async () => {
		const queryParams = new URLSearchParams();

		queryParams.append('video_id', videoId);
		queryParams.append('pose', sourcePose);
		queryParams.append('search_type', searchType);

		const query = `${$page.data.apiBase}/pose-prevalence/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	};

	const options = {
		title: 'Pose prevalence',
		axes: {
			bottom: {
				title: 'Frame',
				mapsTo: 'frame',
				scaleType: 'linear'
			},
			left: {
				mapsTo: 'value',
				title: 'Similarity',
				scaleType: 'linear'
			}
		},
		legend: {
			clickable: false
		},
		height: '400px'
	};
</script>

{#await formatPrevalenceData()}
	<div class="loading"><Loading small withOverlay={false} />Loading data...</div>
{:then data}
	<LineChart {data} {options} style="padding:2rem;" />
{/await}

<style>
</style>
