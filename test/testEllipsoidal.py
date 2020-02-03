
# -*- coding: utf-8 -*-

# Test ellipsoidal earth model functions and methods.

__all__ = ('Tests',)
__version__ = '20.02.03'

from base import coverage, geographiclib
from testLatLon import Tests as _TestsLL
from testVectorial import Tests as _TestsV

from pygeodesy import EPS, F_D, F_D__, F_DMS, bearingDMS, compassDMS, \
                      Datums, ellipsoidalVincenty as V, \
                      fStr, m2SM, normDMS, VincentyError, wrap360


class Tests(_TestsLL, _TestsV):

    def testEllipsoidal(self, module, Cartesian, Nvector):
        # ellipsoidal modules tests

        self.subtitle(module, 'Ellipsoidal')

        LatLon = module.LatLon

        p = LatLon(51.4778, -0.0016, 0, Datums.WGS84)
        self.test('isEllipsoidal', p.isEllipsoidal, True)
        self.test('isSpherical', p.isSpherical, False)

        d = p.convertDatum(Datums.OSGB36)
        self.test('isEllipsoidal', d.isEllipsoidal, True)
        self.test('isSpherical', d.isSpherical, False)

        self.test('convertDatum', d, '51.477284°N, 000.00002°E, -45.91m')  # 51.4773°N, 000.0000°E, -45.91m
        self.test('convertDatum', d.toStr(F_D, prec=4), '51.4773°N, 000.0°E, -45.91m')
        self.test('convertDatum', p.convertDatum(p.datum), p)  # i.e. p.copy()

        if coverage:  # for test coverage
            self.test('parse', p.parse(d.toStr(F_D__)), d)
            t.reframe = None
            self.test('reframe', t.reframe, None)
            self.test('toEtm',    p.toEtm(), '30 N 916396 5720041')
            self.test('toLcc',    p.toLcc(), '5639901 4612638')
            self.test('toOsgr',   p.toOsgr(), 'TQ 38876 77320')
            self.test('toUps',    LatLon(84, 0).toUps(), '00 N 2000000 1333272')
            self.test('toUtm',    p.toUtm(), '30 N 708207 5707224')
            self.test('toUtmUps', p.toUtmUps(), '30 N 708207 5707224')
            self.test('toWm',     p.toWm(), '-178.111 6672799.209')

        if Cartesian and Nvector:
            c = Cartesian(3980581, 97, 4966825)
            n = c.toNvector()  # {x: 0.6228, y: 0.0000, z: 0.7824, h: 0.0000}  # XXX height
            self.test('toNVector', n.toStr(4), '(0.6228, 0.0, 0.7824, +0.24)')
            self.test('toNvector', isinstance(n, Nvector), True)
            c = n.toCartesian()
            self.test('toCartesian', c.toStr(0), '[3980581, 97, 4966825]')
            self.test('toCartesian', isinstance(c, Cartesian), True)

            n = Nvector(0.5, 0.5, 0.7071)
            self.test('Nvector', n, '(0.5, 0.5, 0.7071)')

            c = n.toCartesian()  # [3194434, 3194434, 4487327]
            self.test('toCartesian', c, '[3194434.411, 3194434.411, 4487326.82]')
            self.test('toCartesian', isinstance(c, Cartesian), True)

            p = c.toLatLon()  # 45.0°N, 45.0°E
            self.test('toLatLon', p.toStr('d', 2), '45.0°N, 045.0°E, +0.00m')  # 45.0°N, 45.0°E
            self.test('toLatLon', isinstance(p, LatLon), True)

            n = Nvector(0.51, 0.512, 0.7071, 1).toStr(3)
            self.test('Nvector', n, '(0.51, 0.512, 0.707, +1.00)')

        # <https://GitHub.com/DieuwerH/AE3537/blob/master/PyGeodesyTesting.py>
        s = Cartesian(3145.5036885, 5387.14337206, 3208.93193301).toLatLon()  # WGS84 XXX m, Km, other?
        self.test('sat', s, '82.545852°N, 059.719736°E, -6353121.71m' if Nvector or module is V else
                            '82.219069°N, 059.719736°E, -6353120.97m')  # XXX neg height?
        d = LatLon(51.99888889, 4.37333333, height=134.64, name='DopTrackStation')
        self.test('dop', d, '51.998889°N, 004.373333°E, +134.64m')
        self.test('distance', d.distanceTo(s), '3806542.94364687' if Nvector else
                                              ('3817991.07401530' if module is V else
                                               '3802238.50498862'), fmt='%.8f')

    def testKarney(self, module, datum):

        d = datum
        self.subtitle(module, 'Karney', datum=d.name)
        LatLon = module.LatLon

        Newport_RI = LatLon(41.49008, -71.312796, datum=d)

        Cleveland_OH = LatLon(41.499498, -81.695391, datum=d)
        m = Newport_RI.distanceTo(Cleveland_OH)
        self.test('distanceTo', m, '866455.4329', fmt='%.4f')

        m = Newport_RI.distanceTo(Newport_RI)
        self.test('coincident', m, 0.0)

        if hasattr(LatLon, 'toCartesian'):
            c = Cleveland_OH.convertDatum(Datums.OSGB36)
            self.test('convertDatum', c.datum.name, 'OSGB36')
            try:
                m = Newport_RI.distanceTo(c)
                self.test('ValueError1', None, 'other Ellipsoid mistmatch: ...' + d.ellipsoid.name)
            except ValueError as x:
                self.test('ValueError2', x, 'other Ellipsoid mistmatch: Ellipsoids.Airy1830 vs Ellipsoids.' + d.ellipsoid.name)
            except Exception as x:
                self.test('ValueError3', x, 'ValueError ...' + d.ellipsoid.name)

        p = LatLon(-37.95103342, 144.42486789, datum=d)
        self.test('isEllipsoidal', p.isEllipsoidal, True)

        q = p.copy()
        self.test('copy', q.isequalTo(p), True)
        self.test('isEllipsoidal', q.isEllipsoidal, True)
        self.test('isSpherical', q.isSpherical, False)

        self.test('copy', q.toStr(F_DMS, prec=4), '37°57′03.7203″S, 144°25′29.5244″E')

        self.testKarneyVincenty(module, LatLon, d)
        self.testKarneyVincentyError(module, LatLon, d, True)

    def testKarneyPython(self, module):

        self.subtitle(module, 'KarneyPython')

        ll1 = module.LatLon(-41.32, 174.81)
        # <https://GeographicLib.SourceForge.io/1.49/python>
        d = ll1.geodesic.Inverse(-41.32, 174.81, 40.96, -5.50)
        self.test('lat1', d['lat1'], -41.320, fmt='%.3f')
        self.test('lon1', d['lon1'], 174.810, fmt='%.3f')
        self.test('azi1', d['azi1'], 161.067669986160, fmt='%.12f')
        self.test('lat2', d['lat2'],  40.960, fmt='%.3f')
        self.test('lon2', d['lon2'],  -5.500, fmt='%.3f')
        self.test('azi2', d['azi2'],  18.825195123247, fmt='%.12f')
        self.test('s12',  d['s12'], 19959679.267353821546, fmt='%.12f', known=True)

        d3 = ll1.distanceTo3(module.LatLon(40.96, -5.50))
        self.test('distanceTo3', fStr(d3, prec=12), '19959679.267353821546, 161.06766998616, 18.825195123247', known=True)
        ll2, d2 = ll1.destination2(19959679.26735382, 161.067669986160)
        self.test('destination2', fStr((ll2.lat, ll2.lon, d2), prec=12), '40.96, -5.5, 18.825195123247')

        # <https://GeographicLib.SourceForge.io/scripts/geod-calc.html>
        LL = module.LatLon
        p = LL(-63.1,  -58), LL(-72.9,  -74), LL(-71.9, -102), \
            LL(-74.9, -102), LL(-74.3, -131), LL(-77.5, -163), \
            LL(-77.4,  163), LL(-71.7,  172), LL(-65.9,  140), \
            LL(-65.7,  113), LL(-66.6,   88), LL(-66.9,   59), \
            LL(-69.8,   25), LL(-70.0,   -4), LL(-71.0,  -14), \
            LL(-77.3,  -33), LL(-77.9,  -46), LL(-74.7,  -61)  # on/around south pole!
        self.test('areaOf', module.areaOf(p), '1.366270368e+13', fmt='%.9e')  # 1.366270368002013e+13'
        self.test('perimeterOf', module.perimeterOf(p, closed=True), '1.683106789e+07', fmt='%.9e')  # 1.683106789279071e+07
        self.test('isclockwise', module.isclockwise(p), True)  # polar

    def testVincenty(self, module, datum):

        d = datum
        self.subtitle(module, 'Vincenty', datum=d.name)
        LatLon = module.LatLon

        Newport_RI = LatLon(41.49008, -71.312796, datum=d)
        Cleveland_OH = LatLon(41.499498, -81.695391, datum=d)
        m = Newport_RI.distanceTo(Cleveland_OH)
        self.test('distanceTo', m, '866455.43292', fmt='%.5f')

        if hasattr(LatLon, 'toCartesian'):
            c = Cleveland_OH.convertDatum(Datums.OSGB36)
            self.test('convertDatum', c.datum.name, 'OSGB36')
            try:
                m = Newport_RI.distanceTo(c)
                self.test('ValueError1', None, 'other Ellipsoid mistmatch: ...' + d.ellipsoid.name)
            except ValueError as x:
                self.test('ValueError2', x, 'other Ellipsoid mistmatch: Ellipsoids.Airy1830 vs Ellipsoids.' + d.ellipsoid.name)
            except Exception as x:
                self.test('ValueError3', x, 'ValueError ...' + d.ellipsoid.name)

        p = LatLon(-37.95103342, 144.42486789, datum=d)
        self.test('isEllipsoidal', p.isEllipsoidal, True)
        self.test('isSpherical', p.isSpherical, False)

        self.test('epsilon', p.epsilon, 1e-12)
        self.test('iterations', p.iterations, 100)

        q = p.copy()
        self.test('copy', q.isequalTo(p), True)
        self.test('isEllipsoidal', q.isEllipsoidal, True)
        self.test('isSpherical', q.isSpherical, False)

        self.test('copy', q.toStr(F_DMS, prec=4), '37°57′03.7203″S, 144°25′29.5244″E')

        q.epsilon, q.iterations = EPS, 200
        self.test('epsilon', q.epsilon, EPS)
        self.test('iterations', q.iterations, 200)
        self.test('iteration', q.iteration, 0)

        self.testKarneyVincenty(module, LatLon, d)
        self.testKarneyVincentyError(module, LatLon, d, False)

    def testKarneyVincenty(self, module, LatLon, d):

        self.subtitle(module, 'KarneyVincenty', datum=d.name)

        p = LatLon(-37.95103342, 144.42486789, datum=d)
        t = p.distanceTo(p)
        self.test('coincident', t, '0.0')
        t = p.distanceTo3(p)
        self.test('coincident', fStr(t), '0.0, 0.0, 0.0')

        q = p.destination(54972.271, 306.86816)
        t = q.toStr(F_D, prec=4)
        self.test('destination', t, '37.6528°S, 143.9265°E')
        self.test('destination', isinstance(q, LatLon), True)

        q, f = p.destination2(54972.271, 306.86816)
        t = q.toStr(F_D) + ', ' + compassDMS(f, prec=4)
        self.test('destination2', t, '37.652821°S, 143.926496°E, 307.1736°NW')
        self.test('destination2', isinstance(q, LatLon), True)

        f = p.finalBearingOn(54972.271, 306.86816)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingOn', t, '307.1736°, 307°10′25.07″NW')

        # <https://GitHub.com/chrisveness/geodesy/blob/master/test/latlon-ellipsoidal-vincenty-tests.js>
        # ... Test case (UK), using WGS-84
        p = LatLon(50.06632, -5.71475, datum=d)
        q = LatLon(58.64402, -3.07009, datum=d)
        m = p.distanceTo(q)
        self.test('distanceTo', m, '969954.166', fmt='%.3f')

        t = p.distanceTo3(q)
        t = fStr(t, prec=6)
        self.test('distanceTo3', t, '969954.166314, 9.141877, 11.29722')

        t = p.distanceTo2(q)
        t = fStr(t, prec=5)
        self.test('distanceTo2', t, '972708.16174, 11.22502')

        b = p.initialBearingTo(q)
        t = bearingDMS(b, prec=4) + ', ' + compassDMS(b, form=F_DMS, prec=2)
        self.test('initialBearingTo', t, '9.1419°, 9°08′30.76″N')

        t = p.destination(m, b)
        self.test('destination', t.toStr(form=F_D, prec=5), '58.64402°N, 003.07009°W')

        f = p.finalBearingTo(q)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingTo', t, '11.2972°, 11°17′49.99″NNE')

        f = p.finalBearingOn(m, b)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingOn', t, '11.2972°, 11°17′49.99″NNE')

        p = LatLon(52.205, 0.119)
        q = LatLon(48.857, 2.351)
        m = p.distanceTo(q)
        self.test('distanceTo', m, '404607.806', fmt='%.3f')

        t = p.distanceTo3(q)
        t = fStr(t, prec=6)
        self.test('distanceTo3', t, '404607.805988, 156.11064, 157.8345')

        t = p.distanceTo2(q)
        t = fStr(t, prec=6)
        self.test('distanceTo2', t, '402574.597287, 157.726344')

        b = p.initialBearingTo(q)
        t = bearingDMS(b, prec=4) + ', ' + compassDMS(b, form=F_DMS, prec=2)
        self.test('initialBearingTo', t, '156.1106°, 156°06′38.31″SSE')

        t = p.destination(m, b)
        self.test('destination', t.toStr(form=F_D, prec=5), '48.857°N, 002.351°E')

        f = p.finalBearingTo(q)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingTo', t, '157.8345°, 157°50′04.2″SSE')  # 157.9

        f = p.finalBearingOn(m, b)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingOn', t, '157.8345°, 157°50′04.2″SSE')

        p = LatLon(37.95103, 144.42487, datum=d)
        q = LatLon(37.65280, 143.9265, datum=d)
        m = p.distanceTo(q)
        self.test('distanceTo', m, '54973.295', fmt='%.3f')

        t = p.distanceTo3(q)
        t = fStr(t, prec=5)
        self.test('distanceTo3', t, '54973.29527, 233.13008, 232.82461')

        t = p.distanceTo2(q)
        t = fStr(t, prec=5)
        self.test('distanceTo2', t, '54903.41209, 232.9209')

        b = p.initialBearingTo(q)
        t = bearingDMS(b, prec=4) + ', ' + compassDMS(b, form=F_DMS, prec=2)
        self.test('initialBearingTo', t, '233.1301°, 233°07′48.28″SW')

        t = p.destination(m, b)
        self.test('destination', t.toStr(form=F_D, prec=5), '37.6528°N, 143.9265°E')

        f = p.finalBearingTo(q)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingTo', t, '232.8246°, 232°49′28.59″SW')

        f = p.finalBearingOn(m, b)
        t = bearingDMS(f, prec=4) + ', ' + compassDMS(f, form=F_DMS, prec=2)
        self.test('finalBearingOn', t, '232.8246°, 232°49′28.59″SW')

        # <https://GitHub.com/maurycyp/vincenty> Maurycy Pietrzak
        Boston = LatLon(42.3541165, -71.0693514, datum=d)
        NewYork = LatLon(40.7791472, -73.9680804, datum=d)
        m = Boston.distanceTo(NewYork)
        self.test('distanceToMP', m, '298396.057', fmt='%.3f')
        self.test('distanceToSM', m2SM(m), 185.414, fmt='%.3f')

        p = LatLon(0, 0, datum=d)
        q = LatLon(0, 1, datum=d)
        m = p.distanceTo(q)
        self.test('distanceToMP', m, '111319.491', fmt='%.3f')

        q = LatLon(1, 0, datum=d)
        m = p.distanceTo(q)
        self.test('distanceToMP', m, '110574.389', fmt='%.3f')

        # <https://PyPI.org/project/pygc> Kyle Wilcox
        p = LatLon(0, 50, datum=d)
        q = LatLon(0, 52, datum=d)
        m = p.distanceTo(q)
        self.test('distanceToKW', m, '222638.982', fmt='%.3f')

        q = LatLon(0, 49, datum=d)
        m = p.distanceTo(q)
        self.test('distanceToKW', m, '111319.491', fmt='%.3f')

        # <https://www.Movable-Type.co.UK/scripts/latlong-vincenty.html>
        # ... Test case (from Geoscience Australia), using WGS-84
        FindersPeak = LatLon('37°57′03.72030″S', '144°25′29.52440″E')
        Buninyong = LatLon('37°39′10.15610″S', '143°55′35.38390″E')
        m, b, f = FindersPeak.distanceTo3(Buninyong)
        self.test('distanceTo3', m, '54972.271', fmt='%.3f')
        self.test('distanceTo3', bearingDMS(b, F_DMS), '306°52′05.37″')
        self.test('distanceTo3', bearingDMS(f, F_DMS), '307°10′25.07″')
        m, b = FindersPeak.distanceTo2(Buninyong)
        self.test('distanceTo2', m, '54902.390', fmt='%.3f')
        self.test('distanceTo2', bearingDMS(b, F_DMS), '307°04′38.41″')

    def testKarneyVincentyError(self, module, LatLon, d, isKarney):  # MCCABE 21

        self.subtitle(module, 'KarneyVincentyError', datum=d.name)

        def _i(name, ll):
            return '%s (%s)' % (name, ll.iteration)

        # <https://GitHub.com/chrisveness/geodesy/blob/master/test/latlon-ellipsoidal-vincenty-tests.js>
        # ... Test case (antipodal), using WGS-84
        p = LatLon(0, 0, datum=d)
        q = LatLon(0.5, 179.5, datum=d)
        try:
            m, t, fmt = p.distanceTo(q), '19936288.579', '%.3f'
        except VincentyError as x:
            m, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('distanceTo/antipodal', p), m, t, fmt=fmt, known=True)

        q = LatLon(0.5, 179.7, datum=d)
        try:
            m, t, fmt = p.distanceTo(q), '19944127.421', '%.3f'
        except VincentyError as x:
            m, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('distanceTo/VincentyError', p), m, t, fmt=fmt, known=True)
        try:
            b, t, fmt = p.initialBearingTo(q), '15.556883', '%.6f'
        except VincentyError as x:
            b, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('initialBearingTo/VincentyError', p), b, t, fmt=fmt, known=True)
        try:
            f, t, fmt = p.finalBearingTo(q), '164.442514', '%.6f'
        except VincentyError as x:
            f, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('finalBearingTo/VincentyError', p), f, t, fmt=fmt, known=True)

        q = LatLon(0, 180, datum=d)
        try:
            m, t, fmt = p.distanceTo(q), '20003931.46', '%.2f'
        except VincentyError as x:
            m, t, fmt = str(x), 'ambiguous, ...', '%s'
        self.test(_i('distanceTo/equatorial', p), m, t, fmt=fmt, known=True)
        try:
            b, t, fmt = p.initialBearingTo(q), '0.0', '%.1f'
        except VincentyError as x:
            b, t, fmt = str(x), 'ambiguous, ...', '%s'
        self.test(_i('initialBearingTo/equatorial', p), b, t, fmt=fmt, known=True)

        q = LatLon(0, 1, datum=d)
        m = p.distanceTo(q)
        self.test(_i('distanceTo/coincident', p), m, '111319.491', fmt='%.3f')  # 40075016.686 / 360

        q = LatLon(-90, 0, datum=d)
        m = p.distanceTo(q)
        self.test(_i('distanceTo/meridional', p), m, 10001965.729, fmt='%.3f')
        b = p.initialBearingTo(q)
        self.test(_i('initialBearingTo/meridional', p), b, 180.0, fmt='%.1f')

        # <https://GitHub.com/chrisveness/geodesy/blob/master/test/latlon-ellipsoidal-vincenty-tests.js>
        # ... Test case (coincident), using WGS-84
        p = LatLon(50.06632, -5.71475, datum=d)
        m = p.distanceTo(p)
        self.test(_i('distanceTo/coincident', p), m, '0.0', fmt='%.1f')
        try:
            b, t, fmt = p.initialBearingTo(p), '180.0' if isKarney else '0.0', '%.1f'
        except VincentyError as x:
            b, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('initialBearingTo/coincident', p), b, t, fmt=fmt, known=True)  # NaN
        try:
            f, t, fmt = p.finalBearingTo(p), '180.0' if isKarney else '0.0', '%.1f'
        except VincentyError as x:
            f, t, fmt = str(x), 'no convergence, ...', '%s'
        self.test(_i('finalBearingTo/coincident', p), f, t, fmt=fmt, known=True)  # NaN
        try:
            q, t = p.destination(0, 0), '50.06632°N, 005.71475°W'
        except VincentyError as x:
            q, t = str(x), 'no convergence, ...'
        self.test(_i('destination/coincident', p), q, t, known=True)

        # <https://GitHub.com/chrisveness/geodesy/blob/master/test/latlon-ellipsoidal-vincenty-tests.js>
        # ... Test case (crossing anti-meridian), using WGS-84
        p = LatLon(30,  120, datum=d)
        q = LatLon(30, -120, datum=d)
        m = p.distanceTo(q)
        self.test(_i('distanceTo/anti-meridian', p), m, '10825924.1', fmt='%.1f')

        # <https://GitHub.com/chrisveness/geodesy/blob/master/test/latlon-ellipsoidal-vincenty-tests.js>
        # ... Test case (quadrants), using WGS-84
        for t in (( 30, 30, 60, 60),
                  ( 60, 60, 30, 30),
                  ( 30, 60, 60, 30),
                  ( 60, 30, 30, 60),
                  ( 30,-30, 60,-60),
                  ( 60,-60, 30,-30),
                  ( 30,-60, 60,-30),
                  ( 60,-30, 30,-60),
                  (-30,-30,-60,-60),
                  (-60,-60,-30,-30),
                  (-30,-60,-60,-30),
                  (-60,-30,-30,-60),
                  (-30, 30,-60, 60),
                  (-60, 60,-30, 30),
                  (-30, 60,-60, 30),
                  (-60, 30,-30, 60)):
            p = LatLon(t[0], t[1], datum=d)
            q = LatLon(t[2], t[3], datum=d)
            m = p.distanceTo(q)
            self.test(_i('distanceTo/quadrants', p), m, '4015703.02', fmt='%.2f')

    def testNOAA(self, module):
        # <https://www.NGS.NOAA.gov/PC_PROD/Inv_Fwd/readme.htm>

        self.subtitle(module, 'NOAA')

        LatLon= module.LatLon

        def _dfr(d, f, r):
            r = wrap360(r + 180)  # final bearing to back azimuth
            t = d, normDMS(bearingDMS(f, form=F_DMS, prec=4), norm=' '), \
                   normDMS(bearingDMS(r, form=F_DMS, prec=4), norm=' ')
            return '%.4f, %s, %s' % t

        p = LatLon('34 00 12.12345 N', '111 00 12.12345 W', datum=Datums.WGS84)  # Jones
        q = LatLon('33 22 11.54321 N', '112 55 44.33333 W', datum=Datums.WGS84)  # Smith
        t = p.distanceTo3(q)
        self.test('NOAAexample1', _dfr(*t), '191872.1190, 249 03 16.4237, 67 59 11.1619')

        p = LatLon('45 00 12.0 N', '68 00 0.0 W', datum=Datums.NAD27)  # Charlie
        q = LatLon('44 33 0.0 N', '70 12 34.7890 W', datum=Datums.NAD27)  # Sam
        t = p.distanceTo3(q)
        self.test('NOAAexample2', _dfr(*t), '182009.1679, 254 42 44.6439, 73 09 21.3315')

        p = LatLon('34 00 00.0 N', '111 00 00.0 W', height=76)  # Bill
        q = LatLon('33 31 25.93490 N', '112 12 16.40986 W', height=54)  # George
        t = p.distanceTo3(q)
        self.test('NOAAexample3', _dfr(*t), '123456.7891, 245 00 34.7001, 64 20 24.6864')  # ... 30.70, ... 24.6862

        p = LatLon('36 34 42.89133 N', '118 17 31.18182 W', height=4395.8320)  # Mt Whitney, CA
        q = LatLon('36 01 37.0 N', '116 49 32.0 W', height=-101.8680)  # Bad Water (Death valley), CA
        t = p.distanceTo3(q)
        self.test('NOAAexample4', _dfr(*t), '145239.0603, 114 29 26.9586, 295 21 32.6566')  # Ell Dist, FAZ, BAZ


if __name__ == '__main__':

    from pygeodesy import ellipsoidalKarney as K, \
                          ellipsoidalNvector as N

    t = Tests(__file__, __version__)

    t.testEllipsoidal(N, N.Cartesian, N.Nvector)
    t.testLatLon(N, Sph=False, Nv=True)
    t.testVectorial(N)

    t.testEllipsoidal(V, V.Cartesian, None)
    t.testLatLon(V, Sph=False, Nv=False)
    t.testNOAA(V)
    for d in (Datums.WGS84, Datums.NAD83,):  # Datums.Sphere):
        t.testVincenty(V, d)

    if geographiclib:
        t.testEllipsoidal(K, K.Cartesian, None)
        t.testLatLon(K, Sph=False, Nv=False)
        t.testNOAA(K)
        for d in (Datums.WGS84, Datums.NAD83,):  # Datums.Sphere):
            t.testKarney(K, d)
        t.testKarneyPython(K)

    t.results()
    t.exit()
