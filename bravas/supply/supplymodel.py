import pulp
import biosteam as bst
from ..tea import TEA, TransportationCost  # ajusta según tu estructura de paquetes

class FlpModel:
    """
    Generalized Facility Location Problem (FLP) model with multiple sizes per plant.

    Parameters
    ----------
    suppliers : dict

    plants : dict

    customers : dict

    sizes : dict

    base_CAPEX : float

    base_OPEX : float

    op_hrs : float

    cargo_tons : float

    """

    def __init__(self, suppliers, plants, customers, sizes, base_CAPEX, base_OPEX, op_hrs, cargo_tons,
                 distance_method='geodesic', fuel_price=1.0, fuel_consumption=0.3,
                 return_factor=1.2, solver_name=None):

        self.suppliers = suppliers
        self.plants = plants
        self.customers = customers
        self.sizes = sizes  
        self.base_CAPEX = base_CAPEX
        self.base_OPEX = base_OPEX
        self.op_hrs = op_hrs
        self.cargo_tons = cargo_tons
        self.distance_method = distance_method
        self.fuel_price = fuel_price
        self.fuel_consumption = fuel_consumption
        self.return_factor = return_factor
        self.solver_name = solver_name

        self.capex_dict = {}
        self.opex_dict = {}
        self.transport_objs_h_p = {}
        self.transport_objs_p_k = {}
        self.model = None
        self.variables = {}

        # 
        self.plant_sizes = {}
        for p, info in self.plants.items():
            max_cap = info["Capacity"]
            possible_sizes = [s for s, cap in self.sizes.items() if cap <= max_cap]
            self.plant_sizes[p] = possible_sizes

        # 
        self._scale_capex_opex()

    def _scale_capex_opex(self):
        """
        """
        for p in self.plants:
            for s in self.plant_sizes[p]:
                cap_ratio = self.sizes[s] / self.sizes["S1"]  
                # 
                self.capex_dict[(p, s)] = self.base_CAPEX * cap_ratio**0.6
                # 
                self.opex_dict[(p, s)] = self.base_OPEX * cap_ratio

    def build_model(self):
        """
        """
        model = pulp.LpProblem("FLP_Optimization", pulp.LpMinimize)

        # 
        y = pulp.LpVariable.dicts("y", [(p, s) for p in self.plants for s in self.plant_sizes[p]], cat=pulp.LpBinary)
        x = pulp.LpVariable.dicts("x", [(h, p) for h in self.suppliers for p in self.plants], lowBound=0)
        f = pulp.LpVariable.dicts("f", [(p, k) for p in self.plants for k in self.customers], lowBound=0)

        # 
        transport_cost_h_p = {}
        for h in self.suppliers:
            for p in self.plants:
                t = TransportationCost(
                    origin_coords=(self.suppliers[h]["Latitude"], self.suppliers[h]["Longitude"]),
                    destiny_coords=(self.plants[p]["Latitude"], self.plants[p]["Longitude"]),
                    name_origin=h,
                    name_destiny=p,
                    distance_method=self.distance_method,
                    fuel_price=self.fuel_price,
                    fuel_consumption=self.fuel_consumption,
                    cargo_tons=self.cargo_tons,
                    return_factor=self.return_factor
                )
                self.transport_objs_h_p[(h, p)] = t
                transport_cost_h_p[(h, p)] = t.cost_per_trip()

        # 
        transport_cost_p_k = {}
        for p in self.plants:
            for k in self.customers:
                t = TransportationCost(
                    origin_coords=(self.plants[p]["Latitude"], self.plants[p]["Longitude"]),
                    destiny_coords=(self.customers[k]["Latitude"], self.customers[k]["Longitude"]),
                    name_origin=p,
                    name_destiny=k,
                    distance_method=self.distance_method,
                    fuel_price=self.fuel_price,
                    fuel_consumption=self.fuel_consumption,
                    cargo_tons=self.cargo_tons,
                    return_factor=self.return_factor
                )
                self.transport_objs_p_k[(p, k)] = t
                transport_cost_p_k[(p, k)] = t.cost_per_trip()

        # 
        transport_h_p_term = pulp.lpSum([transport_cost_h_p[(h, p)] * x[(h, p)]
                                         for h in self.suppliers for p in self.plants])
        transport_p_k_term = pulp.lpSum([transport_cost_p_k[(p, k)] * f[(p, k)]
                                         for p in self.plants for k in self.customers])
        CAPEX_term = pulp.lpSum([self.capex_dict[(p, s)] * y[(p, s)]
                                 for p in self.plants for s in self.plant_sizes[p]])
        OPEX_term = pulp.lpSum([self.opex_dict[(p, s)] * y[(p, s)]
                                for p in self.plants for s in self.plant_sizes[p]])

        # o
        model += CAPEX_term + OPEX_term + transport_h_p_term + transport_p_k_term

        # 
        # 
        for h in self.suppliers:
            model += pulp.lpSum([x[(h, p)] for p in self.plants]) == self.suppliers[h].get("Production", 0)

        # 
        for p in self.plants:
            installed_capacity = pulp.lpSum([y[(p, s)] * self.sizes[s] for s in self.plant_sizes[p]])
            model += pulp.lpSum([x[(h, p)] for h in self.suppliers]) <= installed_capacity
            model += pulp.lpSum([f[(p, k)] for k in self.customers]) <= installed_capacity

        # 
        for k in self.customers:
            model += pulp.lpSum([f[(p, k)] for p in self.plants]) == self.customers[k].get("Demand", 0)

        self.model = model
        self.variables = dict(y=y, x=x, f=f)
        return model

    def solve(self, msg=True, timeLimit=None):
        if not self.model:
            self.build_model()
        solver = pulp.PULP_CBC_CMD(msg=msg, timeLimit=timeLimit)
        self.model.solve(solver)
        return self.model.status