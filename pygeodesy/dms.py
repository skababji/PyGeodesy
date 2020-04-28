
# -*- coding: utf-8 -*-

u'''Functions to parse and format bearing, compass, lat- and longitudes
in various forms of degrees, minutes and seconds.

After I{(C) Chris Veness 2011-2015} published under the same MIT Licence**, see
U{Latitude/Longitude<https://www.Movable-Type.co.UK/scripts/latlong.html>} and
U{Vector-based geodesy<https://www.Movable-Type.co.UK/scripts/latlong-vectors.html>}.

@newfield example: Example, Examples
'''

from pygeodesy.basics import InvalidError, isstr, map2, \
                             RangeError, rangerrors
from pygeodesy.lazily import _ALL_LAZY
from pygeodesy.named import LatLon2Tuple, LatLon3Tuple
from pygeodesy.streprs import fstr, fstrzs

from math import copysign, modf, radians
try:
    from string import letters as _LETTERS
except ImportError:  # Python 3+
    from string import ascii_letters as _LETTERS

# all public contants, classes and functions
__all__ = _ALL_LAZY.dms
__version__ = '20.04.27'

F_D   = 'd'    #: Format degrees as unsigned "deg°" plus suffix (C{str}).
F_DM  = 'dm'   #: Format degrees as unsigned "deg°min′" plus suffix (C{str}).
F_DMS = 'dms'  #: Format degrees as unsigned "deg°min′sec″" plus suffix (C{str}).
F_DEG = 'deg'  #: Format degrees as unsigned "[D]DD" plus suffix without symbol (C{str}).
F_MIN = 'min'  #: Format degrees as unsigned "[D]DDMM" plus suffix without symbols (C{str}).
F_SEC = 'sec'  #: Format degrees as unsigned "[D]DDMMSS" plus suffix without symbols (C{str}).
F__E  = 'e'    #: Format degrees as unsigned "%E" plus suffix without symbol (C{str}).
F__F  = 'f'    #: Format degrees as unsigned "%F" plus suffix without symbol (C{str}).
F__G  = 'g'    #: Format degrees as unsigned "%G" plus suffix without symbol (C{str}).
F_RAD = 'rad'  #: Convert degrees to radians and format as unsigned "RR" plus suffix (C{str}).

F_D_   = '-d'    #: Format degrees as signed "-/deg°" without suffix (C{str}).
F_DM_  = '-dm'   #: Format degrees as signed "-/deg°min′" without suffix (C{str}).
F_DMS_ = '-dms'  #: Format degrees as signed "-/deg°min′sec″" without suffix (C{str}).
F_DEG_ = '-deg'  #: Format degrees as signed "-/[D]DD" without suffix and symbol (C{str}).
F_MIN_ = '-min'  #: Format degrees as signed "-/[D]DDMM" without suffix and symbols (C{str}).
F_SEC_ = '-sec'  #: Format degrees as signed "-/[D]DDMMSS" without suffix and symbols (C{str}).
F__E_  = '-e'    #: Format degrees as signed "-%E" without suffix and symbol (C{str}).
F__F_  = '-f'    #: Format degrees as signed "-%F" without suffix and symbol (C{str}).
F__G_  = '-g'    #: Format degrees as signed "-%G" without suffix and symbol (C{str}).
F_RAD_ = '-rad'  #: Convert degrees to radians and format as signed "-/RR" without suffix (C{str}).

F_D__   = '+d'    #: Format degrees as signed "-/+deg°" without suffix (C{str}).
F_DM__  = '+dm'   #: Format degrees as signed "-/+deg°min′" without suffix (C{str}).
F_DMS__ = '+dms'  #: Format degrees as signed "-/+deg°min′sec″" without suffix (C{str}).
F_DEG__ = '+deg'  #: Format degrees as signed "-/+[D]DD" without suffix and symbol (C{str}).
F_MIN__ = '+min'  #: Format degrees as signed "-/+[D]DDMM" without suffix and symbols (C{str}).
F_SEC__ = '+sec'  #: Format degrees as signed "-/+[D]DDMMSS" without suffix and symbols (C{str}).
F__E__  = '+e'    #: Format degrees as signed "-/+%E" without suffix and symbol (C{str}).
F__F__  = '+f'    #: Format degrees as signed "-/+%F" without suffix and symbol (C{str}).
F__G__  = '+g'    #: Format degrees as signed "-/+%G" without suffix and symbol (C{str}).
F_RAD__ = '+rad'  #: Convert degrees to radians and format as signed "-/+RR" without suffix (C{str}).

S_DEG = '°'  #: Degrees "°" symbol (C{str}).
S_MIN = '′'  #: Minutes "′" symbol (C{str}).
S_SEC = '″'  #: Seconds "″" symbol (C{str}).
S_RAD = ''   #: Radians symbol "" (C{str}).
S_SEP = ''   #: Separator between deg, min and sec "" (C{str}).
S_NUL = ''   #: Empty string

_F_case = {F_D:   F_D,  F_DEG: F_D,  'degrees': F_D,
           F_DM:  F_DM, F_MIN: F_DM, 'deg+min': F_DM,
           F__E:  F__E, F__F:  F__F,  F__G:     F__G,
           F_RAD: F_RAD,             'radians': F_RAD}

_F_prec = {F_D:   6, F_DM:  4, F_DMS: 2,  #: (INTERNAL) default precs.
           F_DEG: 6, F_MIN: 4, F_SEC: 2,
           F__E:  8, F__F:  8, F__G:  8, F_RAD: 5}

_F_symb = {F_DEG, F_MIN, F_SEC, F__E, F__F, F__G}  # set({}) pychok -Tb

_S_norm = {'^': S_DEG, '˚': S_DEG,  #: (INTERNAL) normalized DMS.
           "'": S_MIN, '’': S_MIN, '′': S_MIN,
           '"': S_SEC, '″': S_SEC, '”': S_SEC}
_S_ALL  = (S_DEG, S_MIN, S_SEC) + tuple(_S_norm.keys())  #: (INTERNAL) alternates.

_EW   = 'EW'  # common cardinals
_NS   = 'NS'
_SW   = 'SW'  # negative ones
_NSEW = _NS + _EW


class ParseError(ValueError):
    '''Degrees, radians or other parsing issue.
    '''
    pass


def _0wpF(*w_p_f):
    '''(INTERNAL) Float deg, min, sec formatter'.
    '''
    return '%0*.*F' % w_p_f


def _toDMS(deg, form, prec, sep, ddd, suff):  # MCCABE 15 by .units.py
    '''(INTERNAL) Convert degrees to C{str}, with/-out sign and/or suffix.
    '''
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        raise InvalidError(deg=deg)

    form = form.lower()
    sign = form[:1]
    if sign in '-+':
        form = form[1:]
    else:
        sign = S_NUL

    if prec is None:
        z = p = _F_prec.get(form, 6)
    else:
        z = int(prec)
        p = abs(z)
    w = p + (1 if p else 0)
    d = abs(deg)

    if form in _F_symb:
        s_deg = s_min = s_sec = S_NUL  # no symbols
    else:
        s_deg, s_min, s_sec = S_DEG, S_MIN, S_SEC

    F = _F_case.get(form, F_DMS)
    if F is F_DMS:  # 'deg+min+sec'
        d, s = divmod(round(d * 3600, p), 3600)
        m, s = divmod(s, 60)
        t = ''.join((_0wpF(ddd, 0, d), s_deg, sep,
                     _0wpF(  2, 0, m), s_min, sep,
                     _0wpF(w+2, p, s)))
        s = s_sec

    elif F is F_DM:  # 'deg+min'
        d, m = divmod(round(d * 60, p), 60)
        t = ''.join((_0wpF(ddd, 0, d), s_deg, sep,
                     _0wpF(w+2, p, m)))
        s = s_min

    elif F is F_D:  # 'deg'
        t = _0wpF(ddd+w, p, d)
        s = s_deg

    elif F is F_RAD:
        t = '%.*F' % (p, radians(d))
        s = S_RAD

    else:  # F in (F__E, F__F, F__G)
        t = ('%.*' + F) % (p, d)
        s = S_NUL

    if z > 1:
        t = fstrzs(t, ap1z=F is F__G)

    if sign:
        if deg < 0:
            t = '-' + t
        elif deg > 0 and sign == '+':
            t = '+' + t
    elif suff:  # and deg:  # zero suffix?
        s += sep + suff
    return t + s


def bearingDMS(bearing, form=F_D, prec=None, sep=S_SEP):
    '''Convert bearing to a string.

       @arg bearing: Bearing from North (compass C{degrees360}).
       @kwarg form: Optional B{C{bearing}} format (C{str} or L{F_D},
                    L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN}, L{F_SEC},
                    L{F__E}, L{F__F}, L{F__G}, L{F_RAD}, L{F_D_},
                    L{F_DM_}, L{F_DMS_}, L{F_DEG_}, L{F_MIN_},
                    L{F_SEC_}, L{F__E_}, L{F__F_}, L{F__G_}, L{F_RAD_},
                    L{F_D__}, L{F_DM__}, L{F_DMS__}, L{F_DEG__},
                    L{F_MIN__}, L{F_SEC__}, L{F__E__}, L{F__F__},
                    L{F__G__} or L{F_RAD__}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg sep: Optional separator (C{str}).

       @return: Compass degrees per the specified B{C{form}} (C{str}).

       @JSname: I{toBrng}.
    '''
    return _toDMS(bearing % 360, form, prec, sep, 1, '')


def _clipped_(angle, limit, units):
    '''(INTERNAL) Helper for C{clipDegrees} and C{clipRadians}.
    '''
    c = min(limit, max(-limit, angle))
    if c != angle and rangerrors():
        raise RangeError('%s beyond %s %s' % (fstr(angle, prec=6),
                             fstr(copysign(limit, angle), prec=3, ints=True),
                             units))
    return c


def clipDegrees(deg, limit):
    '''Clip a lat- or longitude to the given range.

       @arg deg: Unclipped lat- or longitude (C{degrees}).
       @arg limit: Valid B{C{-limit..+limit}} range (C{degrees}).

       @return: Clipped value (C{degrees}).

       @raise RangeError: If B{C{abs(deg)}} beyond B{C{limit}} and
                          L{rangerrors} set to C{True}.
    '''
    return _clipped_(deg, limit, 'degrees') if limit and limit > 0 else deg


def clipRadians(rad, limit):
    '''Clip a lat- or longitude to the given range.

       @arg rad: Unclipped lat- or longitude (C{radians}).
       @arg limit: Valid B{C{-limit..+limit}} range (C{radians}).

       @return: Clipped value (C{radians}).

       @raise RangeError: If B{C{abs(radians)}} beyond B{C{limit}} and
                          L{rangerrors} set to C{True}.
    '''
    return _clipped_(rad, limit, 'radians') if limit and limit > 0 else rad


def compassDMS(bearing, form=F_D, prec=None, sep=S_SEP):
    '''Convert bearing to a string suffixed with compass point.

       @arg bearing: Bearing from North (compass C{degrees360}).
       @kwarg form: Optional B{C{bearing}} format (C{str} or L{F_D},
                    L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN}, L{F_SEC},
                    L{F__E}, L{F__F}, L{F__G}, L{F_RAD}, L{F_D_},
                    L{F_DM_}, L{F_DMS_}, L{F_DEG_}, L{F_MIN_},
                    L{F_SEC_}, L{F__E_}, L{F__F_}, L{F__G_}, L{F_RAD_},
                    L{F_D__}, L{F_DM__}, L{F_DMS__}, L{F_DEG__},
                    L{F_MIN__}, L{F_SEC__}, L{F__E__}, L{F__F__},
                    L{F__G__} or L{F_RAD__}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg sep: Optional separator (C{str}).

       @return: Compass degrees and point in the specified form (C{str}).
    '''
    return _toDMS(bearing % 360, form, prec, sep, 1, compassPoint(bearing))


def compassPoint(bearing, prec=3):
    '''Convert bearing to a compass point.

       @arg bearing: Bearing from North (compass C{degrees360}).
       @kwarg prec: Optional precision (1 for cardinal or basic winds,
                    2 for intercardinal or ordinal or principal winds,
                    3 for secondary-intercardinal or half-winds or
                    4 for quarter-winds).

       @return: Compass point (1-, 2-, 3- or 4-letter C{str}).

       @raise ValueError: Invalid B{C{prec}}.

       @see: U{Dms.compassPoint
             <https://GitHub.com/chrisveness/geodesy/blob/master/dms.js>}
             and U{Compass rose<https://WikiPedia.org/wiki/Compass_rose>}.

       @example:

       >>> p = compassPoint(24, 1)  # 'N'
       >>> p = compassPoint(24, 2)  # 'NE'
       >>> p = compassPoint(24, 3)  # 'NNE'
       >>> p = compassPoint(24)     # 'NNE'
       >>> p = compassPoint(11, 4)  # 'NbE'
       >>> p = compassPoint(30, 4)  # 'NEbN'

       >>> p = compassPoint(11.249)  # 'N'
       >>> p = compassPoint(11.25)   # 'NNE'
       >>> p = compassPoint(-11.25)  # 'N'
       >>> p = compassPoint(348.749) # 'NNW'
    '''
    try:  # m = 2 << prec; x = 32 // m
        m, x = _MOD_X[prec]
    except KeyError:
        raise InvalidError(prec=prec)
    # not round(), i.e. half-even rounding in Python 3,
    # but round-away-from-zero as int(b + 0.5) iff b is
    # non-negative, otherwise int(b + copysign(0.5, b))
    q = int((bearing % 360) * m / 360.0 + 0.5) % m
    return _WINDS[q * x]


_MOD_X = {1: (4, 8), 2: (8, 4), 3: (16, 2), 4: (32, 1)}  #: (INTERNAL) [prec]
_WINDS = ('N', 'NbE', 'NNE', 'NEbN', 'NE', 'NEbE', 'ENE', 'EbN',
          'E', 'EbS', 'ESE', 'SEbE', 'SE', 'SEbS', 'SSE', 'SbE',
          'S', 'SbW', 'SSW', 'SWbS', _SW , 'SWbW', 'WSW', 'WbS',
          'W', 'WbN', 'WNW', 'NWbW', 'NW', 'NWbN', 'NNW', 'NbW')  #: (INTERNAL) cardinals


def degDMS(deg, prec=6, s_D=S_DEG, s_M=S_MIN, s_S=S_SEC, neg='-', pos=''):
    '''Convert degrees to a string in degrees, minutes B{I{or}} seconds.

       @arg deg: Value in degrees (C{scalar}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg s_D: Symbol for degrees (C{str}).
       @kwarg s_M: Symbol for minutes (C{str}) or C{""}.
       @kwarg s_S: Symbol for seconds (C{str}) or C{""}.
       @kwarg neg: Optional sign for negative (C{'-'}).
       @kwarg pos: Optional sign for positive (C{''}).

       @return: I{Either} degrees, minutes B{I{or}} seconds (C{str}).
    '''
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        raise InvalidError(deg=deg)

    d, s = abs(deg), s_D
    if d < 1:
        if s_M:
            d *= 60
            if d < 1 and s_S:
                d *= 60
                s = s_S
            else:
                s = s_M
        elif s_S:
            d *= 3600
            s = s_S

    n = neg if deg < 0 else pos
    z = int(prec)
    t = '%s%.*F' % (n, abs(z),d)
    if z > 1:
        t = fstrzs(t)
    return t + s


def latDMS(deg, form=F_DMS, prec=2, sep=S_SEP):
    '''Convert latitude to a string, optionally suffixed with N or S.

       @arg deg: Latitude to be formatted (C{degrees}).
       @kwarg form: Optional B{C{deg}} format (C{str} or L{F_D},
                    L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN}, L{F_SEC},
                    L{F__E}, L{F__F}, L{F__G}, L{F_D_}, L{F_RAD},
                    L{F_D_}, L{F_DM_}, L{F_DMS_}, L{F_DEG_}, L{F_MIN_}
                    L{F_SEC_}, L{F__E_}, L{F__F_}, L{F__G_}, L{F_RAD_},
                    L{F_D__}, L{F_DM__}, L{F_DMS__}, L{F_DEG__},
                    L{F_MIN__}, L{F_SEC__}, L{F__E__}, L{F__F__},
                    L{F__G__} or L{F_RAD__}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg sep: Optional separator (C{str}).

       @return: Degrees in the specified form (C{str}).

       @JSname: I{toLat}.
    '''
    return _toDMS(deg, form, prec, sep, 2, 'S' if deg < 0 else 'N')


def lonDMS(deg, form=F_DMS, prec=2, sep=S_SEP):
    '''Convert longitude to a string, optionally suffixed with E or W.

       @arg deg: Longitude to be formatted (C{degrees}).
       @kwarg form: Optional B{C{deg}} format (C{str} or L{F_D},
                    L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN}, L{F_SEC},
                    L{F__E}, L{F__F}, L{F__G}, L{F_RAD}, L{F_D_},
                    L{F_DM_}, L{F_DMS_}, L{F_DEG_}, L{F_MIN_},
                    L{F_SEC_}, L{F__E_}, L{F__F_}, L{F__G_}, L{F_RAD_},
                    L{F_D__}, L{F_DM__}, L{F_DMS__}, L{F_DEG__},
                    L{F_MIN__}, L{F_SEC__}, L{F__E__}, L{F__F__},
                    L{F__G__} or L{F_RAD__}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg sep: Optional separator (C{str}).

       @return: Degrees in the specified form (C{str}).

       @JSname: I{toLon}.
    '''
    return _toDMS(deg, form, prec, sep, 3, 'W' if deg < 0 else 'E')


def normDMS(strDMS, norm=''):
    '''Normalize all degree ˚, minute ' and second " symbols in a
       string to the default symbols %s, %s and %s.

       @arg strDMS: DMS (C{str}).
       @kwarg norm: Optional replacement symbol, default symbol
                    otherwise (C{str}).

       @return: Normalized DMS (C{str}).
    '''
    if norm:
        for s in _S_ALL:
            strDMS = strDMS.replace(s, norm)
        strDMS = strDMS.rstrip(norm)
    else:
        for s, S in _S_norm.items():
            strDMS = strDMS.replace(s, S)
    return strDMS


def parseDDDMMSS(strDDDMMSS, suffix=_NSEW, sep=S_SEP, clip=0):
    '''Parse a lat- or longitude represention form [D]DDMMSS in degrees.

       @arg strDDDMMSS: Degrees in any of several forms (C{str}) and
                        types (C{float}, C{int}, other).
       @kwarg suffix: Optional, valid compass points (C{str}, C{tuple}).
       @kwarg sep: Optional separator between "[D]DD", "MM" and "SS" (%r).
       @kwarg clip: Optionally, limit value to -clip..+clip (C{degrees}).

       @return: Degrees (C{float}).

       @raise ParseError: Invalid B{C{strDDDMMSS}} or B{C{clip}} or the
                          B{C{strDDDMMSS}} form is incompatible with the
                          suffixed or B{C{suffix}} compass point.

       @raise RangeError: Value of B{C{strDDDMMSS}} outside the valid
                          range and L{rangerrors} set to C{True}.

       @note: Type C{str} values "[D]DD", "[D]DDMM" and "[D]DDMMSS" for
              B{C{strDDDMMSS}} are parsed properly only if I{either}
              unsigned and suffixed with a valid, compatible, C{cardinal}
              L{compassPoint} I{or} if unsigned or signed, unsuffixed and
              with keyword argument B{C{suffix}} set to B{%r}, B{%r} or a
              compatible L{compassPoint}.

       @note: Unlike function L{parseDMS}, type C{float}, C{int} and
              other non-C{str} B{C{strDDDMMSS}} values are interpreted
              form [D]DDMMSS.  For example, C{int(1230)} is returned as
              12.5 I{and not 1230.0} degrees.  However, C{int(345)} is
              considered form "DDD" 345 I{and not "DDMM" 0345}, unless
              B{C{suffix}} specifies compass point B{%r}.

       @see: Functions L{parseDMS}, L{parseDMS2} and L{parse3llh}.
    '''
    def _DDDMMSS_(strDDDMMSS, suffix, sep, clip):
        S = suffix.upper()
        if isstr(strDDDMMSS):
            t = strDDDMMSS.strip()
            if sep:
                t = t.replace(sep, '').strip()

            s = t[:1]   # sign or digit
            P = t[-1:]  # compass point, digit or dot

            t = t.lstrip('-+').rstrip(S).strip()
            f = t.split('.')
            d = len(f[0])
            f = ''.join(f)
            if 1 < d < 8 and f.isdigit() and (
                                 (P in S and s.isdigit()) or
                            (P.isdigit() and s in '-0123456789+'  # PYCHOK indent
                                         and S in ((_NS, _EW) + _WINDS))):
                # check [D]DDMMSS form and compass point
                X = _EW if (d & 1) else _NS
                if not (P in X or (S in X and (P.isdigit() or P == '.'))):
                    t = 'DDDMMSS'[d & 1 ^ 1:d | 1], X[:1], X[1:]
                    raise ParseError('form %s applies %s-%s' % t)
                f = 0  # fraction
            else:  # try other forms
                return _DMS2deg(strDDDMMSS, S, sep, clip)

        else:  # float or int to [D]DDMMSS[.fff]
            f = float(strDDDMMSS)
            s = '-' if f < 0 else ''
            P = '0'  # anything except _SW
            f, i = modf(abs(f))
            t = '%.0f' % (i,)  # str(i) == 'i.0'
            d = len(t)
            # bump number of digits to match
            # the given, valid compass point
            if S in (_NS if (d & 1) else _EW):
                t = '0' + t
                d += 1
            #   P = S
            # elif d > 1:
            #   P = (_EW if (d & 1) else _NS)[0]

        if d < 4:  # [D]DD[.ddd]
            if f:
                t = float(t) + f
            t = t, 0, 0
        else:
            f += float(t[d-2:])
            if d < 6:  # [D]DDMM[.mmm]
                t = t[:d-2], f, 0
            else:  # [D]DDMMSS[.sss]
                t = t[:d-4], t[d-4:d-2], f
        d = _dms2deg(s, P, *map2(float, t))

        return clipDegrees(d, float(clip)) if clip else d

    return _parsex(_DDDMMSS_, strDDDMMSS, suffix, sep, clip,
                              strDDDMMSS=strDDDMMSS, suffix=suffix)


if __debug__:  # no __doc__ at -O and -OO
    parseDDDMMSS.__doc__  %= (S_SEP, _NS, _EW, _NS)


def _dms2deg(s, P, deg, min, sec):
    '''(INTERNAL) Helper for C{parseDDDMMSS} and C{parseDMS}.
    '''
    deg += (min + (sec / 60.0)) / 60.0
    if s == '-' or P in _SW:
        deg = -deg
    return deg


def _DMS2deg(strDMS, suffix, sep, clip):
    '''(INTERNAL) Helper for C{parseDDDMMSS} and C{parseDMS}.
    '''
    try:
        d = float(strDMS)

    except (TypeError, ValueError):
        strDMS = strDMS.strip()

        t = strDMS.lstrip('-+').rstrip(suffix.upper()).strip()
        if sep:
            t = t.replace(sep, ' ')
            for s in _S_ALL:
                t = t.replace(s, '')
        else:
            for s in _S_ALL:
                t = t.replace(s, ' ')
        t =  map2(float, t.strip().split()) + (0, 0)
        d = _dms2deg(strDMS[:1], strDMS[-1:], *t[:3])

    return clipDegrees(d, float(clip)) if clip else d


def parseDMS(strDMS, suffix=_NSEW, sep=S_SEP, clip=0):  # MCCABE 14
    '''Parse a lat- or longitude represention in degrees.

       This is very flexible on formats, allowing signed decimal
       degrees, degrees and minutes or degrees minutes and seconds
       optionally suffixed by a cardinal compass point.

       A variety of symbols, separators and suffixes are accepted,
       for example "3°37′09″W".  Minutes and seconds may be omitted.

       @arg strDMS: Degrees in any of several forms (C{str}) and
                    types (C{float}, C{int}, other).
       @kwarg suffix: Optional, valid compass points (C{str}, C{tuple}).
       @kwarg sep: Optional separator between deg°, min′ and sec″ ("''").
       @kwarg clip: Optionally, limit value to -clip..+clip (C{degrees}).

       @return: Degrees (C{float}).

       @raise ParseError: Invalid B{C{strDMS}} or B{C{clip}}.

       @raise RangeError: Value of B{C{strDMS}} outside the valid range
                          and L{rangerrors} set to C{True}.

       @note: Inlike function L{parseDDDMMSS}, type C{float}, C{int}
              and other non-C{str} B{C{strDMS}} values are considered
              as decimal degrees.  For example, C{int(1230)} is returned
              as 1230.0 I{and not as 12.5} degrees and C{float(345)} as
              345.0 I{and not as 3.75} degrees!

       @see: Functions L{parseDDDMMSS}, L{parseDMS2} and L{parse3llh}.
    '''
    return _parsex(_DMS2deg, strDMS, suffix, sep, clip, strDMS=strDMS, suffix=suffix)


def parseDMS2(strLat, strLon, sep=S_SEP, clipLat=90, clipLon=180):
    '''Parse lat- and longitude representions in degrees.

       @arg strLat: Latitude in any of several forms (C{str} or C{degrees}).
       @arg strLon: Longitude in any of several forms (C{str} or C{degrees}).
       @kwarg sep: Optional separator between deg°, min′ and sec″ ('').
       @kwarg clipLat: Keep latitude in B{C{-clipLat..+clipLat}} range (C{degrees}).
       @kwarg clipLon: Keep longitude in B{C{-clipLon..+clipLon}} range (C{degrees}).

       @return: A L{LatLon2Tuple}C{(lat, lon)} in C{degrees}.

       @raise ParseError: Invalid B{C{strLat}} or B{C{strLon}}.

       @raise RangeError: Value of B{C{strLat}} or B{C{strLon}} outside the
                          valid range and L{rangerrors} set to C{True}.

       @note: See the B{Notes} at function L{parseDMS}.

       @see: Functions L{parseDDDMMSS}, L{parseDMS} and L{parse3llh}.
    '''
    return LatLon2Tuple(parseDMS(strLat, suffix=_NS, sep=sep, clip=clipLat),
                        parseDMS(strLon, suffix=_EW, sep=sep, clip=clipLon))


def parse3llh(strllh, height=0, sep=',', clipLat=90, clipLon=180):
    '''Parse a string representing lat-, longitude and optional height.

       The lat- and longitude value must be separated by a separator
       character.  If height is present it must follow, separated by
       another separator.

       The lat- and longitude values may be swapped, provided at least
       one ends with the proper compass point.

       @arg strllh: Latitude, longitude[, height] (C{str}, ...).
       @kwarg height: Optional, default height (C{meter}) or C{None}.
       @kwarg sep: Optional separator (C{str}).
       @kwarg clipLat: Keep latitude in B{C{-clipLat..+clipLat}} (C{degrees}).
       @kwarg clipLon: Keep longitude in B{C{-clipLon..+clipLon}} range (C{degrees}).

       @return: A L{LatLon3Tuple}C{(lat, lon, height)} in C{degrees},
                C{degrees} and C{float}.

       @raise RangeError: Lat- or longitude value of B{C{strllh}} outside
                          valid range and L{rangerrors} set to C{True}.

       @raise ValueError: Invalid B{C{strllh}} or B{C{height}}.

       @note: See the B{Notes} at function L{parseDMS}.

       @see: Functions L{parseDDDMMSS}, L{parseDMS} and L{parseDMS2}.

       @example:

       >>> parse3llh('000°00′05.31″W, 51° 28′ 40.12″ N')
       (51.4778°N, 000.0015°W, 0)
    '''
    def _3llh_(strllh, height, sep):
        ll = strllh.strip().split(sep)
        if len(ll) > 2:  # XXX interpret height unit
            h = float(ll.pop(2).strip().rstrip(_LETTERS).rstrip())
        else:
            h = height  # None from wgrs.Georef.__new__
        if len(ll) != 2:
            raise ValueError

        a, b = [_.strip() for _ in ll]  # PYCHOK false
        if a[-1:] in _EW or b[-1:] in _NS:
            a, b = b, a
        return LatLon3Tuple(parseDMS(a, suffix=_NS, clip=clipLat),
                            parseDMS(b, suffix=_EW, clip=clipLon), h)

    return _parsex(_3llh_, strllh, height, sep, strllh=strllh)


def parseRad(strRad, suffix=_NSEW, clip=0):
    '''Parse a string representing angle in radians.

       @arg strRad: Degrees in any of several forms (C{str} or C{radians}).
       @kwarg suffix: Optional, valid compass points (C{str}, C{tuple}).
       @kwarg clip: Optionally, limit value to -clip..+clip (C{radians}).

       @return: Radians (C{float}).

       @raise ParseError: Invalid B{C{strRad}} or B{C{clip}}.

       @raise RangeError: Value of B{C{strRad}} outside the valid range
                          and L{rangerrors} set to C{True}.
    '''
    def _Rad_(strRad, suffix, clip):
        try:
            r = float(strRad)

        except (TypeError, ValueError):
            strRad = strRad.strip()

            r = float(strRad.lstrip('-+').rstrip(suffix.upper()).strip())
            if strRad[:1] == '-' or strRad[-1:] in _SW:
                r = -r

        return clipRadians(r, float(clip)) if clip else r

    return _parsex(_Rad_, strRad, suffix, clip, strRad=strRad, suffix=suffix)


def _parseUTMUPS(strUTMUPS, band='', sep=','):  # see .utm.py
    '''(INTERNAL) Parse a string representing a UTM or UPS coordinate
       consisting of C{"zone[band] hemisphere/pole easting northing"}.

       @arg strUTMUPS: A UTM or UPS coordinate (C{str}).
       @kwarg band: Optional, default Band letter (C{str}).
       @kwarg sep: Optional, separator to split (",").

       @return: 5-Tuple (C{zone, hemisphere/pole, easting, northing,
                band}).

       @raise ParseError: Invalid B{C{strUTMUPS}}.
    '''
    def _UTMUPS_(strUTMUPS, band, sep):
        u = strUTMUPS.replace(sep, ' ').strip().split()
        if len(u) < 4:
            raise ValueError

        z, h = u[:2]
        if h[:1] not in 'NnSs':
            raise ValueError

        if z.isdigit():
            z, B = int(z), band
        else:
            for i in range(len(z)):
                if not z[i].isdigit():
                    # int('') raises ValueError
                    z, B = int(z[:i]), z[i:]
                    break
            else:
                raise ValueError

        e, n = map(float, u[2:4])
        return z, h.upper(), e, n, B.upper()

    return _parsex(_UTMUPS_, strUTMUPS, band, sep, strUTMUPS=strUTMUPS)


def _parsex(parser, *args, **name_value_pairs):
    '''(INTERNAL) Invoke a parser and handle exceptions.
    '''
    try:
        return parser(*args)
    except RangeError as _:
        x, E = str(_), RangeError  # avoid Python 3+ nested exception messages
    except (AttributeError, IndexError, TypeError, ValueError) as _:
        x, E = str(_), ParseError  # avoid Python 3+ nested exception messages
    raise InvalidError(Error=E, txt=x, **name_value_pairs)


def precision(form, prec=None):
    '''Set the default precison for a given F_ form.

       @arg form: L{F_D}, L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN},
                  L{F_SEC}, L{F__E}, L{F__F}, L{F__G} or L{F_RAD}
                  (C{str}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.

       @return: Previous precision (C{int}).

       @raise ValueError: Invalid B{C{form}} or B{C{prec}} or
                          B{C{prec}} outside valid range.
    '''
    try:
        p = _F_prec[form]
    except KeyError:
        raise InvalidError(form=form)

    if prec is not None:
        from pygeodesy.units import Precision_
        _F_prec[form] = Precision_(prec, name='prec', low=-9, high=9)

    return p


def toDMS(deg, form=F_DMS, prec=2, sep=S_SEP, ddd=2, neg='-', pos=''):
    '''Convert signed degrees to string, without suffix.

       @arg deg: Degrees to be formatted (C{degrees}).
       @kwarg form: Optional B{C{deg}} format (C{str} or L{F_D},
                    L{F_DM}, L{F_DMS}, L{F_DEG}, L{F_MIN}, L{F_SEC},
                    L{F__E}, L{F__F}, L{F__G}, L{F_RAD}, L{F_D_},
                    L{F_DM_}, L{F_DMS_}, L{F_DEG_}, L{F_MIN_},
                    L{F_SEC_}, L{F__E_}, L{F__F_}, L{F__G_}, L{F_RAD_},
                    L{F_D__}, L{F_DM__}, L{F_DMS__}, L{F_DEG__},
                    L{F_MIN__}, L{F_SEC__}, L{F__E__}, L{F__F__},
                    L{F__G__} or L{F_RAD__}).
       @kwarg prec: Optional number of decimal digits (0..9 or
                    C{None} for default).  Trailing zero decimals
                    are stripped for B{C{prec}} values of 1 and
                    above, but kept for negative B{C{prec}}.
       @kwarg sep: Optional separator (C{str}).
       @kwarg ddd: Optional number of digits for deg° (2 or 3).
       @kwarg neg: Optional sign for negative degrees ('-').
       @kwarg pos: Optional sign for positive degrees ('').

       @return: Degrees in the specified form (C{str}).
    '''
    t = _toDMS(deg, form, prec, sep, ddd, '')
    if form[:1] not in '-+':
        t = (neg if deg < 0 else (pos if deg > 0 else '')) + t
    return t

# **) MIT License
#
# Copyright (C) 2016-2020 -- mrJean1 at Gmail -- All Rights Reserved.
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
