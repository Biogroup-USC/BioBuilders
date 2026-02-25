import pulp
import biosteam as bst
from ..tea import TEA, TransportationCost  # ajusta según tu estructura de paquetes

class FlpModel:
    """
    Generalized Facility Location Problem (FLP) model.
    - suppliers, plants, customers: dict con info de lat, lon, producción/demanda
    - sizes: dict de capacidades posibles por planta {size_name: capacity}
    - cargo_tons: flujo de materia prima a transportar (puede ser cualquier stream de BioSTEAM)
    """
    def __init__(self, suppliers, plants, customers, sizes, op_hrs, cargo_tons,
                 distance_method='geodesic', fuel_price=1.0, fuel_consumption=0.3,
                 return_factor=1.2, solver_name=None):
        
        self.suppliers = suppliers
        self.plants = plants
        self.customers = customers
        self.sizes = sizes
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

    def _get_capex_opex(self):
        """Calcula CAPEX/OPEX de cada planta y tamaño usando BioSTEAM/TEA"""
        for p, plant_info in self.plants.items():
            units = plant_info.get("units", [])
            if not isinstance(units, list):
                units = [units]

            for idx, unit in enumerate(units):
                system = bst.System(f'Plant_{p}_{idx}', unit)
                tea = TEA(system, operating_days=self.op_hrs / 24)
                total_CAPEX = tea.TCI
                total_OPEX = tea._FOC(tea._FCI(tea.TDC))

                # asociamos CAPEX/OPEX a cada tamaño disponible
                for s_name, s_capacity in self.sizes.items():
                    self.capex_dict[(p, s_name)] = total_CAPEX
                    self.opex_dict[(p, s_name)] = total_OPEX

    def build_model(self):
        """Construye el modelo de optimización"""
        if not self.capex_dict or not self.opex_dict:
            self._get_capex_opex()

        model = pulp.LpProblem("FLP_Optimization", pulp.LpMinimize)

        # Variables
        y = pulp.LpVariable.dicts("y", [(p, s) for p in self.plants for s in self.sizes], cat=pulp.LpBinary)
        x = pulp.LpVariable.dicts("x", [(h, p) for h in self.suppliers for p in self.plants], lowBound=0)
        f = pulp.LpVariable.dicts("f", [(p, k) for p in self.plants for k in self.customers], lowBound=0)

        # Costes de transporte
        transport_cost_h_p = {}
        for h in self.suppliers:
            for p in self.plants:
                t = TransportationCost(
                    self.suppliers[h]["Latitude"], self.suppliers[h]["Longitude"],
                    self.plants[p]["Latitude"], self.plants[p]["Longitude"],
                    distance_method=self.distance_method,
                    fuel_price=self.fuel_price,
                    fuel_consumption=self.fuel_consumption,
                    cargo_tons=self.cargo_tons,
                    return_factor=self.return_factor
                )
                self.transport_objs_h_p[(h, p)] = t
                transport_cost_h_p[(h, p)] = t.cost_per_trip()

        transport_cost_p_k = {}
        for p in self.plants:
            for k in self.customers:
                t = TransportationCost(
                    self.plants[p]["Latitude"], self.plants[p]["Longitude"],
                    self.customers[k]["Latitude"], self.customers[k]["Longitude"],
                    distance_method=self.distance_method,
                    fuel_price=self.fuel_price,
                    fuel_consumption=self.fuel_consumption,
                    cargo_tons=self.cargo_tons,
                    return_factor=self.return_factor
                )
                self.transport_objs_p_k[(p, k)] = t
                transport_cost_p_k[(p, k)] = t.cost_per_trip()

        transport_h_p_term = pulp.lpSum([transport_cost_h_p[(h, p)] * x[(h, p)]
                                         for h in self.suppliers for p in self.plants])
        transport_p_k_term = pulp.lpSum([transport_cost_p_k[(p, k)] * f[(p, k)]
                                         for p in self.plants for k in self.customers])

        # CAPEX/OPEX
        CAPEX_term = pulp.lpSum([self.capex_dict[(p, s)] * y[(p, s)]
                                 for p in self.plants for s in self.sizes])
        OPEX_term = pulp.lpSum([self.opex_dict[(p, s)] * y[(p, s)]
                                for p in self.plants for s in self.sizes])

        # Función objetivo
        model += CAPEX_term + OPEX_term + transport_h_p_term + transport_p_k_term

        # Restricciones
        # No enviar más que la producción de proveedores
        for h in self.suppliers:
            model += pulp.lpSum([x[(h, p)] for p in self.plants]) == self.suppliers[h].get("Production", 0)

        # Capacidad de planta
        for p in self.plants:
            installed_capacity = pulp.lpSum([y[(p, s)] * self.sizes[s] for s in self.sizes])
            model += pulp.lpSum([x[(h, p)] for h in self.suppliers]) <= installed_capacity

        # No enviar más producto del que se puede producir
        for p in self.plants:
            model += pulp.lpSum([f[(p, k)] for k in self.customers]) <= installed_capacity

        # Satisfacer la demanda de clientes
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