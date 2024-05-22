<script>
	import { Tabs, Tab, TabContent } from '/node_modules/carbon-components-svelte/src/index.js';
	import WebcamPoseInput from '$components/WebcamPoseInput.svelte';

	let selected = $state(0);
</script>

<section>
	<div id="query-container">
		<header>Source Pose</header>
		<Tabs bind:selected>
			<Tab label="Webcam" />
			<Tab label="Pose Editor" />
			<svelte:fragment slot="content">
				<TabContent>
					{#if selected === 0}<WebcamPoseInput />{/if}
				</TabContent>
				<TabContent>Pose Editor goes here...</TabContent>
			</svelte:fragment>
		</Tabs>
	</div>
	<div id="results-container"></div>
</section>

<style>
	section {
		display: flex;
		height: 100%;
		width: 100%;

		header {
			display: flex;
			padding: 1rem;
			background-color: var(--panel-background);
			border-bottom: 2px solid var(--primary);
		}

		div {
			border: 1px solid var(--primary);
		}

		#query-container {
			flex: 0 0 324px;
			max-width: 324px;
			overflow: hidden;
		}

		#results-container {
			flex: 1 1 auto;
		}
	}
</style>
