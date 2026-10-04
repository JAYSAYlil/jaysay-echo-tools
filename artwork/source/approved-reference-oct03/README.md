# Approved reference study (2026-10-03)

This is a review-only implementation study of the user's approved full-upgrade concept. It starts from the untouched 32×32 0.1.1 item texture and draws four progressive material overlays in a separate source script. It does not edit production assets, Java, the existing 95-candidate set, installed mods, or item display transforms.

Run from the repository root with `python artwork/source/approved-reference-oct03/render_approved_reference.py`. Output is written to `artwork/validation/v0.1.2/approved-reference-oct03/`.

The six comparison states are the baseline, each material alone at maximum, and all materials at maximum. The validation folder includes white and dark backgrounds, a nearest-neighbor 16px inventory view, individual 32px states, a concept comparison, and a large nearest-neighbor view for pixel review.
