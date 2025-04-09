
import chems as cs
import biosteam as bst
import units as uts
import results as rs
import parameters as pts
import biosteam as bst

Chem_List = ["Water", "Methanol","Ethanol"]
ChMn = cs.ChemManager(Chem_List)
Chemicals = ChMn.creating_chems()
ChMn.initialize_chemicals(Chemicals)

S1 = bst.Stream(ID = 'S1', Water = 1000, units = "kg/hr")
S2 = bst.Stream(ID = 'S2')
S0 = bst.Stream(ID = 'Water', Water = 400)

R1 = bst.Reaction("Water -> Methanol", reactant = "Water", basis = "wt", X = 1)
R2 = bst.Reaction("Methanol -> Ethanol", reactant = "Methanol", basis = "wt", X = 0.5)
Rsys = bst.ReactionSystem(bst.SRxn([R1,R2]))

U1 = uts.BatchEnzymaticTreatment('U1',(S1,S0),(S2), reaction = Rsys, time = 9, loadCIPtime = 1.5)

U1.simulate()

print(U1.results())