<script>
	import { page } from '$app/state';
	import { fade } from 'svelte/transition';
	import {
		Button,
		Loading,
		MultiSelect,
		ProgressBar,
		TileGroup,
		RadioTile
	} from 'carbon-components-svelte';
	import { getVideoData } from '$lib/data-fetching';

	let selectedVideoIds = $state([]);
	let /** @type Number */ selectedProfile = $state(0);
	let /** @type {Object.<string, string>} */ videoNameById = {};
	let profileData = $state([]);
	let profilesToLoad = $state(0);
	let profilesLoaded = $state(0);
	let metricName = 'Pose embeddings';
	let resultsClass = $state('hidden');

	const imageLoaded = () => {
		// XXX There's a concurrency issue here (?) that sometimes prevents the progress
		//  bar from reaching 100%. But it's desirable to hide the old plots when a new
		//  set is being generated. So hiding the results divs when the "Profile" button
		//  is pressed, but revealing them when the •first* new response comes in,
		//  seems to work OK and at least won't leave the results divs hidden if the
		//  race condition crops up.
		profilesLoaded++;
		resultsClass = '';
	};

	const profileTypes = [
		{ id: 0, text: 'Pose embeddings (view invariant)', endpoint: 'profile/poses/poem_embedding' },
		{ id: 1, text: 'Pose coordinates (global 3D)', endpoint: 'profile/poses/global3d_coco13' },
		{ id: 2, text: 'Hand embeddings (class weights)', endpoint: 'profile/hands/class_weights' },
		{ id: 3, text: 'Hand joint angles (view invariant)', endpoint: 'profile/hands/joint_angles3d' }
	];

	const setProfileType = (/** @type Number */ profileTypeId) => {
		selectedProfile = profileTypeId;
		metricName = profileTypes.filter((item) => item.id === selectedProfile)[0]['text'];
	};

	const runProfiles = async () => {
		if (selectedVideoIds.length === 0) return;

		resultsClass = 'hidden';
		profileData = [];
		profilesLoaded = 0;
		profilesToLoad = selectedVideoIds.length;
		selectedVideoIds.forEach(async (/** @type String */ videoId) => {
			const endpoint = profileTypes.filter((item) => item.id === selectedProfile)[0]['endpoint'];
			const profileUrl = `${page.data.apiBase}/${endpoint}/${videoId}/`;
			profileData.push({ url: profileUrl, videoId: videoId });
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
	<TileGroup
		on:select={({ detail }) => {
			setProfileType(detail);
		}}
		legend="Select a profile to calculate"
		name="profiles"
	>
		{#each profileTypes as pType}
			<RadioTile value={pType.id} checked={selectedProfile === pType.id}>{pType.text}</RadioTile>
		{/each}
	</TileGroup>
	<Button onclick={runProfiles} size="field" disabled={selectedVideoIds.length === 0}
		>Profile</Button
	>
</div>

<div class="results-board">
	{#if profilesToLoad > 0 && profilesLoaded < profilesToLoad}
		<ProgressBar
			labelText="Processing status"
			helperText={`Calculating profile ${profilesLoaded + 1} of ${profilesToLoad}`}
			bind:value={profilesLoaded}
			bind:max={profilesToLoad}
		/>
	{/if}
	{#each profileData as profileInfo}
		<div class={resultsClass}>
			<p>
				{videoNameById[profileInfo['videoId']]}: Archetype similarity based on {metricName}
			</p>
			<img
				src={profileInfo['url']}
				alt="Bar plot of avg pose or hand similarity from a performance video to Delsarte archetypes"
				on:load={imageLoaded}
			/>
		</div>
	{/each}
</div>

<style>
	.hidden {
		opacity: 0;
	}

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
