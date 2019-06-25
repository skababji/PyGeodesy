
# -*- coding: utf-8 -*-

u'''Vincenty's ellipsoidal geodetic (lat-/longitude) and cartesian (x/y/z)
classes L{LatLon}, L{Cartesian} and L{VincentyError} and functions
L{areaOf} and L{perimeterOf}.

Pure Python implementation of geodesy tools for ellipsoidal earth models,
transcribed from JavaScript originals by I{(C) Chris Veness 2005-2016}
and published under the same MIT Licence**, see U{Vincenty geodesics
<https://www.Movable-Type.co.UK/scripts/LatLongVincenty.html>}.  More at
U{GeographicLib<https://PyPI.org/project/geographiclib>} and
U{GeoPy<https://PyPI.org/project/geopy>}.

Calculate geodesic distance between two points using the U{Vincenty
<https://WikiPedia.org/wiki/Vincenty's_formulae>} formulae and one of
several ellipsoidal earth models.  The default model is WGS-84, the
most accurate and widely used globally-applicable model for the earth
ellipsoid.

Other ellipsoids offering a better fit to the local geoid include
Airy (1830) in the UK, Clarke (1880) in Africa, International 1924
in much of Europe, and GRS-67 in South America.  North America
(NAD83) and Australia (GDA) use GRS-80, which is equivalent to the
WGS-84 model.

Great-circle distance uses a spherical model of the earth with the
mean earth radius defined by the International Union of Geodesy and
Geophysics (IUGG) as M{(2 * a + b) / 3 = 6371008.7714150598} meter or
approx. 6371009 meter (for WGS-84, resulting in an error of up to
about 0.5%).

Here's an example usage of C{ellipsoidalVincenty}:

    >>> from pygeodesy.ellipsoidalVincenty import LatLon
    >>> Newport_RI = LatLon(41.49008, -71.312796)
    >>> Cleveland_OH = LatLon(41.499498, -81.695391)
    >>> Newport_RI.distanceTo(Cleveland_OH)
    866,455.4329158525  # meter

You can change the ellipsoid model used by the Vincenty formulae
as follows:

    >>> from pygeodesy import Datums
    >>> from pygeodesy.ellipsoidalVincenty import LatLon
    >>> p = LatLon(0, 0, datum=Datums.OSGB36)

or by converting to anothor datum:

    >>> p = p.convertDatum(Datums.OSGB36)

@newfield example: Example, Examples
'''

# make sure int division yields float quotient
from __future__ import division

from datum import Datums
from ellipsoidalBase import CartesianBase, LatLonEllipsoidalBase
from fmath import EPS, fpolynomial, hypot, scalar
from lazily import _ALL_LAZY
from named import Bearing2Tuple, Destination2Tuple, Distance3Tuple
from points import ispolar  # PYCHOK ispolar
from utily import degrees90, degrees180, degrees360, sincos2, unroll180

from math import atan2, cos, radians, tan

# all public contants, classes and functions
__all__ = _ALL_LAZY.ellipsoidalVincenty + (
          'Cartesian', 'LatLon',
          'ispolar')
__version__ = '19.05.06'

division = 1 / 2  # double check int division, see .datum.py
if not division:
    raise ImportError('%s 1/2 == %d' % ('division', division))
del division


class VincentyError(ValueError):
    '''Error raised from Vincenty's direct and inverse methods
       for coincident points or lack of convergence.
    '''
    pass


class LatLon(LatLonEllipsoidalBase):
    '''Using the formulae devised by Thaddeus Vincenty (1975) with an
       ellipsoidal model of the earth to compute the geodesic distance
       and bearings between two given points or the destination point
       given an start point and initial bearing.

       Set the earth model to be used with the keyword argument
       datum.  The default is Datums.WGS84, which is the most globally
       accurate.  For other models, see the Datums in module datum.

       Note: This implementation of the Vincenty methods may not
       converge for some valid points, raising a VincentyError.  In
       that case, a result may be obtained by increasing the epsilon
       and/or the iteration limit, see properties L{LatLon.epsilon}
       and L{LatLon.iterations}.
    '''
    _epsilon    = 1.0e-12  # about 0.006 mm
    _iterations = 50

    def _xcopy(self, *attrs):
        '''(INTERNAL) Make copy with add'l, subclass attributes.
        '''
        return LatLonEllipsoidalBase._xcopy(self, '_epsilon', '_iterations', *attrs)

    def bearingTo(self, other, wrap=False):
        '''DEPRECATED, use method C{initialBearingTo}.
        '''
        return self.initialBearingTo(other, wrap=wrap)

    def bearingTo2(self, other, wrap=False):
        '''Compute the initial and final bearing (forward and reverse
           azimuth) from this to an other point, using Vincenty's
           inverse method.  See methods L{initialBearingTo} and
           L{finalBearingTo} for more details.

           @param other: The other point (L{LatLon}).
           @keyword wrap: Wrap and unroll longitudes (C{bool}).

           @return: A L{Bearing2Tuple}C{(initial, final)}..

           @raise TypeError: The B{C{other}} point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.
        '''
        r = Bearing2Tuple(*self._inverse(other, True, wrap)[1:])
        return self._xnamed(r)

    def destination(self, distance, bearing, height=None):
        '''Compute the destination point after having travelled
           for the given distance from this point along a geodesic
           given by an initial bearing, using Vincenty's direct
           method.  See method L{destination2} for more details.

           @param distance: Distance (C{meter}).
           @param bearing: Initial bearing (compass C{degrees360}).
           @keyword height: Optional height, overriding the default
                            height (C{meter}, same units as C{distance}).

           @return: The destination point (L{LatLon}).

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit.

           @example:

           >>> p = LatLon(-37.95103, 144.42487)
           >>> d = p.destination(54972.271, 306.86816)  # 37.6528°S, 143.9265°E
        '''
        return self._direct(distance, bearing, True, height=height)[0]

    def destination2(self, distance, bearing, height=None):
        '''Compute the destination point and the final bearing (reverse
           azimuth) after having travelled for the given distance from
           this point along a geodesic given by an initial bearing,
           using Vincenty's direct method.

           The distance must be in the same units as this point's datum
           axes, conventionally meter.  The distance is measured on the
           surface of the ellipsoid, ignoring this point's height.

           The initial and final bearing (forward and reverse azimuth)
           are in compass degrees.

           The destination point's height and datum are set to this
           point's height and datum.

           @param distance: Distance (C{meter}).
           @param bearing: Initial bearing (compass C{degrees360}).
           @keyword height: Optional height, overriding the default
                            height (C{meter}, same units as B{C{distance}}).

           @return: A L{Destination2Tuple}C{(destination, final)}.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit.

           @example:

           >>> p = LatLon(-37.95103, 144.42487)
           >>> b = 306.86816
           >>> d, f = p.destination2(54972.271, b)  # 37.652818°S, 143.926498°E, 307.1736
        '''
        r = Destination2Tuple(*self._direct(distance, bearing, True,
                                            height=height))
        return self._xnamed(r)

    def distanceTo(self, other, wrap=False):
        '''Compute the distance between this and an other point
           along a geodesic, using Vincenty's inverse method.
           See method L{distanceTo3} for more details.

           @param other: The other point (L{LatLon}).
           @keyword wrap: Wrap and unroll longitudes (C{bool}).

           @return: Distance (C{meter}).

           @raise TypeError: The B{C{other}} point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit and/or if this and the B{C{other}} point
                                 are near-antipodal.

           @example:

           >>> p = LatLon(50.06632, -5.71475)
           >>> q = LatLon(58.64402, -3.07009)
           >>> d = p.distanceTo(q)  # 969,954.166 m
        '''
        return self._inverse(other, False, wrap)

    def distanceTo3(self, other, wrap=False):
        '''Compute the distance, the initial and final bearing along a
           geodesic between this and an other point, using Vincenty's
           inverse method.

           The distance is in the same units as this point's datum axes,
           conventially meter.  The distance is measured on the surface
           of the ellipsoid, ignoring this point's height.

           The initial and final bearing (forward and reverse azimuth)
           are in compass degrees from North.

           @param other: Destination point (L{LatLon}).
           @keyword wrap: Wrap and unroll longitudes (C{bool}).

           @return: A L{Distance3Tuple}C{(distance, initial, final)}.

           @raise TypeError: The B{C{other}} point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit and/or if this and the B{C{other}} point
                                 are near-antipodal.
        '''
        r = Distance3Tuple(*self._inverse(other, True, wrap))
        return self._xnamed(r)

    @property
    def epsilon(self):
        '''Get the convergence epsilon (scalar).
        '''
        return self._epsilon

    @epsilon.setter  # PYCHOK setter!
    def epsilon(self, eps):
        '''Set the convergence epsilon.

           @param eps: New epsilon (scalar).

           @raise TypeError: Non-scalar B{C{eps}}.

           @raise ValueError: Out of bounds B{C{eps}}.
        '''
        self._epsilon = scalar(eps, name='epsilon')

    def finalBearingOn(self, distance, bearing):
        '''Compute the final bearing (reverse azimuth) after having
           travelled for the given distance along a geodesic given
           by an initial bearing from this point, using Vincenty's
           direct method.  See method L{destination2} for more details.

           @param distance: Distance (C{meter}).
           @param bearing: Initial bearing (compass C{degrees360}).

           @return: Final bearing (compass C{degrees360}).

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit.

           @example:

           >>> p = LatLon(-37.95103, 144.42487)
           >>> b = 306.86816
           >>> f = p.finalBearingOn(54972.271, b)  # 307.1736
        '''
        return self._direct(distance, bearing, False)

    def finalBearingTo(self, other, wrap=False):
        '''Compute the final bearing (reverse azimuth) after having
           travelled along a geodesic from this point to an other
           point, using Vincenty's inverse method.  See method
           L{distanceTo3} for more details.

           @param other: The other point (L{LatLon}).
           @keyword wrap: Wrap and unroll longitudes (C{bool}).

           @return: Final bearing (compass C{degrees360}).

           @raise TypeError: The B{C{other}} point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit and/or if this and the B{C{other}} point
                                 are near-antipodal.

           @example:

           >>> p = new LatLon(50.06632, -5.71475)
           >>> q = new LatLon(58.64402, -3.07009)
           >>> f = p.finalBearingTo(q)  # 11.2972°

           >>> p = LatLon(52.205, 0.119)
           >>> q = LatLon(48.857, 2.351)
           >>> f = p.finalBearingTo(q)  # 157.9
        '''
        return self._inverse(other, True, wrap)[2]

    def initialBearingTo(self, other, wrap=False):
        '''Compute the initial bearing (forward azimuth) to travel
           along a geodesic from this point to an other point,
           using Vincenty's inverse method.  See method
           L{distanceTo3} for more details.

           @param other: The other point (L{LatLon}).
           @keyword wrap: Wrap and unroll longitudes (C{bool}).

           @return: Initial bearing (compass C{degrees360}).

           @raise TypeError: The B{C{other}} point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit and/or if this and the B{C{other}} point
                                 are near-antipodal.

           @example:

           >>> p = LatLon(50.06632, -5.71475)
           >>> q = LatLon(58.64402, -3.07009)
           >>> b = p.initialBearingTo(q)  # 9.141877°

           >>> p = LatLon(52.205, 0.119)
           >>> q = LatLon(48.857, 2.351)
           >>> b = p.initialBearingTo(q)  # 156.11064°

           @JSname: I{bearingTo}.
        '''
        return self._inverse(other, True, wrap)[1]

    @property
    def iterations(self):
        '''Get the iteration limit (C{int}).
        '''
        return self._iterations

    @iterations.setter  # PYCHOK setter!
    def iterations(self, limit):
        '''Set the iteration limit.

           @param limit: New iteration limit (scalar).

           @raise TypeError: Non-scalar B{C{limit}}.

           @raise ValueError: Out-of-bounds B{C{limit}}.
        '''
        self._iterations = scalar(limit, 4, 200, name='limit')

    def toCartesian(self):
        '''Convert this (geodetic) point to (geocentric) x/y/z
           Cartesian coordinates.

           @return: Ellipsoidal (geocentric) Cartesian point (L{Cartesian}).
        '''
        x, y, z = self.to3xyz()  # ellipsoidalBase.LatLonEllipsoidalBase
        return Cartesian(x, y, z)  # this ellipsoidalVincenty.Cartesian

    def _direct(self, distance, bearing, llr, height=None):
        '''(INTERNAL) Direct Vincenty method.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit.
        '''
        E = self.ellipsoid()

        c1, s1, t1 = _r3(self.lat, E.f)

        i = radians(bearing)  # initial bearing (forward azimuth)
        si, ci = sincos2(i)
        s12 = atan2(t1, ci) * 2

        sa = c1 * si
        c2a = 1 - sa**2
        if c2a < EPS:
            c2a = 0
            A, B = 1, 0
        else:  # e22 == (a / b)**2 - 1
            A, B = _p2(c2a * E.e22)

        s = d = distance / (E.b * A)
        for _ in range(self._iterations):
            ss, cs = sincos2(s)
            c2sm = cos(s12 + s)
            s_, s = s, d + _ds(B, cs, ss, c2sm)
            if abs(s - s_) < self._epsilon:
                break
        else:
            raise VincentyError('no convergence %r' % (self,))

        t = s1 * ss - c1 * cs * ci
        # final bearing (reverse azimuth +/- 180)
        r = degrees360(atan2(sa, -t))
        if llr:
            # destination latitude in [-90, 90)
            a = degrees90(atan2(s1 * cs + c1 * ss * ci,
                                (1 - E.f) * hypot(sa, t)))
            # destination longitude in [-180, 180)
            b = degrees180(atan2(ss * si, c1 * cs - s1 * ss * ci) -
                          _dl(E.f, c2a, sa, s, cs, ss, c2sm) +
                           radians(self.lon))
            h = self.height if height is None else height
            r = self.classof(a, b, height=h, datum=self.datum), r
        return r

    def _inverse(self, other, azis, wrap):
        '''(INTERNAL) Inverse Vincenty method.

           @raise TypeError: The other point is not L{LatLon}.

           @raise ValueError: If this and the B{C{other}} point's L{Datum}
                              ellipsoids are not compatible.

           @raise VincentyError: Vincenty fails to converge for the current
                                 L{LatLon.epsilon} and L{LatLon.iterations}
                                 limit and/or if this and the B{C{other}} point
                                 are near-antipodal or coincide.
        '''
        E = self.ellipsoids(other)

        c1, s1, _ = _r3(self.lat, E.f)
        c2, s2, _ = _r3(other.lat, E.f)

        c1c2, s1c2 = c1 * c2, s1 * c2
        c1s2, s1s2 = c1 * s2, s1 * s2

        dl, _ = unroll180(self.lon, other.lon, wrap=wrap)
        ll = dl = radians(dl)
        for _ in range(self._iterations):
            ll_ = ll
            sll, cll = sincos2(ll)

            ss = hypot(c2 * sll, c1s2 - s1c2 * cll)
            if ss < EPS:  # coincident, ...
                d = 0.0  # like Karney, ...
                if azis:  # return zeros
                    d = d, 0, 0
                return d

            cs = s1s2 + c1c2 * cll
            s = atan2(ss, cs)

            sa = c1c2 * sll / ss
            c2a = 1 - sa**2
            if abs(c2a) < EPS:
                c2a = 0  # equatorial line
                ll = dl + E.f * sa * s
            else:
                c2sm = cs - 2 * s1s2 / c2a
                ll = dl + _dl(E.f, c2a, sa, s, cs, ss, c2sm)

            if abs(ll - ll_) < self._epsilon:
                break
            # <https://GitHub.com/ChrisVeness/geodesy/blob/master/latlon-vincenty.js>
            # omitted and applied only after failure to converge, see footnote under
            # Inverse at <https://WikiPedia.org/wiki/Vincenty's_formulae>
#           elif abs(ll) > PI and self.isantipodeTo(other, eps=self._epsilon):
#              raise VincentyError('%r antipodal to %r' % (self, other))
        else:
            t = 'antipodal ' if self.isantipodeTo(other, eps=self._epsilon) else ''
            raise VincentyError('no convergence, %r %sto %r' % (self, t, other))

        if c2a:  # e22 == (a / b)**2 - 1
            A, B = _p2(c2a * E.e22)
            s = A * (s - _ds(B, cs, ss, c2sm))

        b = E.b
#       if self.height or other.height:
#           b += self._havg(other)
        d = b * s

        if azis:  # forward and reverse azimuth
            sll, cll = sincos2(ll)
            f = degrees360(atan2(c2 * sll,  c1s2 - s1c2 * cll))
            r = degrees360(atan2(c1 * sll, -s1c2 + c1s2 * cll))
            d = d, f, r
        return d


def _dl(f, c2a, sa, s, cs, ss, c2sm):
    '''(INTERNAL) Dl.
    '''
    C = f / 16.0 * c2a * (4 + f * (4 - 3 * c2a))
    return (1 - C) * f * sa * (s + C * ss * (c2sm +
                     C * cs * (2 * c2sm**2 - 1)))


def _ds(B, cs, ss, c2sm):
    '''(INTERNAL) Ds.
    '''
    c2sm2 = 2 * c2sm**2 - 1
    ss2 = (4 * ss**2 - 3) * (2 * c2sm2 - 1)
    return B * ss * (c2sm + B / 4.0 * (c2sm2 * cs -
                            B / 6.0 *  c2sm  * ss2))


def _p2(u2):  # e'2 WGS84 = 0.00673949674227643
    '''(INTERNAL) Compute A, B polynomials.
    '''
    A = fpolynomial(u2, 16384, 4096, -768, 320, -175) / 16384
    B = fpolynomial(u2,     0,  256, -128,  74,  -47) / 1024
    return A, B


def _r3(a, f):
    '''(INTERNAL) Reduced cos, sin, tan.
    '''
    t = (1 - f) * tan(radians(a))
    c = 1 / hypot(1, t)
    s = t * c
    return c, s, t


class Cartesian(CartesianBase):
    '''Extended to convert (geocentric) L{Cartesian} points to
       Vincenty-based (ellipsoidal) geodetic L{LatLon}.
    '''

    def toLatLon(self, datum=Datums.WGS84, LatLon=LatLon):  # PYCHOK XXX
        '''Convert this (geocentric) Cartesian (x/y/z) point to
           an (ellipsoidal) geodetic point on the specified datum.

           @keyword datum: Optional datum to use (L{Datum}).
           @keyword LatLon: Optional ellipsoidal (sub-)class to return
                            the point (L{LatLon}) or C{None}.

           @return: The ellipsoidal geodetic point (B{C{LatLon}}) or
                    a L{LatLon3Tuple}C{(lat, lon, height)} if
                    B{C{LatLon}} is C{None}.
        '''
        return CartesianBase._to3LLh(self, datum, LatLon)


def areaOf(points, datum=Datums.WGS84, wrap=True):
    '''DEPRECATED, use function C{ellipsoidalKarney.areaOf}.
    '''
    from ellipsoidalKarney import areaOf
    return areaOf(points, datum=datum, wrap=wrap)


def perimeterOf(points, closed=False, datum=Datums.WGS84, wrap=True):
    '''DEPRECATED, use function C{ellipsoidalKarney.perimeterOf}.
    '''
    from ellipsoidalKarney import perimeterOf
    return perimeterOf(points, closed=closed, datum=datum, wrap=wrap)

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
