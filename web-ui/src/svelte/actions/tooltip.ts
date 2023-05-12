import { computePosition, flip, offset } from "@floating-ui/dom";
import Tooltip from "./Tooltip.svelte";

export const tooltip = (node: HTMLElement, text: string) => {
  if (!text) return {};
  let tooltipComponentInstance: Tooltip;

  const attachTooltip = () => {
    tooltipComponentInstance = new Tooltip({
      target: document.body,
      // @ts-ignore
      props: { text },
    });

    const { element: tooltipElement } = tooltipComponentInstance;

    computePosition(node, tooltipElement, {
      placement: "top",
      middleware: [offset(10), flip()],
    }).then(({ x, y, placement }) => {
      tooltipElement.style.left = `${x}px`;
      tooltipElement.style.top = `${y}px`;
      tooltipComponentInstance.$set({ arrowPosition: placement });
    });
  };

  const removeTooltip = () => {
    tooltipComponentInstance?.$destroy();
  };

  node.addEventListener("mouseenter", attachTooltip);
  node.addEventListener("mouseleave", removeTooltip);

  return {
    destroy() {
      removeTooltip();
      node.removeEventListener("mouseenter", attachTooltip);
      node.removeEventListener("mouseleave", removeTooltip);
    },
  };
};
