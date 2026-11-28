"""The countdown pill (`.rq-timer`) is exactly as wide as its clock: a flex column / grid cell must never stretch it
(Review Requests > Badge Approval Requests used to show a full-width brown bar)."""
import os
import unittest

CSS = open(os.path.join(os.path.dirname(__file__), "..", "css", "components.css"), encoding="utf-8").read()


class TestCountdownPillFit(unittest.TestCase):
    def rule(self, selector):
        return CSS.split(chr(10) + selector + " {")[1].split("}")[0]      # a rule that STARTS a line (not ".tlv-card .rq-timer {")

    def test_pill_is_shrink_wrapped(self):
        block = self.rule(".rq-timer")
        for part in ("display: inline-flex", "width: fit-content", "align-self: flex-start", "justify-self: start", "max-width: 100%", "flex: 0 0 auto", "white-space: nowrap"):
            self.assertIn(part, block, part)

    def test_the_card_extra_column_does_not_force_stretch_on_the_pill(self):
        # .lg-sb-extra is a flex column (children stretch by default); the pill opts out with align-self on itself
        extra = self.rule(".lg-saved-badge-card .lg-sb-extra")
        self.assertIn("flex-direction: column", extra)
        self.assertIn("align-self: flex-start", self.rule(".rq-timer"))


if __name__ == "__main__":
    unittest.main()
