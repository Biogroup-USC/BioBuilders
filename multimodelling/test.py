
import chems as cs
import biosteam as bst
import units as uts
import results as rs
import parameters as pts
import tea 
import biosteam as bst
from biosteam.units.decorators import cost

Chem_List = ["Water", "Methanol","Ethanol"]
ChMn = cs.ChemManager(Chem_List)
Chemicals = ChMn.creating_chems()
ChMn.initialize_chemicals(Chemicals)

S1 = bst.Stream(ID = 'S1', Water = 0, units = "kg/hr")
S2 = bst.Stream(ID = 'S2')
S0 = bst.Stream(ID = 'Water', Water = 0, units = "kg/hr")

R1 = bst.Reaction("Water -> Methanol", reactant = "Water", basis = "wt", X = 1)

U1 = uts.BatchEnzymaticTreatment('U1',(S1,S0),(S2), reaction = R1, time = 1, loadCIPtime = 0)
U1.V_max = 67.5 # m3

mu = bst.settings.get_cooling_agent('cooling_water')
print(mu.T, mu.P)

print(S1.price)
bst.settings.stream_prices = {'S1': 40}
S1.show()
print(S1.price)

tea.Load_Process_Settings(streamsprice = {S1:50})
print(S1.price)