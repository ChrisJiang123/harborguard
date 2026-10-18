"""Numerical invariants for the separate regional preprocessing product."""
import importlib.util
import unittest
import tempfile
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('shore_fill', Path(__file__).with_name('prepare-shore-fill.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FillTests(unittest.TestCase):
    def test_nodata_is_not_a_height(self):
        source = np.array([[10., 10., 10.], [10., np.nan, 10.], [10., 10., 10.]])
        smooth = module.smooth_masked(source)
        self.assertTrue(np.isnan(smooth[1, 1]))
        np.testing.assert_array_equal(smooth[np.isfinite(smooth)], 10.)
        bounds = dict(west=0., east=2., south=0., north=2.)
        sampled = module.resample(source, bounds, bounds, (5, 5))
        self.assertTrue(np.isnan(sampled[2, 2]))
        self.assertTrue(np.isnan(sampled[1, 1]), 'Do not bilinearly mix a missing support cell as zero')
        self.assertEqual(sampled[0, 0], 10.)

    def test_scaled_int16_and_missing_mask(self):
        import rasterio
        from rasterio.transform import from_origin
        target = dict(west=-117.995, east=-117.985, north=33.995, south=33.985)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'test.tif'
            with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1,
                               dtype='int16', crs='EPSG:4326', transform=from_origin(-118,34,.01,.01), nodata=-9999) as ds:
                ds.write(np.array([[100,-9999],[200,300]], dtype=np.int16),1)
                ds.scales=(.1,)
            values, _ = module.read_regional(path,target,(2,2),'NAVD88')
            self.assertAlmostEqual(values[0,0],10.,places=4)
            self.assertAlmostEqual(values[1,0],20.,places=4)
            self.assertTrue(np.isnan(values[0,1]),'NoData must not turn into a scaled negative height')
            with rasterio.open(path,'r+') as ds:
                ds.nodata=None
            with self.assertRaises(ValueError):
                module.read_regional(path,target,(2,2),'NAVD88')

    def test_fill_only_changes_unsupported_domain(self):
        measured = np.full((9, 9), np.nan)
        measured[:, :3] = 12.
        before = measured.copy()
        regional = np.full((9, 9), 20.)
        regional[-1, -1] = np.nan
        fused = module.blend_fill(regional, measured, (8., 8.), 32.)
        np.testing.assert_array_equal(measured, before)
        np.testing.assert_array_equal(fused[:, :3], measured[:, :3])
        self.assertTrue(np.isnan(fused[-1, -1]), 'An unknown regional location remains unknown')
        np.testing.assert_allclose(fused[0, 3:7], [13.25, 16., 18.75, 20.])
        self.assertTrue(np.all(np.diff(fused[0]) >= 0), 'Transition must approach the regional floor without overshoot')

    def test_no_measurements_does_not_invent_a_boundary(self):
        regional = np.array([[1., 2.], [3., np.nan]])
        result = module.blend_fill(regional, np.full((2, 2), np.nan), (8., 8.), 32.)
        np.testing.assert_array_equal(result, regional)


if __name__ == '__main__':
    unittest.main()
