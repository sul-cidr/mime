<script>
	import { page } from '$app/state';
	import { Tabs, Tab, TabContent } from 'carbon-components-svelte';

	import { getPoseData, getVideoData } from '$lib/data-fetching';
	import SearchResults from '$components/SearchResults.svelte';
	import HandSearchResults from '$components/HandSearchResults.svelte';
	import WebcamPoseInput from '$components/WebcamPoseInput.svelte';
	import ExamplePoses from '$components/ExamplePoses.svelte';
	import ExampleHands from '$components/ExampleHands.svelte';
	import SourcePoseFromDb from '$components/SourcePoseFromDb.svelte';

	let searchTab = $state(0);
	let searchType = $derived(searchTab === 0 ? 'pose' : 'hand');
	let sourceTab = $state(0);
	let sourcePose = $state();
	let sourcePoseFromUrl = $state(true);
	let sourceHand = $state();

	/** @param {Coco13SkeletonNoConfidence} skeleton */
	const setSourcePoseFromCoco13Skeleton = (skeleton) => {
		sourcePose = { norm: skeleton };
	};

	/** @param {HandForSearching} hand */
	const setSourceHand = (hand) => {
		sourceHand = hand;
	};

	/** @param {PoseRecord} pose */
	const setPoseFromURL = async (pose) => {
		const video = (await getVideoData()).find(
			(/** @type {VideoRecord} */ video) => video.id === pose.video_id
		);
		pose.video_name = /** @type {VideoRecord} */ (video).video_name;
		sourcePose = pose;
		sourcePoseFromUrl = true;
	};

	$effect(() => {
		const videoId = page.url.searchParams.get('video');
		const frame = parseInt(page.url.searchParams.get('frame') ?? '', 10);
		const poseIdx = parseInt(page.url.searchParams.get('pose') ?? '', 10);

		if (videoId && !isNaN(frame) && !isNaN(poseIdx)) {
			getPoseData(videoId, frame).then((data) => {
				const pose = data.find((/** @type {PoseRecord} */ p) => p.pose_idx === poseIdx);
				if (!pose) {
					throw new Error('Pose not found');
				}
				setPoseFromURL(pose);
			});
		} else {
			sourcePoseFromUrl = false;
		}
	});
</script>

<section>
	<div id="query-container">
		<Tabs bind:selected={searchTab} type="container">
			<Tab>Poses</Tab>
			<Tab>Hands</Tab>
			<svelte:fragment slot="content">
				<TabContent class="tab-panel">
					{#if sourcePoseFromUrl}
						{#if sourcePose}
							<SourcePoseFromDb poseRecord={sourcePose} />
						{/if}
					{:else}
						<Tabs bind:selected={sourceTab} autoWidth>
							<Tab label="Examples" />
							<Tab label="Webcam" />
							<Tab label="Pose Editor" />
							<svelte:fragment slot="content">
								<TabContent class="tab-panel">
									<ExamplePoses {setSourcePoseFromCoco13Skeleton} />
								</TabContent>
								<TabContent class="tab-panel">
									{#if sourceTab === 1}<WebcamPoseInput {setSourcePoseFromCoco13Skeleton} />{/if}
								</TabContent>
								<TabContent class="tab-panel">Pose Editor goes here...</TabContent>
							</svelte:fragment>
						</Tabs>
					{/if}
				</TabContent>
				<TabContent>
					{#if searchType === 'hand'}
						<ExampleHands {setSourceHand} />
					{/if}
				</TabContent>
			</svelte:fragment>
		</Tabs>
	</div>
	<div id="results-container">
		{#if searchType === 'pose'}
			<SearchResults {sourcePose} />
		{:else if searchType === 'hand'}
			<HandSearchResults {sourceHand} />
		{/if}
	</div>
</section>

<style>
	#query-container {
		display: flex;
		flex-direction: column;

		& :global(> .tab-panel) {
			padding: 0;
		}
	}

	:global(.tab-panel) {
		min-height: 0;
		overflow-y: auto;
	}

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
			overflow-y: auto;
		}
	}
</style>
