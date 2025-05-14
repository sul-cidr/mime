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

// Adapted from https://stackoverflow.com/questions/27205018/multiply-2-matrices-in-javascript
export const matrixProd = (A: number[][], B: number[][]): number[][] =>
  A.map((row, i) =>
    B[0].map((_, j) =>
      row.reduce((acc, _, n) =>
        acc + A[i][n] * B[n][j], 0
      )
    )
  )
