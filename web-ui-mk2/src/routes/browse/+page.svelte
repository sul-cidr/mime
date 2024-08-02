<script>
	import { DataTable } from 'carbon-components-svelte';
	import { page } from '$app/stores';

	const headers = [
		{ key: 'video_name', value: 'Name' },
		{ key: 'meta', value: 'Meta' },
		{ key: 'length', value: 'Length' },
		{ key: 'pose_ct', value: 'Poses' },
		{ key: 'poses_per_frame', value: 'Poses/Frame' },
		{ key: 'face_ct', value: 'Faces' },
		{ key: 'track_ct', value: 'Tracks' },
		{ key: 'shot_ct', value: 'Shots' }
	];

	const getVideoRows = async () => {
		return await fetch(`${$page.data.apiBase}/videos/`)
			.then((data) => data.json())
			.then((data) =>
				data.videos.map((/** @type {VideoRecord} */ video) => ({
					id: video.id,
					video_name: video.video_name,
					meta: `${video.width}x${video.height}@${video.fps.toFixed(2)}fps`,
					length: new Date((video.frame_count / video.fps) * 1000).toISOString().slice(11, 19),
					pose_ct: video.pose_ct.toLocaleString(),
					poses_per_frame: video.poses_per_frame,
					face_ct: video.face_ct.toLocaleString(),
					track_ct: video.track_ct.toLocaleString(),
					shot_ct: video.shot_ct.toLocaleString()
				}))
			);
	};
</script>

{#await getVideoRows()}
	<p>Loading...</p>
{:then rows}
	<DataTable {headers} {rows} />
{/await}
