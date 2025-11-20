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
    V = (1/1000)*(1/1350),     # m3/mol 
    Rho = 1350,         # 1350 kg/m3 is a generic reference value for proteins  https://doi.org/10.1110/ps.04688204  
    Cp = 1.364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    Hf = -285830,       # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    description = "Viscozyme is a commercial solution that has pectinase activity"
    )

# Protein
DB.insert_data_into_db(
    ID = "Protein", 
    MW = 1, 
    Phase = 's', 
    V = 1*(1/1350),     # m3/mol 
    Rho = 1350,         # 1350 kg/m3 is a generic reference value for proteins  https://doi.org/10.1110/ps.04688204 
    Cp = 1.364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    Hf = -285830        # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2
    )

# Peptides
DB.insert_data_into_db(
    ID = "Peptides", 
    MW = 1, 
    Phase = 's', 
    V = (1/1000)*(1/1350),     # m3/mol 
    Rho = 1350,         # 1350 kg/m3 is a generic reference value for proteins  https://doi.org/10.1110/ps.04688204 
    Cp = 1.364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    Hf = -285830        # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# Structural_Protein
DB.insert_data_into_db(
    ID="Structural_Protein", 
    MW = 1, 
    Phase = 's', 
    V = (1/1000)*(1/1350),     # m3/mol 
    Rho = 1350,         # 1350 kg/m3 is a generic reference value for proteins  https://doi.org/10.1110/ps.04688204 
    Cp = 1.364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    description = "Protein embedded into the cell wall matrix",
    Hf = -285830        # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# Trypsin 
DB.insert_data_into_db(
    ID = "Trypsin", 
    MW = 1, 
    Phase = 's', 
    V = (1/1000)*(1/1350),     # m3/mol       
    Rho = 1350,         # 1350 kg/m3 is a generic reference value for proteins  https://doi.org/10.1110/ps.04688204 
    Cp = 1.364,         # kJ/(kg*K) same as cellulose 
    description = "Enzyme that hydrolyses proteins",
    Hf = -285830        # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# Non_Protein
DB.insert_data_into_db(
    ID = "Non_Protein", 
    MW = 1, 
    Phase = 's', 
    V = (1/1000)*(1/1100),     # m3/mol 
    Rho = 1100,         # 1100 kg/m3 is an aproximate value for tomato seeds    https://doi.org/10.1006/jaer.1993.1016 
    Cp = 1.364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6 
    description = "Non-proteic fraction of tomato seeds",
    Hf = -285830        # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# Phenolic_Compounds
DB.insert_data_into_db(
    ID = "Phenolic_Compounds", 
    CAS = "502-65-8", 
    formula = "C40H56",     # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    MW = 536.9,             # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    description = "Phenolic_Compounds embedded into the Tomato Peel using Lycopene as reference",
    Phase = 's',
    V = (536.9/1000)*(1/899),    # m3/mol
    Rho = 899,              # https://doi.org/10.1155/2024/6252426 from lycopene
    Cp = 2.1,               # Similar to cutin
    Hf = -285830            # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# Free_Phenolic_Compounds
DB.insert_data_into_db(
    ID = "Free_Phenolic_Compounds", 
    formula = "C40H56",     # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    MW = 536.9,             # https://pubchem.ncbi.nlm.nih.gov/compound/lycopene
    description = "Phenolic compounds extracted",
    Phase = 's',
    V = (536.9/1000)*(1/899),    # m3/mol
    Rho = 899,              # https://doi.org/10.1155/2024/6252426 from lycopene
    Cp = 2.1,               # Similar to cutin
    Hf = -285830            # J/mol Water from https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=2 
    )

# n-hentriacontane
DB.insert_data_into_db(
    ID = "Hentriacontane",
    CAS = "630-04-6",       #               https://webbook.nist.gov/cgi/cbook.cgi?ID=C630046&Mask=200
    MW = 436.84,            # g/mol         https://webbook.nist.gov/cgi/cbook.cgi?ID=C630046&Mask=200
    formula = "C31H64",     #               https://webbook.nist.gov/cgi/cbook.cgi?ID=C630046&Mask=200
    Phase = 's',
    Rho = 781.0,            # kg/m3
    Cp = 2.088,             # kJ/(kg*k)     https://webbook.nist.gov/cgi/cbook.cgi?ID=C630046&Mask=2#Thermo-Condensed                                            
    description = "Hentriacontane is used to represent all the n-alkanes present in the wax of the peel"
)

# Amyrin
DB.insert_data_into_db(
    ID = "Alpha_Amyrin",    #               https://webbook.nist.gov/cgi/cbook.cgi?ID=638-95-9
    MW = 426.72,            # g/mol         https://webbook.nist.gov/cgi/cbook.cgi?ID=638-95-9
    CAS = "638-95-9",       #               https://webbook.nist.gov/cgi/cbook.cgi?ID=638-95-9
    Phase = 's',             
    Cp = 2.088,             # kJ/(kg*k)     same as hentriacontane
    Rho = 781.0,            # kg/m3         same as hentriacontane
    description = "Alpha-amyrin is used to represent the diferent amyrins present in the wax of the peel"
)

# Pectin
DB.insert_data_into_db(
    ID = "Pectin",
    MW = 1.0,               # g/mol
    Phase = 's',             
    Cp = 2.088,             # kJ/(kg*k)     same as cellulose
    Rho = 1100.0,           # kg/m3         same as cellulose
)

# Lignin Fiber
DB.insert_data_into_db(
    ID = "Lignin_Fiber",
    MW = 1.0,               # g/mol
    Phase = 's',             
    Cp = 2.088,             # kJ/(kg*k)     same as cellulose
    Rho = 1100.0,           # kg/m3         same as cellulose
)

# Cutin
DB.insert_data_into_db(
    ID = "Cutin", 
    MW = 1, 
    CAS = "54990-88-4",
    Phase = 's',
    Cp = 2.1,           #kJ/(kg*K)          https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1364,         # kg/m3             https://link.springer.com/article/10.1007/s10853-013-7815-6
    V = (1/1000)*(1/1364),     # m3/mol 
    )

# Cutin Oligomers
DB.insert_data_into_db(
    ID = "Cutin_Olig", 
    MW = 1,
    Phase = 's',
    Cp = 2.1,           #J/(g*K)    https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    V = (1/1000)*(1/1364),     # m3/mol 
    )

DB.insert_data_into_db(
    ID = "Cutin_Olig_Sol", 
    MW = 1,
    Phase = 's',
    Cp = 2.1,           #J/(g*K)    https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    V = (1/1000)*(1/1364),     # m3/mol 
    )

DB.insert_data_into_db(
    ID = "Cutin_Olig_Insol", 
    MW = 1,
    Phase = 's',
    Cp = 2.1,           #J/(g*K)    https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    V = (1/1000)*(1/1364),     # m3/mol 
    )

# Free Cutin
DB.insert_data_into_db(
    ID = "Free_Cutin", 
    MW = 1,
    Phase = 's',
    Cp = 2.1,           #J/(g*K)    https://doi.org/10.1016/S0005-2736(01)00285-1
    Rho = 1364,         # kJ(kg*K) same as cellulose https://link.springer.com/article/10.1007/s10853-013-7815-6
    V = (1/1000)*(1/1364),     # m3/mol 
    )

# Cholinium Hexanoate
DB.insert_data_into_db(
    ID = 'Cholinium_Hexanoate',
    formula = 'C11H25NO3',              # The sum of Choline    https://pubchem.ncbi.nlm.nih.gov/compound/choline#section=SMILES and Hexanoate https://pubchem.ncbi.nlm.nih.gov/compound/hexanoate
    MW = 104.17 + 115.15,               # The sum of both
    Rho = 1010,                         #kg/m3       https://www.oepm.es/pdf/ES/0000/000/02/90/83/ES-2908345_T3.pdf
    Phase = 'l',
    Cp = 2.05,                          # J/(g*K)    https://doi.org/10.1016/j.jct.2022.106999 --> ethanediol + L-carnitine 3:1
    V = ((104.17 + 115.15)/1000) * (1/1010)    # m3/mol
)

# NADES (Choline lactate [1:2])
DB.insert_data_into_db(
    ID = 'NADES_ChCl_LA_1_2',
    MW = 319.77964,                 # Ch:LA [1:2]
    Phase = 'l',
    Rho = 1138.0,                   # kg/m3 https://pmc.ncbi.nlm.nih.gov/articles/PMC9655353/pdf/molecules-27-07429.pdf
    Cp = 4.18,
    V = ((139.62 + 2 * 90.07794)/1000)*(1/1138.0)
)