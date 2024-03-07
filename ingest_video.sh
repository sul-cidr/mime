#!/bin/zsh

#just add-video-4dh $1
just add-shots $1
just do-poem-embeddings $1
just add-motion $1
just calculate-pose-interest $1
just match-faces $1
just cluster-faces $1 16
just cluster-poses $1 20
just cluster-plot-poses $1 20
