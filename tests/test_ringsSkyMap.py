import unittest

import lsst.utils.tests
import lsst.afw.geom

from lsst.skymap.ringsSkyMap import RingsSkyMap
from helper import skyMapTestCase


class RingsTestCase(skyMapTestCase.SkyMapTestCase):

    def setUp(self):
        config = RingsSkyMap.ConfigClass()
        config.numRings = 3
        self.setAttributes(
            SkyMapClass=RingsSkyMap,
            name="rings",
            config=config,
            numTracts=26,
            neighborAngularSeparation=None,  # no uniform tract separation
            numNeighbors=None,    # ignored because neighborAngularSeparation=None
        )

    def testPoles(self):
        """Test that findAllTracts behaves at the poles

        Testing fix to DM-10686.
        """
        skymap = self.getSkyMap()
        for ra in (0, 123, 321, 359.9):
            tracts = skymap.findAllTracts(lsst.afw.geom.SpherePoint(ra, 90, lsst.afw.geom.degrees))
            self.assertListEqual(tracts, [skymap[len(skymap) - 1]])
            tracts = skymap.findAllTracts(lsst.afw.geom.SpherePoint(ra, -90, lsst.afw.geom.degrees))
            self.assertListEqual(tracts, [skymap[0]])

    def testSha1Compare(self):
        """Test that RingsSkyMap's extra state is included in its hash."""
        defaultSkyMap = self.getSkyMap()
        for numRings in (4, 5):
            config = self.getConfig()
            config.numRings = numRings
            skyMap = self.getSkyMap(config=config)
            self.assertNotEqual(skyMap, defaultSkyMap)
        for raStart in (60.0, 75.0):
            config = self.getConfig()
            config.raStart = raStart
            skyMap = self.getSkyMap(config=config)
            self.assertNotEqual(skyMap, defaultSkyMap)


class HscRingsTestCase(lsst.utils.tests.TestCase):
    def setUp(self):
        # This matches the HSC SSP configuration, on which the problem was discovered
        config = RingsSkyMap.ConfigClass()
        config.numRings = 120
        config.projection = "TAN"
        config.tractOverlap = 1.0/60  # Overlap between tracts (degrees)
        config.pixelScale = 0.168
        self.skymap = RingsSkyMap(config)

    def tearDown(self):
        del self.skymap

    def testDm7770(self):
        """Test that DM-7770 has been fixed

        These operations previously caused:
            lsst::pex::exceptions::RuntimeError: 'Error: wcslib
            returned a status code of 9 at sky 30.18, -3.8 deg:
            One or more of the world coordinates were invalid'

        We are only testing function, and not the actual results.
        """
        coordList = [lsst.afw.geom.SpherePoint(ra, dec, lsst.afw.geom.degrees) for
                     ra, dec in [(30.18, -3.8), (31.3, -3.8), (31.3, -2.7), (30.18, -2.7)]]
        for coord in coordList:
            self.skymap.findAllTracts(coord)
        self.skymap.findTractPatchList(coordList)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
