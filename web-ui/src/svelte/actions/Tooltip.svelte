<svelte:options accessors />

<script lang="ts">
  import type { Placement } from "@floating-ui/dom";
  export let text: string;
  export let arrowPosition: Placement | null = null;
  export let element;
</script>

<div bind:this={element} data-arrow={arrowPosition}>
  <span>{text}</span>
</div>

<style>
  div {
    --tip-color: hsla(0, 0%, 20%, 0.9);
    --arrow-width: 5px;
    position: absolute;
    z-index: 999;
  }

  span {
    animation: scaleIn 0.2s ease forwards;
    background-color: var(--tip-color);
    border-radius: var(--theme-rounded-base); /* from the skeleton theme */
    color: #fff;
    display: inline-block;
    line-height: 1.2;
    max-width: 250px;
    min-width: 70px;
    padding: 4px 7px;
    position: relative;
    text-align: center;
    white-space: pre-line;
  }

  span::after {
    border: var(--arrow-width) solid transparent;
    content: " ";
    font-size: 0;
    line-height: 0;
    position: absolute;
    width: 0;
  }

  div[data-arrow="top"] span::after {
    border-top-color: var(--tip-color);
    top: 100%;
    left: 50%;
    transform: translate(-50%, 0);
  }

  div[data-arrow="bottom"] span::after {
    border-bottom-color: var(--tip-color);
    bottom: 100%;
    left: 50%;
    transform: translate(-50%, 0);
  }

  div[data-arrow="left"] span::after {
    border-left-color: var(--tip-color);
    left: 100%;
    top: 50%;
    transform: translate(0, -50%);
  }

  div[data-arrow="right"] span::after {
    border-right-color: var(--tip-color);
    right: 100%;
    top: 50%;
    transform: translate(0, -50%);
  }

  @keyframes scaleIn {
    from {
      transform: scale(0.95);
      opacity: 0;
    }
    to {
      transform: scale(1);
      opacity: 1;
    }
  }
</style>
