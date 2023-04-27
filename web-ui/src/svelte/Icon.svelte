<script>
  export let name;
  export let width = "1rem";
  export let height = "1rem";
  export let customAttribs = {};

  const defaultAttribs = {
    viewBox: "0 0 24 24",
    "stroke-width": 2,
    stroke: "currentColor",
    fill: "none",
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
  };

  const icons = {
    "book-2": {
      svg: `
        <path d="M19 4v16h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h12z" />
        <path d="M19 16h-12a2 2 0 0 0 -2 2" />
        <path d="M9 8h6" />      
      `,
    },
    notebook: {
      svg: `
        <path d="M6 4h11a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-11a1 1 0 0 1 -1 -1v-14a1 1 0 0 1 1 -1m3 0v18" />
        <path d="M13 8l2 0" />
        <path d="M13 12l2 0" />
      `,
    },
    github: {
      svg: `
        <path d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5" />
      `,
    },
  };
  const { attribs, svg } = icons[name];
</script>

<svg
  {height}
  {width}
  {...defaultAttribs}
  {...attribs}
  {...customAttribs}
  {...$$props}>{@html svg}</svg
>
