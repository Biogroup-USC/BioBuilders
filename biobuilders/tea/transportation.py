from geopy.distance import geodesic

class BaseDistance:
    """
    Computes and stores distance once.
    Reusable for all transport models (truck, pipeline, etc.)
    """

    def __init__(self,
                 origin_coords,
                 destiny_coords,
                 distance_method="geodesic",
                 tortuosity_factor=1.0):

        self.origin_coords = origin_coords
        self.destiny_coords = destiny_coords
        self.distance_method = distance_method
        self.tortuosity_factor = tortuosity_factor

        self.distance_km = self._compute_distance()

    def _compute_distance(self):

        if self.distance_method == "geodesic":
            return geodesic(self.origin_coords, self.destiny_coords).km * self.tortuosity_factor

        elif self.distance_method == "haversine":
            lat1, lon1 = self.origin_coords
            lat2, lon2 = self.destiny_coords
            return 2 * 6371 * (((lat2 - lat1)**2 + (lon2 - lon1)**2) ** 0.5)

        elif self.distance_method == "euclidean":
            lat1, lon1 = self.origin_coords
            lat2, lon2 = self.destiny_coords
            return ((lat1 - lat2)**2 + (lon1 - lon2)**2) ** 0.5

        else:
            raise ValueError("Invalid distance method")


    def get_distance(self):
        """
        Public access (MILP / export / reuse)
        """
        return self.distance_km

class TruckTransportationCost(BaseDistance):
    """
    MILP transport cost for biomass (€/ton)
    """

    def __init__(self,
                 origin_coords,
                 destiny_coords,
                 distance_method="geodesic",
                 cost_per_ton_km=0.05,
                 tortuosity_factor=1.0):

        super().__init__(
            origin_coords,
            destiny_coords,
            distance_method,
            tortuosity_factor
        )

        self.cost_per_ton_km = cost_per_ton_km

    def cost_per_ton(self):
        """
        €/ton transported
        """
        return self.get_distance() * self.cost_per_ton_km

class PipelineTransportationCost(BaseDistance):
    """
    MILP steam pipeline model:

    - Fixed CAPEX per km
    - Variable energy loss cost
    """

    def __init__(self,
                 origin_coords,
                 destiny_coords,
                 distance_method="geodesic",
                 capex_per_km=50000,
                 loss_cost_per_kwh_km=0.02,
                 tortuosity_factor=1.0):

        super().__init__(
            origin_coords,
            destiny_coords,
            distance_method,
            tortuosity_factor
        )

        self.capex_per_km = capex_per_km
        self.loss_cost_per_kwh_km = loss_cost_per_kwh_km

    def capex_per_connection(self):
        """
        €/connection 
        """
        return self.capex_per_km * self.get_distance()

    def opex_per_kWh_km(self):
        """
        €/kWh·km 
        """
        return self.loss_cost_per_kwh_km * self.get_distance()