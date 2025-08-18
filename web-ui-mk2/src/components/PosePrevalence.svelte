<script>
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import { Loading } from 'carbon-components-svelte';
	import { LineChart } from '@carbon/charts-svelte';
	import '@carbon/charts-svelte/styles.css';

	/**
	 * @typedef {Object} PosePrevalenceProps
	 * @property {VideoRecord} video
	 * @property {string} sourcePose Pose or hand to be searched
	 * @property {string} searchType
	 * @property {Number} itemSequence
	 */

	/**
	 * @typedef {Object} FrameData
	 * @property {Number} frame
	 * @property {Number} similarity
	 * @property {Number} moving_average
	 * @property {Number} gaussian
	 */

	/** @type {PosePrevalenceProps} */
	let { video, sourcePose, searchType, itemSequence } = $props();

	let showComponent = $state(false);

	onMount(async () => {
		// View Invariant matches take significantly longer to process than the
		// others... while we're being arbitrary, might as well make the distinction
		const waitTime = searchType === 'view_invariant' ? 3000 : 1000;
		await new Promise((resolve) => setTimeout(resolve, waitTime * itemSequence));
		showComponent = true;
		await tick(); // Ensure pending state changes are applied
	});

	const formatPrevalenceData = async () =>
		await getPrevalenceData().then((data) =>
			data.flatMap((/** @type {FrameData} */ frameData) => {
				return [
					{
						group: 'Similarity',
						value: frameData.similarity,
						frame: frameData.frame
					},
					{
						group: 'Moving average',
						value: frameData.moving_average,
						frame: frameData.frame
					},
					{
						group: 'Gaussian',
						value: frameData.gaussian,
						frame: frameData.frame
					}
				];
			})
		);

	const getPrevalenceData = async () => {
		const queryParams = new URLSearchParams();

		queryParams.append('video_id', video.id);
		queryParams.append('pose', sourcePose);
		queryParams.append('search_type', searchType);

		const query = `${$page.data.apiBase}/pose-prevalence/?${queryParams.toString()}`;

		const response = await fetch(query);
		return await response.json();
	};

	const options = {
		title: 'Prevalence',
		axes: {
			bottom: {
				title: 'Time',
				mapsTo: 'frame',
				scaleType: 'linear',
				ticks: {
					number: 8,
					formatter: (/** @type Number */ frame) =>
						new Date((frame / video.fps) * 1000).toISOString().slice(11, 19)
				}
			},
			left: {
				mapsTo: 'value',
				title: 'Similarity',
				scaleType: 'linear',
				domain: [0, 1]
			}
		},
		legend: {
			enabled: true
		},
		points: {
			enabled: false
		},
		tooltip: {
			valueFormatter: (/** @type Number */ value, /** @type string */ label) => {
				if (label === 'Time') {
					const timeString = new Date((value / video.fps) * 1000).toISOString().slice(11, 19);
					return `Frame ${value} (${timeString})`;
				} else if (!isNaN(value)) {
					return value.toFixed(5);
				}
				return value;
			},
			groupLabel: 'Performance',
			showTotal: false,
			truncation: {
				numCharacter: 30
			}
		},
		height: '400px'
	};
</script>

{#if showComponent}
	{#await formatPrevalenceData()}
		<div class="loading"><Loading small withOverlay={false} />Loading data...</div>
	{:then data}
		<div class="prevalence-chart">
			<div class="chart-title">{video.video_name}</div>
			<LineChart {data} {options} />
		</div>
	{/await}
{/if}

<style>
	.prevalence-chart {
		padding: 1em;
	}
</style>
