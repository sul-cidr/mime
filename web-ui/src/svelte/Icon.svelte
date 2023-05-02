<script>
  export let name;
  export let width = "16px";
  export let height = "16px";
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
    "alert-triangle": {
      svg: `
        <path d="M10.24 3.957l-8.422 14.06a1.989 1.989 0 0 0 1.7 2.983h16.845a1.989 1.989 0 0 0 1.7 -2.983l-8.423 -14.06a1.989 1.989 0 0 0 -3.4 0z"></path>
        <path d="M12 9v4"></path>
        <path d="M12 17h.01"></path>
      `,
    },
    eye: {
      svg: `
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <path d="M10 12a2 2 0 1 0 4 0a2 2 0 0 0 -4 0"></path>
        <path d="M21 12c-2.4 4 -5.4 6 -9 6c-3.6 0 -6.6 -2 -9 -6c2.4 -4 5.4 -6 9 -6c3.6 0 6.6 2 9 6"></path>
      `,
    },
    "eye-off": {
      svg: `
        <path d="M10.585 10.587a2 2 0 0 0 2.829 2.828"></path>
        <path d="M16.681 16.673a8.717 8.717 0 0 1 -4.681 1.327c-3.6 0 -6.6 -2 -9 -6c1.272 -2.12 2.712 -3.678 4.32 -4.674m2.86 -1.146a9.055 9.055 0 0 1 1.82 -.18c3.6 0 6.6 2 9 6c-.666 1.11 -1.379 2.067 -2.138 2.87"></path>
        <path d="M3 3l18 18"></path>
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
