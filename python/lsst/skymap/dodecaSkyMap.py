# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#
"""
@todo
- Consider tweaking pixel scale so the average scale is as specified, rather than the scale at the center
"""
import math
import numpy

import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
from . import detail
from .baseSkyMap import BaseSkyMap
from .tractInfo import TractInfo

_TinyFloat = numpy.finfo(float).tiny

# Default tract overlap is approximately one field diameter
_DefaultTractOverlap = afwGeom.Angle(3.5, afwGeom.degrees)

# Default patch border -- approx. 50" worth of pixels
_DefaultPatchBorder = 250

# LSST plate scale is 50 um/arcsec
# LSST pixel size is 10 um
# Default sky pixel scale is the same as the image pixel scale
_DefaultPlateScale = afwGeom.Angle(10.0 / 50.0, afwGeom.arcseconds)

# Default patchInnerDimensions
_DefaultPatchInnerDimensions = (4000, 4000)

def _coordFromVec(vec, defRA=None):
    """Convert an ICRS cartesian vector to an ICRS Coord
    
    @param[in] vec: an ICRS catesian vector as a sequence of three floats
    @param[in] defRA: the RA to use if the vector is too near a pole (an afwGeom Angle);
                ignored if not near a pole
    
    @throw RuntimeError if vec too near a pole and defRA is None
    """
    if abs(vec[0]) < _TinyFloat and abs(vec[1]) < _TinyFloat:
        if defRA is None:
            raise RuntimeError("At pole and defRA==None")
        if vec[2] > 0:
            dec = 90.0
        else:
            dec = -90.0
        return afwCoord.makeCoord(afwCoord.ICRS, defRA, afwGeom.Angle(dec, afwGeom.degrees))
    return afwCoord.makeCoord(afwCoord.ICRS, afwGeom.Point3D(*vec))
        

class DodecaSkyMap(BaseSkyMap):
    """Dodecahedron-based sky map pixelization.
        
    DodecaSkyMap divides the sky into 12 overlapping Tracts arranged as the faces of a dodecahedron.
    """
    def __init__(self,
        patchInnerDimensions = _DefaultPatchInnerDimensions,
        patchBorder = _DefaultPatchBorder,
        tractOverlap = _DefaultTractOverlap,
        pixelScale = _DefaultPlateScale,
        projection = "STG",
        withTractsOnPoles = False,
    ):
        """Construct a DodecaSkyMap

        @param[in] patchInnerDimensions: dimensions of inner region of patches (x,y pixels)
        @param[in] patchBorder: overlap between adjacent patches (in pixels, one int)
        @param[in] tractOverlap: minimum overlap between adjacent sky tracts; an afwGeom.Angle
        @param[in] pixelScale: nominal pixel scale (angle on sky/pixel); an afwGeom.Angle
        @param[in] projection: one of the FITS WCS projection codes, such as:
          - STG: stereographic projection
          - MOL: Molleweide's projection
          - TAN: tangent-plane projection
        @param[in] withTractsOnPoles: if True center a tract on each pole, else put a vertex on each pole
        """
        self._version = (1, 0) # for pickle
        self._dodecahedron = detail.Dodecahedron(withFacesOnPoles = withTractsOnPoles)
        BaseSkyMap.__init__(self,
            patchInnerDimensions = patchInnerDimensions,
            patchBorder = patchBorder,
            tractOverlap = tractOverlap,
            pixelScale = pixelScale,
            projection = projection,
        )

        for id in range(12):
            tractVec = self._dodecahedron.getFaceCtr(id)
            tractCoord = _coordFromVec(tractVec, defRA=afwGeom.Angle(0))
            tractRA = tractCoord.getLongitude()
            vertexVecList = self._dodecahedron.getVertices(id)
            
            self._tractInfoList.append(
                TractInfo(
                    id = id,
                    patchInnerDimensions = self._patchInnerDimensions,
                    patchBorder = self._patchBorder,
                    ctrCoord = tractCoord,
                    vertexCoordList = [_coordFromVec(vec, defRA=tractRA) for vec in vertexVecList],
                    tractOverlap = self.getTractOverlap(),
                    wcsFactory = self._wcsFactory,
                )
            )
    
    def __getstate__(self):
        """Support pickle
        
        @note: angle arguments are persisted in radians
        """
        return dict(
            version = self._version,
            patchInnerDimensions = tuple(self.getPatchInnerDimensions()),
            patchBorder = self.getPatchBorder(),
            tractOverlap = self.getTractOverlap().asRadians(),
            pixelScale = self.getPixelScale().asRadians(),
            projection = self.getProjection(),
            withTractsOnPoles = self.getWithTractsOnPoles(),
        )
    
    def __setstate__(self, argDict):
        """Support unpickle
        """
        version = argDict.pop("version")
        if version >= (2, 0):
            raise runtimeError("Version = %s >= (2,0); cannot unpickle" % (version,))
        for angleArg in ("tractOverlap", "pixelScale"):
            argDict[angleArg] = afwGeom.Angle(argDict[angleArg], afwGeom.radians)
        self.__init__(**argDict)
    
    def findTract(self, coord):
        """Find the tract whose inner region includes the coord.
        
        @param[in] coord: sky coordinate (afwCoord.Coord)
        @return TractInfo for tract whose inner region includes the coord.
        
        @note This routine will be more efficient if coord is ICRS.
        """
        return self[self._dodecahedron.getFaceInd(coord.toIcrs().getVector())]
    
    def getVersion(self):
        """Return version (e.g. for pickle)
        
        @return version as a pair of integers
        """
        return self._version
    
    def getWithTractsOnPoles(self):
        """Return withTractsOnPoles parameter
        
        @return withTractsOnPoles as a bool
        """
        return self._dodecahedron.getWithFacesOnPoles()