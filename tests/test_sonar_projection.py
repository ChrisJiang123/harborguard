"""Check the public projection against actual rendered annotation centers."""
import math
import pytest
from ml.sonar.render import range_bearing_to_pixel, render_ping


@pytest.mark.parametrize("distance,bearing", [(30, 0), (75, 0), (100, -30), (100, 30), (140, 0)])
def test_projection_matches_rendered_center(distance, bearing):
    target = dict(cls="uuv", range_m=distance, bearing_deg=bearing,
                  length_m=4, width_m=2, aspect_deg=0)
    _, annotations = render_ping([target], noise=.05, seed=7)
    assert len(annotations) == 1
    x1, y1, x2, y2 = annotations[0]["bbox"]
    x, y = range_bearing_to_pixel(distance, bearing)
    assert math.hypot(x - (x1+x2)/2, y - (y1+y2)/2) <= 3
