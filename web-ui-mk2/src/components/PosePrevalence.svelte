<script>
	import { page } from '$app/stores';
	import { Loading } from 'carbon-components-svelte';
	import { LineChart } from '@carbon/charts-svelte';
	import '@carbon/charts-svelte/styles.css';

	/**
	 * @typedef {Object} PosePrevalenceProps
	 * @property {VideoRecord} video
	 * @property {string} sourcePose Pose or hand to be searched
	 * @property {string} searchType
	 */

	/** @type {PosePrevalenceProps} */
	let { video, sourcePose, searchType } = $props();

	const formatPrevalenceData = async () =>
		await getPrevalenceData().then((data) =>
			data.flatMap((frameData) => {
				if (frameData.frame < 500) console.log(frameData);
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
		title: `Pose prevalence for ${video.video_name}`,
		axes: {
			bottom: {
				title: 'Time',
				mapsTo: 'frame',
				scaleType: 'linear',
				ticks: {
					number: 8,
					formatter: (frame) => new Date((frame / video.fps) * 1000).toISOString().slice(11, 19)
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
			valueFormatter: (value, label) => {
				if (label === 'Time') {
					const timeString = new Date((value / video.fps) * 1000).toISOString().slice(11, 19);
					return `Frame ${value} (${timeString})`;
				} else if (label === 'Similarity') {
					return `${value.toFixed(5)}`;
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

{#await formatPrevalenceData()}
	<div class="loading"><Loading small withOverlay={false} />Loading data...</div>
{:then data}
	<LineChart {data} {options} style="padding:2rem;" />
{/await}

<style>
</style>
