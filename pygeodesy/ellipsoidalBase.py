
# -*- coding: utf-8 -*-

u'''(INTERNAL) Ellipsoidal base classes.

Pure Python implementation of geodesy tools for ellipsoidal earth models,
transcribed in part from JavaScript originals by I{(C) Chris Veness 2005-2016}
and published under the same MIT Licence**, see for example U{latlon-ellipsoidal
<https://www.Movable-Type.co.UK/scripts/geodesy/docs/latlon-ellipsoidal.js.html>}.

@newfield example: Example, Examples
'''

from bases import LatLonHeightBase
from datum import Datum, Datums
from fmath import EPS, EPS1, fsum_, hypot, hypot1
from lazily import _ALL_DOCS
from named import LatLon3Tuple, Vector3Tuple
from utily import degrees90, degrees180, property_RO, sincos2
from vector3d import Vector3d

from math import atan2, copysign, sqrt

__all__ = _ALL_DOCS('CartesianBase', 'LatLonEllipsoidalBase')
__version__ = '19.05.10'


class CartesianBase(Vector3d):
    '''(INTERNAL) Base class for ellipsoidal C{Cartesian}.
    '''

    def _applyHelmert(self, transform, inverse=False):
        '''(INTERNAL) Return a new (geocentric) Cartesian point
           by applying a Helmert transform to this point.

           @param transform: Transform to apply (L{Transform}).
           @keyword inverse: Optionally, apply the inverse of
                             Helmert transform (C{bool}).

           @return: The transformed point (L{Cartesian}).
        '''
        x, y, z = self.to3xyz()
        return self.classof(*transform.transform(x, y, z, inverse))

    def to3llh(self, datum=Datums.WGS84):
        '''Convert this (geocentric) Cartesian (x/y/z) point to
           (ellipsoidal, geodetic) lat-, longitude and height on
           the given datum.

           Uses Bowring’s (1985) formulation for μm precision in concise
           form: U{'The accuracy of geodetic latitude and height equations'
           <https://www.ResearchGate.net/publication/
           233668213_The_Accuracy_of_Geodetic_Latitude_and_Height_Equations>},
           B. R. Bowring, Survey Review, Vol 28, 218, Oct 1985.

           See also Ralph M. Toms U{'An Efficient Algorithm for Geocentric to
           Geodetic Coordinate Conversion'<https://www.OSTI.gov/scitech/biblio/110235>},
           Sept 1995 and U{'An Improved Algorithm for Geocentric to Geodetic Coordinate
           Conversion'<https://www.OSTI.gov/scitech/servlets/purl/231228>},
           Apr 1996, from Lawrence Livermore National Laboratory.

           @keyword datum: Optional datum to use (L{Datum}).

           @return: A L{LatLon3Tuple}C{(lat, lon, height)}.
        '''
        E = datum.ellipsoid
        x, y, z = self.to3xyz()

        p = hypot(x, y)  # distance from minor axis
        r = hypot(p, z)  # polar radius

        if min(p, r) > EPS:
            # parametric latitude (Bowring eqn 17, replaced)
            t = (E.b * z) / (E.a * p) * (1 + E.e22 * E.b / r)
            c = 1 / hypot1(t)
            s = t * c

            # geodetic latitude (Bowring eqn 18)
            a = atan2(z + E.e22 * E.b * s**3,
                      p - E.e2  * E.a * c**3)
            b = atan2(y, x)  # ... and longitude

            # height above ellipsoid (Bowring eqn 7)
            sa, ca = sincos2(a)
#           r = E.a / E.e2s(sa)  # length of normal terminated by minor axis
#           h = p * ca + z * sa - (E.a * E.a / r)
            h = fsum_(p * ca, z * sa, -E.a * E.e2s(sa))

            a, b = degrees90(a), degrees180(b)

        # see <https://GIS.StackExchange.com/questions/28446>
        elif p > EPS:  # latitude arbitrarily zero
            a, b, h = 0.0, degrees180(atan2(y, x)), p - E.a
        else:  # polar latitude, longitude arbitrarily zero
            a, b, h = copysign(90.0, z), 0.0, abs(z) - E.b
        return self._xnamed(LatLon3Tuple(a, b, h))

    def _to3LLh(self, datum, LL):
        '''(INTERNAL) Helper for C{subclass.toLatLon} and C{.to3llh}.
        '''
        r = self.to3llh(datum)  # LatLon3Tuple
        if LL is not None:
            r = LL(r.lat, r.lon, height=r.height, datum=datum)
            r = self._xnamed(r)
        return r

    def toStr(self, prec=3, fmt='[%s]', sep=', '):  # PYCHOK expected
        '''Return the string representation of this cartesian.

           @keyword prec: Optional number of decimals, unstripped (C{int}).
           @keyword fmt: Optional enclosing backets format (string).
           @keyword sep: Optional separator to join (string).

           @return: Cartesian represented as "[x, y, z]" (string).
        '''
        return Vector3d.toStr(self, prec=prec, fmt=fmt, sep=sep)


class LatLonEllipsoidalBase(LatLonHeightBase):
    '''(INTERNAL) Base class for ellipsoidal C{LatLon}.
    '''
    _convergence  = None  #: (INTERNAL) UTM/UPS meridian convergence (C{degrees}).
    _datum        = Datums.WGS84  #: (INTERNAL) Datum (L{Datum}).
    _elevation2   = ()    #: (INTERNAL) cached C{elevation2} result.
    _etm          = None  #: (INTERNAL) cache toEtm (L{Etm}).
    _geoidHeight2 = ()    #: (INTERNAL) cached C{geoidHeight2} result.
    _lcc          = None  #: (INTERNAL) cache toLcc (C{Lcc}).
    _osgr         = None  #: (INTERNAL) cache toOsgr (C{Osgr}).
    _scale        = None  #: (INTERNAL) UTM/UPS scale factor (C{float}).
    _ups          = None  #: (INTERNAL) cache toUps (L{Ups}).
    _utm          = None  #: (INTERNAL) cache toUtm (L{Utm}).
    _wm           = None  #: (INTERNAL) cache toWm (webmercator.Wm instance).
    _3xyz         = None  #: (INTERNAL) Cache (L{Vector3Tuple})

    def __init__(self, lat, lon, height=0, datum=None, name=''):
        '''Create an (ellipsoidal) C{LatLon} point frome the given
           lat-, longitude and height on the given datum.

           @param lat: Latitude (C{degrees} or DMS C{[N|S]}).
           @param lon: Longitude (C{degrees} or DMS C{str[E|W]}).
           @keyword height: Optional elevation (C{meter}, the same units
                            as the datum's half-axes).
           @keyword datum: Optional datum to use (L{Datum}).
           @keyword name: Optional name (string).

           @example:

           >>> p = LatLon(51.4778, -0.0016)  # height=0, datum=Datums.WGS84
        '''
        LatLonHeightBase.__init__(self, lat, lon, height=height, name=name)
        if datum:  # check datum
            self.datum = datum

    def _Radjust2(self, adjust, datum, meter_text2):
        '''(INTERNAL) Adjust elevation or geoidHeight with difference
           in Gaussian radii of curvature of given datum and NAD83.

           @note: This is an arbitrary, possibly incorrect adjustment.
        '''
        if adjust:  # Elevation2Tuple or GeoidHeight2Tuple
            m, t = meter_text2
            if isinstance(m, float):
                n = Datums.NAD83.ellipsoid.rocGauss(self.lat)
                if min(abs(m), n) > EPS:
                    # use ratio, datum and NAD83 units may differ
                    e = self.ellipsoid(datum).rocGauss(self.lat)
                    if min(abs(e - n), e) > EPS:
                        m *= e / n
                        meter_text2 = meter_text2.classof(m, t)
        return self._xnamed(meter_text2)

    def _update(self, updated):
        if updated:  # reset caches
            self._etm = self._lcc = self._osgr = self._ups = \
                        self._utm = self._wm = self._3xyz = None
            self._elevation2 = self._geoidHeight2 = ()
            LatLonHeightBase._update(self, updated)

    def _xcopy(self, *attrs):
        '''(INTERNAL) Make copy with add'l, subclass attributes.
        '''
        return LatLonHeightBase._xcopy(self, '_datum', *attrs)

    def antipode(self, height=None):
        '''Return the antipode, the point diametrically opposite
           to this point.

           @keyword height: Optional height of the antipode, height
                            of this point otherwise (C{meter}).

           @return: The antipodal point (C{LatLon}).
        '''
        lla = LatLonHeightBase.antipode(self, height=height)
        if lla.datum != self.datum:
            lla.datum = self.datum
        return lla

    @property_RO
    def convergence(self):
        '''Get this point's UTM or UPS meridian convergence (C{degrees})
           or C{None} if not converted from L{Utm} ot L{Ups}.
        '''
        return self._convergence

    def convertDatum(self, datum):
        '''Convert this C{LatLon} point to a new datum.

           @param datum: Datum to convert to (L{Datum}).

           @return: The converted point (ellipsoidal C{LatLon}).

           @example:

           >>> pWGS84 = LatLon(51.4778, -0.0016)  # default Datums.WGS84
           >>> pOSGB  = pWGS84.convertDatum(Datums.OSGB36)  # 51.477284°N, 000.00002°E
        '''
        if self.datum == datum:
            return self.copy()

        elif self.datum == Datums.WGS84:
            # converting from WGS 84
            ll, t, i = self, datum.transform, False

        elif datum == Datums.WGS84:
            # converting to WGS84, use inverse transform
            ll, t, i = self, self.datum.transform, True

        else:  # neither self.datum nor datum is WGS84, convert to WGS84 first
            ll, t, i = self.convertDatum(Datums.WGS84), datum.transform, False

        return ll.toCartesian()._applyHelmert(t, i).toLatLon(datum=datum)

    @property
    def datum(self):
        '''Get this point's datum (L{Datum}).
        '''
        return self._datum

    @datum.setter  # PYCHOK setter!
    def datum(self, datum):
        '''Set this point's datum without conversion.

           @param datum: New datum (L{Datum}).

           @raise TypeError: The B{C{datum}} is not a L{Datum}.

           @raise ValueError: The B{C{datum}} is not ellipsoidal.
        '''
        if not isinstance(datum, Datum):
            raise TypeError('%r not a %s: %r' % ('datum', Datum.__name__, datum))
        if not datum.isEllipsoidal:
            raise ValueError('%r not %s: %r' % ('datum', 'ellipsoidal', datum))
        self._update(datum != self._datum)
        self._datum = datum

    def distanceTo2(self, other):
        '''Approximate the distance and (initial) bearing between this
           and an other (ellipsoidal) point based on the radii of curvature.

           Suitable only for short distances up to a few hundred Km
           or Miles and only between non-near-polar points.

           @param other: The other point (C{LatLon}).

           @return: An L{Distance2Tuple}C{(distance, initial)}.

           @raise TypeError: The B{C{other}} point is not C{LatLon}.

           @raise ValueError: Incompatible datum ellipsoids.

           @see: Method L{Ellipsoid.distance2} and U{Local, flat earth
                 approximation<https://www.EdWilliams.org/avform.htm#flat>}.
        '''
        return self.ellipsoids(other).distance2(self.lat,  self.lon,
                                               other.lat, other.lon)

    def elevation2(self, adjust=True, datum=Datums.WGS84, timeout=2):
        '''Return elevation of this point for its or the given datum.

           @keyword adjust: Adjust the elevation for a B{C{datum}} other
                            than C{NAD83}.
           @keyword datum: Optional datum (L{Datum}).
           @keyword timeout: Optional query timeout (seconds).

           @return: An L{Elevation2Tuple}C{(elevation, data_source)}
                    or C{(None, error)} in case of errors.

           @note: The adjustment applied is the difference in geocentric
                  earth radius for the B{C{datum}} used and the C{NAV83}
                  datum upon which L{elevations.elevation2} is based.

           @note: NED elevation is only available for locations within
                  the U{Conterminous US (CONUS)
                  <https://WikiPedia.org/wiki/Contiguous_United_States>}.

           @see: Function L{elevations.elevation2} and method
                 L{Ellipsoid.Rgeocentric} for further details and
                 possible C{error}s.
        '''
        if not self._elevation2:  # get elevation and data source
            from elevations import elevation2
            self._elevation2 = elevation2(self.lat, self.lon,
                                          timeout=timeout)
        return self._Radjust2(adjust, datum, self._elevation2)

    def ellipsoid(self, datum=Datums.WGS84):
        '''Return the ellipsoid of this point's datum or the given datum.

           @keyword datum: Optional datum (L{Datum}).

           @return: The ellipsoid (L{Ellipsoid}).
        '''
        return getattr(self, 'datum', datum).ellipsoid

    def ellipsoids(self, other):
        '''Check the type and ellipsoid of this and an other point's datum.

           @param other: The other point (C{LatLon}).

           @return: This point's datum ellipsoid (L{Ellipsoid}).

           @raise TypeError: The B{C{other}} point is not C{LatLon}.

           @raise ValueError: Incompatible datum ellipsoids.
        '''
        self.others(other)

        E = self.ellipsoid()
        try:  # other may be Sphere, etc.
            e = other.ellipsoid()
        except AttributeError:
            try:  # no ellipsoid method, try datum
                e = other.datum.ellipsoid
            except AttributeError:
                e = E  # no datum, XXX assume equivalent?
        if e != E:
            c = E.classname
            raise ValueError('%s %s mistmatch: %ss.%s vs %ss.%s' %
                             ('other', c, c, e.name, c, E.name))
        return E

    def geoidHeight2(self, adjust=False, datum=Datums.WGS84, timeout=2):
        '''Return geoid height of this point for its or the given datum.

           @keyword adjust: Adjust the geoid height for a B{C{datum}} other
                            than C{NAD83/NADV88}.
           @keyword datum: Optional datum (L{Datum}).
           @keyword timeout: Optional query timeout (seconds).

           @return: An L{GeoidHeight2Tuple}C{(height,
                    model_name)} or C{(None, error)} in case of errors.

           @note: The adjustment applied is the difference in geocentric
                  earth radius for the given B{C{datum}} and the C{NAV83/NADV88}
                  datum upon which L{elevations.geoidHeight2} is based.

           @note: The geoid height is only available for locations within
                  the U{Conterminous US (CONUS)
                  <https://WikiPedia.org/wiki/Contiguous_United_States>}.

           @see: Function L{elevations.geoidHeight2} and method
                 L{Ellipsoid.Rgeocentric} for further details and
                 possible C{error}s.
        '''
        if not self._geoidHeight2:  # get elevation and data source
            from elevations import geoidHeight2
            self._geoidHeight2 = geoidHeight2(self.lat, self.lon,
                                              model=0, timeout=timeout)
        return self._Radjust2(adjust, datum, self._geoidHeight2)

    @property_RO
    def isEllipsoidal(self):
        '''Check whether this C{LatLon} point is ellipsoidal (C{bool}).
        '''
        return self.datum.isEllipsoidal

    @property_RO
    def isSpherical(self):
        '''Check whether this C{LatLon} point is spherical (C{bool}).
        '''
        return self.datum.isSpherical

    def parse(self, strll, height=0, datum=None, sep=','):
        '''Parse a string representing this C{LatLon} point.

           The lat- and longitude must be separated by a sep[arator]
           character.  If height is present it must follow and be
           separated by another sep[arator].  Lat- and longitude
           may be swapped, provided at least one ends with the
           proper compass direction.

           For more details, see functions L{parse3llh} and L{parseDMS}
           in sub-module L{dms}.

           @param strll: Lat, lon [, height] (string).
           @keyword height: Optional, default height (C{meter} or C{None}).
           @keyword datum: Optional, default datum (L{Datum}).
           @keyword sep: Optional separator (string).

           @return: The point (L{LatLonEllipsoidalBase}).

           @raise ValueError: Invalid B{C{strll}}.
        '''
        from dms import parse3llh
        a, b, h = parse3llh(strll, height=height, sep=sep)
        return self.classof(a, b, height=h, datum=datum or self.datum)

    @property_RO
    def scale(self):
        '''Get this point's UTM grid or UPS point scale factor (C{float})
           or C{None} if not converted from L{Utm} or L{Ups}.
        '''
        return self._scale

    def to3xyz(self):  # overloads _LatLonHeightBase.to3xyz
        '''Convert this (ellipsoidal) geodetic C{LatLon} point to
           (geocentric) cartesian x/y/z components.

           @return: A L{Vector3Tuple}C{(x, y, z)}.
        '''
        if self._3xyz is None:
            a, b = self.to2ab()
            sa, ca, sb, cb = sincos2(a, b)

            E = self.ellipsoid()
            # radius of curvature in prime vertical
            t = E.e2s2(sa)
            if t > EPS1:
                r = E.a
            elif t > EPS:
                r = E.a / sqrt(t)
            else:
                r = 0

            h = self.height
            t = (h + r) * ca
            self._3xyz = Vector3Tuple(t * cb, t * sb, (h + r * E.e12) * sa)
        return self._xrenamed(self._3xyz)

    def toEtm(self):
        '''Convert this C{LatLon} point to an ETM coordinate.

           @return: The ETM coordinate (L{Etm}).

           @see: Function L{toEtm8}.
        '''
        if self._etm is None:
            from etm import toEtm8, Etm  # PYCHOK recursive import
            self._etm = toEtm8(self, datum=self.datum, Etm=Etm)
        return self._etm

    def toLcc(self):
        '''Convert this C{LatLon} point to a Lambert location.

           @see: Function L{toLcc} in module L{lcc}.

           @return: The Lambert location (L{Lcc}).
        '''
        if self._lcc is None:
            from lcc import Lcc, toLcc  # PYCHOK recursive import
            self._lcc = toLcc(self, height=self.height, Lcc=Lcc,
                                                        name=self.name)
        return self._lcc

    def toOsgr(self):
        '''Convert this C{LatLon} point to an OSGR coordinate.

           @see: Function L{toOsgr} in module L{osgr}.

           @return: The OSGR coordinate (L{Osgr}).
        '''
        if self._osgr is None:
            from osgr import Osgr, toOsgr  # PYCHOK recursive import
            self._osgr = toOsgr(self, datum=self.datum, Osgr=Osgr,
                                                        name=self.name)
        return self._osgr

    def toUps(self, pole='N', falsed=True):
        '''Convert this C{LatLon} point to a UPS coordinate.

           @keyword pole: Optional top/center of (stereographic)
                          projection (C{str}, 'N[orth]' or 'S[outh]').
           @keyword falsed: False easting and northing (C{bool}).

           @return: The UPS coordinate (L{Ups}).

           @see: Function L{toUps8}.
        '''
        if self._ups is None:
            from ups import toUps8, Ups  # PYCHOK recursive import
            self._ups = toUps8(self, datum=self.datum, Ups=Ups,
                                     pole=pole, falsed=falsed)
        return self._ups

    def toUtm(self):
        '''Convert this C{LatLon} point to a UTM coordinate.

           @return: The UTM coordinate (L{Utm}).

           @see: Function L{toUtm8}.
        '''
        if self._utm is None:
            from utm import toUtm8, Utm  # PYCHOK recursive import
            self._utm = toUtm8(self, datum=self.datum, Utm=Utm)
        return self._utm

    def toUtmUps(self, pole=''):
        '''Convert this C{LatLon} point to a UTM or UPS coordinate.

           @keyword pole: Optional top/center of UPS (stereographic)
                          projection (C{str}, 'N[orth]' or 'S[outh]').

           @return: The UTM or UPS coordinate (L{Utm} or L{Ups}).

           @raise TypeError: Result in L{Utm} or L{Ups}.

           @see: Function L{toUtmUps}.
        '''
        if self._utm:
            u = self._utm
        elif self._ups and (self._utm.pole == pole or not pole):
            u = self._ups
        else:
            from utmups import toUtmUps8, Utm, Ups  # PYCHOK recursive import
            u = toUtmUps8(self, datum=self.datum, Utm=Utm, Ups=Ups, pole=pole)
            if isinstance(u, Utm):
                self._utm = u
            elif isinstance(u, Ups):
                self._ups = u
            else:
                raise TypeError('%s: %r' % ('toUtmUps8', u))
        return u

    def toWm(self):
        '''Convert this C{LatLon} point to a WM coordinate.

           @see: Function L{toWm} in module L{webmercator}.

           @return: The WM coordinate (L{Wm}).
        '''
        if self._wm is None:
            from webmercator import toWm  # PYCHOK recursive import
            self._wm = toWm(self)
        return self._wm

# **) MIT License
#
# Copyright (C) 2016-2019 -- mrJean1 at Gmail dot com
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
