import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree


def test_intersection_union_area():
    a, b = box(0, 0, 2, 2), box(1, 1, 3, 3)
    assert a.intersection(b).area == pytest.approx(1)
    assert a.union(b).area == pytest.approx(7)
    assert a.difference(b).area == pytest.approx(3)
    assert a.intersection(b).equals(box(1, 1, 2, 2))
    assert a.intersection(box(3, 3, 4, 4)).is_empty


def test_crossing_and_spatial_index():
    crossing = LineString([(0, 0), (2, 2)]).intersection(LineString([(0, 2), (2, 0)]))
    assert crossing.equals(Point(1, 1))
    geometries = np.array([box(0, 0, 1, 1), box(2, 2, 3, 3), box(10, 10, 11, 11)])
    assert set(STRtree(geometries).query(box(0.5, 0.5, 2.5, 2.5), predicate='intersects')) == {0, 1}
    np.testing.assert_allclose(shapely.area(geometries), [1, 1, 1])


def test_roundtrip_invalid_and_negative_control():
    shape = box(0, 0, 2, 2).difference(box(0.5, 0.5, 1.5, 1.5))
    assert shapely.from_wkb(shapely.to_wkb(shape)).equals(shape)
    assert shape.area == 3
    invalid = shapely.from_wkt('POLYGON ((0 0, 2 2, 0 2, 2 0, 0 0))')
    assert not invalid.is_valid
    assert shapely.make_valid(invalid).is_valid
    with pytest.raises(shapely.errors.GEOSException):
        shapely.from_wkt('NOT A GEOMETRY')
    # Deliberately wrong geometry must be rejected by the same area oracle.
    with pytest.raises(AssertionError):
        assert shape.area == pytest.approx(4)
