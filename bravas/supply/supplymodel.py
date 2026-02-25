import pulp
from ..tea import TEA, TransportationCost
import biosteam as bst

class FlpModel():
    """
    Generalized Facility Location Problem (FLP) model...
    """
    def __init__(self, suppliers, plants, customers, sizes, op_hrs, supply_capacity, product_capacity, product_demand,
                    distance_method, fuel_price, fuel_consumption, cargo_tons, return_factor, solver_name=None):
            """
            """
            self.suppliers = suppliers
            self.plants = plants
            self.customers = customers
            self.sizes = sizes
            self.op_hrs = op_hrs
            self.supply_capacity = supply_capacity
            self.product_capacity = product_capacity
            self.product_demand = product_demand
            self.distance_method = distance_method
            self.fuel_price = fuel_price
            self.fuel_consumption = fuel_consumption
            self.cargo_tons = cargo_tons
            self.return_factor = return_factor
            self.solver_name = solver_name

            self.capex_dict = {}
            self.opex_dict = {}
            self.transport_objs_h_p = {}
            self.transport_objs_p_k = {}

    def _get_capex_opex(self):
        """
        """
        for p, plant_info in self.plants.items():
            units = plant_info["units"]
            op_hrs = self.op_hrs

            # Simulate a system in BioSTEAM
            system = bst.System('Plant_'+p, units)
            tea = TEA(system, operating_days = op_hrs / 24)

            # Total CAPEX and OPEX 
            total_CAPEX = tea.TCI # Total capital investment
            total_OPEX = tea._FOC(tea._FCI(tea.TDC)) # Fixed operating cost

            for s in self.sizes:
                self.capex_dict[(p,s)] = total_CAPEX
                self.opex_dict[(p,s)] = total_OPEX

    def build_model(self):
        """
        """
        if not self.capex_dict or not self.opex_dict:
            self._get_capex_opex()

        # create the model
        model = pulp.LpProblem("FLP_Optimization", pulp.LpMinimize)

        # create the variables
        # binary variable for installing the plant 'p' of size 's'
        y = pulp.LpVariable.dicts("y", 
                                  [(p,s) for p in self.plants for s in self.sizes], 
                                  cat=pulp.LpBinary) 
        
        # quantity of raw material sended from supplier 'h' to plant 'p'
        x = pulp.LpVariable.dicts("x", 
                                  [(h,p) for h in self.suppliers for p in self.plants], 
                                  lowBound=0) 
        
        # quantity of product sended from plant 'p' to customer 'k'
        f = pulp.LpVariable.dicts("f", 
                                  [(p,k) for p in self.plants for k in self.customers], 
                                  lowBound=0) 
        
        # economic terms
        # transportation cost
        transport_cost_h_p = {}
        for h in self.suppliers:
            for p in self.plants:
                t = TransportationCost(self.suppliers[h]["lat"], self.suppliers[h]["lon"], self.plants[p]["lat"], self.plants[p]["lon"],
                                       name_origin=h, name_destiny=p, distance_method=self.distance_method, fuel_price=self.fuel_price, 
                                       fuel_consumption=self.fuel_consumption, cargo_tons=self.cargo_tons, return_factor=self.return_factor)
                self.transport_objs_h_p[(h,p)] = t
                transport_cost_h_p[(h,p)] = t.cost_per_trip()

        transport_cost_p_k = {}
        for p in self.plants:
            for k in self.customers:
                t = TransportationCost(self.plants[p]["lat"], self.plants[p]["lon"], self.customers[k]["lat"], self.customers[k]["lon"],
                                       name_origin=p, name_destiny=k, distance_method=self.distance_method, fuel_price=self.fuel_price,
                                       fuel_consumption=self.fuel_consumption, cargo_tons=self.cargo_tons, return_factor=self.return_factor)
                self.transport_objs_p_k[(p,k)] = t
                transport_cost_p_k[(p,k)] = t.cost_per_trip()

        transport_h_p = pulp.lpSum([transport_cost_h_p[(h,p)] * x[(h,p)] for h in self.suppliers for p in self.plants])
        transport_p_k = pulp.lpSum([transport_cost_p_k[(p,k)] * f[(p,k)] for p in self.plants for k in self.customers])
      
        # fixed and operational cost
        CAPEX_term = pulp.lpSum([self.capex_dict[(p,s)] * y[(p,s)] for p in self.plants for s in self.sizes])
        OPEX_term = pulp.lpSum([self.opex_dict[(p,s)] * y[(p,s)] for p in self.plants for s in self.sizes])
        
        # objective function
        model += CAPEX_term + OPEX_term +  transport_h_p + transport_p_k

        # creating the constraints
        # send all 'x' suppliers 'h' capacity to plants 'p'
        for h in self.suppliers:
            model += pulp.lpSum([x[(h,p)] for p in self.plants]) == self.supply_capacity

        # do not send more 'x' suppliers 'h' capacity to plants 'p' than their 's' size
        for p in self.plants:
            installed_p_capacity = pulp.lpSum([y[(p,s)] * self.sizes[s] for s in self.sizes])
            model += pulp.lpSum([x[(h,p)] for h in self.suppliers]) <= installed_p_capacity 

        # do not send more more 'f' product from plants 'p' to custumers 'k' than the quantity that is produced
        for p in self.plants:
            model += pulp.lpSum([f[(p,k)] for k in self.customers]) <= self.product_capacity 

        # do not send more 'f' product from plants 'p' to customers 'k' than it's demand
        for k in self.customers:
             model += pulp.lpSum([f[(p,k)] for p in self.plants]) == self.product_demand
        
        self.model = model
        self.variables = dict(y=y, x=x, f=f)
        return model
    
    def solve(self, msg=True, timeLimit=None):
        if not hasattr(self, "model"):
            self.build_model
        self.model.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=timeLimit))
        return self.model.status