<script>
	import { base } from '$app/paths';
</script>

<svelte:head>
	<title>MIME :: Home</title>
	<meta name="description" content="Machine Intelligence for Motion Exegesis" />
</svelte:head>

<section>
	<h1>MIME: Machine Intelligence for Motion Exegesis</h1>
	<p>
		MIME is a collaboration between faculty in the Department of Theater and Performance Studies at
		Stanford University and AI Modeling & Inference developers at the Stanford Libraries, with the
		goal of studying recorded theatrical performances through the lens of pose estimation and motion
		tracking. More information is available at our <a href="https://github.com/sul-cidr/mime"
			>GitHub</a
		> repo.
	</p>
	<p>
		This portion of the MIME interface supports focused searching for specific sampled poses and
		hand gestures that are derived from "in the wild" performance recordings, predefined archetypes,
		and user input, as well as "distant viewing" analytics that can be applied across all or a
		portion of the entire corpus of performances. You may select the "Timelines" tab at left to
		access the other half of the site, which explores timeline and clustering analyses of poses,
		hands, actions, and (optionally) faces within individual performances.
	</p>
</section>

<style>
	p {
		padding: 20px 0 0 0;
	}
</style>
