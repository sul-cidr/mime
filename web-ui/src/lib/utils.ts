export const formatSeconds = (seconds: number) => {
  return [
    [Math.floor(seconds / 31536000), "y"],
    [Math.floor((seconds % 31536000) / 86400), "d"],
    [Math.floor(((seconds % 31536000) % 86400) / 3600), "h"],
    [Math.floor((((seconds % 31536000) % 86400) % 3600) / 60), "m"],
    [Math.round((((seconds % 31536000) % 86400) % 3600) % 60), "s"],
  ]
    .map(([c, t]) => (c ? `${c}${t}` : ""))
    .join("");
};

export const clamp = (num: number, min: number, max: number): number =>
  num < min ? min : num > max ? max : num;
