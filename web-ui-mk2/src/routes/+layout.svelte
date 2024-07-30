<script>
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import {
		Content,
		Header,
		SideNav,
		SideNavDivider,
		SideNavItems,
		SideNavLink,
		SkipToContent
	} from 'carbon-components-svelte';
	import DataBase from 'carbon-icons-svelte/lib/DataBase.svelte';
	import Home from 'carbon-icons-svelte/lib/Home.svelte';
	import LogoGithub from 'carbon-icons-svelte/lib/LogoGithub.svelte';
	import Search from 'carbon-icons-svelte/lib/Search.svelte';
	import ChartScatter from 'carbon-icons-svelte/lib/ChartScatter.svelte';

	import '@/carbon-theming.css';

	let isSideNavOpen = false;
</script>

<Header
	platformName="Machine Intelligence for Motion Exegesis"
	company="MIME ::"
	bind:isSideNavOpen
>
	<svelte:fragment slot="skip-to-content">
		<SkipToContent />
	</svelte:fragment>
</Header>

<SideNav bind:isOpen={isSideNavOpen} rail>
	<SideNavItems>
		<SideNavLink
			icon={Home}
			text="Home"
			href="{base}/"
			isSelected={$page.url.pathname == `${base}/`}
		/>
		<SideNavLink
			icon={DataBase}
			text="Browse Videos"
			href="{base}/browse/"
			isSelected={$page.url.pathname == `${base}/browse`}
		/>
		<SideNavLink
			icon={Search}
			text="Search Interface"
			href="{base}/search/"
			isSelected={$page.url.pathname == `${base}/search`}
		/>
		<SideNavLink
			icon={ChartScatter}
			text="Analytics"
			href="{base}/analytics/"
			isSelected={$page.url.pathname == `${base}/analytics`}
		/>
		<SideNavDivider />
		<SideNavLink icon={LogoGithub} text="GitHub" href="https://github.com/sul-cidr/mime" />
	</SideNavItems>
</SideNav>

<Content>
	<slot />
</Content>

<style>
	:global(#main-content) {
		height: calc(100vh - 3rem);
		overflow: hidden;
	}
</style>
