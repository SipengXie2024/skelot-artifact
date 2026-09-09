"""Shared colour palette for Naive-vs-SkelOT comparison figures.

Canonical values, ported from the FIG4_* constants originally defined in
render_all.py (Fig 2 and Fig 4 push-invariance). Every figure that compares
Naive AOT against SkelOT should import from here rather than redefining these
hex values locally, so "purple = Naive, green = SkelOT" reads the same way
across the paper.

Categorical figures that break a single quantity into unrelated parts (Fig 4's
four-chain comparison, Fig 9's cycle-attribution breakdown) are a different
kind of chart and are not expected to use this palette.
"""

NAIVE_DARK = "#7B1FA2"
NAIVE_LIGHT = "#C7A4D8"
# A third, deeper purple for "Naive AOT" read under a harsher constraint (e.g.
# forced to match SkelOT's coverage set one artifact per contract). Still
# purple because it is still Naive AOT, just a different reading of it.
NAIVE_DEEP = "#4A148C"

SKELOT_DARK = "#2E7D32"
SKELOT_LIGHT = "#A5D6A7"

# All-variant is a SkelOT configuration (shares skeletons) that skips the
# invariant/variant split, so it is neither plain Naive AOT nor the split
# SkelOT design. It gets its own hue rather than reusing NAIVE_DEEP, which is
# a Naive-family colour and would wrongly suggest All-variant is a Naive
# reading rather than a SkelOT one.
ALLVAR_LIGHT = "#F0C674"
ALLVAR_DARK = "#B8860B"

AXIS = "#262626"
NO_CHANGE = "#C62828"
