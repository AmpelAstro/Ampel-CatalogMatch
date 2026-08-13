# Copyright (c) 2011-2026, Astropy Developers
# SPDX-License-Identifier: BSD-3-Clause

import math


# adapted from astropy.coordinates.angular_separation
def angular_separation(lon1, lat1, lon2, lat2):
    """
    Angular separation between two points on a sphere.

    Parameters
    ----------
    lon1, lat1, lon2, lat2 : `~astropy.coordinates.Angle`, `~astropy.units.Quantity` or float
        Longitude and latitude of the two points. Quantities should be in
        angular units; floats in radians.

    Returns
    -------
    angular separation : `~astropy.units.Quantity` ['angle'] or float
        Type depends on input; ``Quantity`` in angular units, or float in
        radians.

    Notes
    -----
    The angular separation is calculated using the Vincenty formula [1]_,
    which is slightly more complex and computationally expensive than
    some alternatives, but is stable at at all distances, including the
    poles and antipodes.

    .. [1] https://en.wikipedia.org/wiki/Great-circle_distance
    """
    sdlon = math.sin(lon2 - lon1)
    cdlon = math.cos(lon2 - lon1)
    slat1 = math.sin(lat1)
    slat2 = math.sin(lat2)
    clat1 = math.cos(lat1)
    clat2 = math.cos(lat2)

    num1 = clat2 * sdlon
    num2 = clat1 * slat2 - slat1 * clat2 * cdlon
    denominator = slat1 * slat2 + clat1 * clat2 * cdlon

    return math.atan2(math.hypot(num1, num2), denominator)
