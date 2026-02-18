"""
"""

import pandas as pd
import math
from typing import Tuple
from geopy.distance import geodesic

__all__ = (
    "geodesic_distance",
    "haversine_distance",
    "euclidean_distance",
    
)

def geodesic_distance(
        origin_coords: Tuple[float, float],
        destiny_coords: Tuple[float, float],
        name_origin: str,
        name_destiny: str,
        tortuosity_factor: float = 1.0
):
    """
    Calculates the geodesic distance (km) between two set of points and applies a tortuosity factor.

    Parameters
    ----------
    origin_coords: (lat, lon)
    destiny_coords: (lat, lon)
    name_origin: str
    name_destiny: str
    tortuosity_factor: float

    Returns
    -------
    pandas.DataFrame
    """

    # Calculate the distance in km
    dist_km = geodesic(origin_coords, destiny_coords).km
    dist_real_km = dist_km * tortuosity_factor

    # Return results as DataFrame
    return pd.DataFrame([{
        "Origin": name_origin, 
        "Destiny": name_destiny,
        "Distance_(km)": dist_real_km
    }])

def haversine_distance(
        origin_coords: Tuple[float, float],
        destiny_coords: Tuple[float, float],
        name_origin: str,
        name_destiny: str,
):
    """ 
    Calculates the havesine distance (km) between two set of points.

    Is the shortest distance between two points on a sphere (Earth) using their latitude and longitude coordinates.

    Parameters
    ----------
    origin_coords: (lat, lon)
    destiny_coords: (lat, lon)
    name_origin: str
    name_destiny: str

    Returns
    -------
    pandas.DataFrame
    """

    # Calculate the distance in km
    lat1, lon1 = origin_coords
    lat2, lon2 = destiny_coords

    R = 6371 # Earth radio in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.asin(math.sqrt(a))

    dist_real_km = R * c

    # Return results as DataFrame
    return pd.DataFrame([{
        "Origin": name_origin,
        "Destiny": name_destiny,
        "Distance_(km)": dist_real_km
    }])

def euclidean_distance(
        origin_coords: Tuple[float, float],
        destiny_coords: Tuple[float, float],
        name_origin: str,
        name_destiny: str,
):
    """
    Calculates the euclidean distance (km) between two set of points.

    Is the ordinary distance between two points in a Euclidean space, which is deduced from the Pythagorean theorem.

    Parameters
    ----------
    origin_coords: (lat, lon)
    destiny_coords: (lat, lon)
    name_origin: str
    name_destiny: str

    Return
    ------
    pandas.DataFrame
    """

    # Calculate the distance in km
    lat1, lon1 = origin_coords
    lat2, lon2 = destiny_coords

    dx = lat1 - lat2
    dy = lon1 - lon2
    dist_real_km = math.sqrt(dx**2 + dy**2)

    # Return results as DataFrame
    return pd.DataFrame([{
        "Origin": name_origin,
        "Destiny": name_destiny,
        "Distance_(km)": dist_real_km
    }])