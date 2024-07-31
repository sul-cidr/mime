<script>
	import { page } from '$app/stores';
	import { Tabs, Tab, TabContent } from 'carbon-components-svelte';

	import { getPoseData, getVideoData } from '$lib/data-fetching';
	import PoseCard from '$components/PoseCard.svelte';
	import SearchResults from '$components/SearchResults.svelte';
	import WebcamPoseInput from '$components/WebcamPoseInput.svelte';

	let selected = $state(0);
	let sourcePose = $state();
	let sourcePoseFromUrl = $state();

	/** @param {Coco13SkeletonNoConfidence} pose */
	const setSourcePoseFromCoco13Skeleton = (pose) => {
		sourcePose = pose;
	};

	/** @param {PoseRecord} pose */
	const setPoseFromURL = async (pose) => {
		const video = (await getVideoData()).find(
			(/** @type {VideoRecord} */ video) => video.id === pose.video_id
		);
		pose.video_name = /** @type {VideoRecord} */ (video).video_name;
		sourcePoseFromUrl = pose;
		setSourcePoseFromCoco13Skeleton(pose.norm);
	};

	$effect(() => {
		const videoId = $page.url.searchParams.get('video');
		const frame = parseInt($page.url.searchParams.get('frame') ?? '', 10);
		const poseIdx = parseInt($page.url.searchParams.get('pose') ?? '', 10);

		if (videoId && frame && poseIdx) {
			getPoseData(videoId, frame).then((data) => {
				const pose = data.find((/** @type {PoseRecord} */ p) => p.pose_idx === poseIdx);
				if (!pose) {
					throw new Error('Pose not found');
				}
				setPoseFromURL(pose);
			});
		}
	});
</script>

<section>
	<div id="query-container">
		<header>Source Pose</header>
		{#if sourcePoseFromUrl}
			<PoseCard sourcePose={sourcePoseFromUrl} showPose={false} class="source-pose-card" />
		{:else}
			<Tabs bind:selected>
				<Tab label="Webcam" />
				<Tab label="Pose Editor" />
				<svelte:fragment slot="content">
					<TabContent>
						{#if selected === 0}<WebcamPoseInput {setSourcePoseFromCoco13Skeleton} />{/if}
					</TabContent>
					<TabContent>Pose Editor goes here...</TabContent>
				</svelte:fragment>
			</Tabs>
		{/if}
	</div>
	<div id="results-container">
		<SearchResults {sourcePose} />
	</div>
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
			overflow-y: auto;
		}

		& :global(.source-pose-card) {
			width: 100%;
		}
	}
</style>
