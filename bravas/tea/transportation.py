"""
"""
from ..tools.mathtools import geodesic_distance, haversine_distance, euclidean_distance

class TransportationCost():
    """
    Calculates the transport cost (EUR/ton·km) for road freight based on truck characteristics, fuel consumption and distance.
    """

    def __init__(self, 
                 origin_coords,
                 destiny_coords,
                 name_origin,
                 name_destiny,
                 distance_method,
                 fuel_price,
                 fuel_consumption,
                 cargo_tons, 
                 return_factor = 1.0, 
                 tortuosity_factor = 1.0):
        """
        Initializes the object with the required parameters.

        Parameters
        ----------
        fuel_price: 
            Average gasoil/diesel price (EUR/L).

        fuel_consumption: 
            Average fuel consumption (L/km).

        cargo_tons: 
            Quantity transported (ton).

        distance_real_km: 
            Distance of the trip (km).
        
        return_factor: 
            Factor to account for empty return trips (1.0 = one way, 2.0 = return empty).

        Returns
        -------
        Numeric distance in km.
        """
        self.origin_coords = origin_coords
        self.destiny_coords = destiny_coords
        self.name_origin = name_origin
        self.name_destiny = name_destiny
        self.distance_method = distance_method

        self.fuel_price = fuel_price                
        self.fuel_consumption = fuel_consumption
        self.cargo_tons = cargo_tons
        self.return_factor = return_factor
        self.tortuosity_factor = tortuosity_factor

        self.dist_real_km = self._get_distance_value()

    def _get_distance_value(self):
        """
        Returns the numerical distance (km) depending on the selected method calculation.
        """

        if self.distance_method == 'geodesic':
            df = geodesic_distance(
                self.origin_coords,
                self.destiny_coords,
                self.name_origin,
                self.name_destiny,
                self.tortuosity_factor
            )

        elif self.distance_method == 'haversine':
            df = haversine_distance(
                self.origin_coords,
                self.destiny_coords,
                self.name_origin,
                self.name_destiny
            )
        
        elif self.distance_method == 'euclidean':
            df = euclidean_distance(
                self.origin_coords,
                self.destiny_coords,
                self.name_origin,
                self.name_destiny
            )
        
        else:
            raise ValueError(
                "distance_method must be: 'geodesic', 'haversine', or 'euclidean'"
            )
        
        return df["Distance_(km)"].iloc[0]

    def cost_per_trip(self):
        """
        Calculates total cost per ton-km for a given trip ditance.

        Returns
        -------
        Transport cost (EU/ton·km).
        """

        # Calculate the fuel cost based on distances and market price
        total_km = self.dist_real_km * self.return_factor
        total_fuel_L = total_km * self.fuel_consumption
        fuel_cost = total_fuel_L * self.fuel_price

        # calculate the transportation cost
        cost_per_km = fuel_cost / (self.cargo_tons*self.dist_real_km)
        return cost_per_km