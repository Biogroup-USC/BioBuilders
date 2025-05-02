"""

This script is used to create the database and add elements to it. This database will be used to
create new chemicals.

"""
from chem_db import ChemDataBase

# Create the database
DB = ChemDataBase("multimodelling/chems/database/MultiModelling_Chem.db")
DB.create_table_chemical_properties()

# Viscozyme
DB.insert_data_into_db(
    ID = "Viscozyme", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350),     # m3/mol 
    Rho = 1350, 
    Cp = 1.364, 
    description = "Viscozyme is a commercial solution that has pectinase activity"
    )

# Structural_Protein
DB.insert_data_into_db(
    ID="Structural_Protein", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350),     # m3/mol 
    Rho = 1350, 
    Cp = 1.364, 
    description = "Protein embedded into the cell wall matrix"
    )

# Trypsin 
DB.insert_data_into_db(
    ID = "Trypsin", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350),     # m3/mol       
    Rho = 1350, 
    Cp = 1.364, 
    description = "Enzyme that hydrolyses proteins"
    )

# Non_Protein
DB.insert_data_into_db(
    ID = "Non_Protein", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1100),     # m3/mol 
    Rho = 1100, 
    Cp = 1.364, 
    description = "Non-proteic fraction of tomato seeds"
    )

# Phenolic_Compounds
DB.insert_data_into_db(
    ID = "Phenolic_Compounds", 
    CAS = "502-65-8", 
    formula = "C40H56",     # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    MW = 536.9,             # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    description = "Phenolic_Compounds embedded into the Tomato Peel using Lycopene as reference",
    Phase = 's',
    V = 536.9*(1/0.899),    # m3/mol
    Rho = 0.899,            # https://doi.org/10.1155/2024/6252426 from lycopene
    Cp = 2.1                # Similar to cutin
    )

# Cutin
DB.insert_data_into_db(
    ID = "Cutin", 
    MW = 1, 
    CAS = "54990-88-4",
    Phase = 's',
    Cp = 2.1,           #J/(g*K)    https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1.364,        # kg/m3     (cellulose)
    V = 1*(1/1364),     # m3/mol 
    )

# Cholinium Hexanoate
DB.insert_data_into_db(
    ID = 'Cholinium_Hexanoate',
    formula = 'C11H25NO3',              # The sum of Choline    https://pubchem.ncbi.nlm.nih.gov/compound/choline#section=SMILES and Hexanoate https://pubchem.ncbi.nlm.nih.gov/compound/hexanoate
    MW = 104.17 + 115.15,               # The sum of both
    Rho = 1.010,                        #kg/m3       https://www.oepm.es/pdf/ES/0000/000/02/90/83/ES-2908345_T3.pdf
    Phase = 'l',
    Cp = 2.05,                          # J/(g*K)    https://doi.org/10.1016/j.jct.2022.106999 --> ethanediol + L-carnitine 3:1
    V = (104.17 + 115.15) * (1/1010)    # m3/mol
)

# Choline Chloride
DB.insert_data_into_db(
    ID = 'Choline_Chloride',
    CAS = '67-48-1',
    formula = 'C5H14NOCl',
    MW = 139.62,            # g/mol 
    Phase = 'l',
    Cp = 249/139.62,        # J/(g*K) calculated using the hypothetical heat capacity of the liquid (ChCl) obtained in https://doi.org/10.1039/D2CP00377E.
    Rho = 1.205,            # kg/m3 from https://www.chemsrc.com/en/cas/67-48-1_829430.html
    V = 139.62*(1/1205),    # m3/mol
)