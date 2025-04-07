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
    V = 1*(1/1350), 
    Rho = 1350, 
    Cp = 1.364, 
    description = "Viscozyme is a commercial solution that has pectinase activity"
    )

# Structural_Protein
DB.insert_data_into_db(
    ID="Structural_Protein", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350), 
    Rho = 1350, 
    Cp = 1.364, 
    description = "Protein embedded into the cell wall matrix"
    )

# Trypsin 
DB.insert_data_into_db(
    ID = "Trypsin", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350), 
    Rho = 1350, 
    Cp = 1.364, 
    description = "Enzyme that hydrolyses proteins"
    )

# Non_Protein
DB.insert_data_into_db(
    ID = "Non_Protein", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1100), 
    Rho = 1100, 
    Cp = 1.364, 
    description = "Non-proteic fraction of tomato seeds"
    )

# Phenolic_Compounds
DB.insert_data_into_db(
    ID = "Phenolic_Compounds", 
    CAS = "502-65-8", 
    formula = "C40H56", 
    MW = 536.9, 
    description = "Phenolic_Compounds embedded into the Tomato Peel using Lycopene as reference"
    )

# Cutin
DB.insert_data_into_db(
    ID = "Cutin", 
    MW = 1, 
    CAS = "54990-88-4"
    )

# Cholinium Hexanoate
DB.insert_data_into_db(
    ID = 'Cholinium_Hexanoate',
    formula = 'C11H25NO3',
    MW = 104.17 + 115.15,
    Rho = 1010,
    Cp = 2.05,
)