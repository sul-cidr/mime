<script>
	import PoseCard from './PoseCard.svelte';
	import { getKeypointsBounds } from '$lib/pose-utils';

	/**
	 * @typedef {Object} ExamplePosesProps
	 * @property {function} setSourcePoseFromCoco13Skeleton Function to set the selected pose in the parent component
	 */

	/** @type {ExamplePosesProps} */
	let { setSourcePoseFromCoco13Skeleton } = $props();

	const /** @type {Partial<MinimalPose>[]} */ poses = [
			{
				norm: [
					61, 0, 51, 9, 42, 9, 55, 26, 37, 27, 68, 29, 40, 43, 52, 41, 41, 39, 50, 73, 37, 72, 49,
					100, 31, 99
				]
			},
			{
				norm: [
					51.191663381075045, 0, 75.03353397092368, 15.516181431653841, 43.39068709008815,
					12.924789405710943, 77.40678587043656, 43.87648040764366, 32.54092286439638,
					36.3386052209169, 53.29793142070187, 51.61337536987292, 34.963775063718906,
					46.5697900104882, 68.60443929027669, 49.328763862888856, 49.760195429495425,
					47.88429312102273, 74.23094554330552, 61.98013304338284, 22.59321412956343,
					52.79471328561922, 68.10814445107114, 100, 28.08901363192993, 88.98733450824757
				]
			},
			{
				norm: [
					39.64142500102298, 13.056990205339474, 50.94232923173767, 21.451690466494647,
					29.122292557436396, 20.269089001638108, 67.64366885577871, 16.680360072308073,
					16.92213392062387, 18.322962582553778, 83.07786607937612, 0, 36.87839783223297,
					2.546266254791284, 46.167272402779304, 51.49441958940055, 31.179505377228814,
					52.555310726030726, 45.365533550047324, 78.60130771692637, 30.196592234472092,
					77.65646272766944, 43.40437110467492, 100, 29.210499200710107, 98.14441435251754
				]
			}
		];

	for (const pose of poses) {
		if (!pose.norm) continue;
		if (!pose.bbox) {
			// if there's no bbox, calculate one
			pose.bbox = getKeypointsBounds(pose.norm, false);
		}
		if (!pose.keypoints) {
			// if there's no keypoints, interpolate a confidence value (1)
			//  (the pose drawing functions expect a confidence value --
			//   this might be better addressed elsewhere, but this will do for now)
			pose.keypoints = /** @type {Coco13SkeletonNoConfidence} */ (
				pose.norm.flatMap((val, i) => ((i + 1) % 2 === 0 ? [val, 1] : val))
			);
		}
	}
</script>

<section>
	{#each poses as pose}
		<button onclick={() => setSourcePoseFromCoco13Skeleton(pose.norm)}>
			<PoseCard sourcePose={/** @type {MinimalPose} */ pose} showPose={true} />
		</button>
	{/each}
</section>

<style>
	section {
		align-items: center;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	button {
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;

		&:hover {
			background: rgba(0, 0, 0, 0.25);
			border-radius: 1px;
			outline-offset: 6px;
			outline: 2px solid var(--primary);
		}
	}
</style>
