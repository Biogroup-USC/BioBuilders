"""
"""
from .chem_db import ChemDataBase
import biosteam as bst

__all__=('ChemManager',)

class ChemManager:

    def __init__(self, chemlist: list = None):
        """
        _______________________________________________________

        This class creates a Chemical Manager that facilitates 
        the creation of chemicals and setting the thermodynamic
        properties.

        _______________________________________________________

        ARGUMENTS:
            chemlist (list):
                This list must contain the chemicals of the whole
                system.
        """
        self.chems = chemlist if chemlist is not None else []
    
    def get_chem_list(self):
        """
        
        This method is used to get the list of chemicals inside the
        object ChemManager.

        """
        return self.chems
    
    def creating_chems(self, properties: dict = None, checks = False):                          #TODO add the function to copy properties from a certain chemical
        """                                                                     
        This method allows creating any chemical disregarding wether or
        not it is yet defined in ChEDL database or it is not. The properties
        defined inside the dictionary should follow the BioSteam rules in 
        terms of name.
        _____________________________________________________________

        PROPERTIES:
        
        The properties dictionary must contain the next structure:
        {"Chem":{"Prop_name": "Value"}}

            cache (bool): use or not cached chemicals and cache new chemicals.   

            eos: equation of state for solving thermodynamics. Default
            to Peng-Robinson.

            phase (str): phase of the chemical ('s','l','g').

            phase_ref (str): Reference phase of chemical ('s','l','g').

            Psat (float): Vapor pressure model [N/m] as function of temperature [K].

            Hvap (float): Heat of vaporisation model [J/mol] as a function of 
            temperature [K].

            Cp (float): Constant heat capacity [J/g].

            rho (float): Constant density model [kg/m3].

            default (bool): Do you want to assign the missing properties to the ones of
            water (Weight basis)? Then True.

            formula (str): Formula of the chemical.

            MW: Molecular weight of the chemical (g/mol).
        
        Note that there is more properties in BioSteam than the previous. However,
        the properties mentioned before are basically the most used for modelling
        the different units inside MultiModelling.
        """
        # Create an empty Chemicals object (BioSteam) to append all the chemicals as Chemical objects (BioSteam)
        chemicals = bst.Chemicals([])

        #Create a dictionary to transformate the keys avoiding errors
        Transformed_Keys = {
            'Rho': 'rho','Default': 'default','Phase_ref': 'phase_ref','Phase_Ref': 'phase_ref',
            'Cache': 'cache','Formula': 'formula','Phase': 'phase','MW_g_per_mol': 'MW',
            'Cp_J_per_g_K': 'Cp','Rho_kg_per_m3': 'rho', 'Hvap_J_per_mol': 'Hvap','V_m3_per_mol': 'V',
            'Hf_J_per_mol': 'Hf',
        }

        # Download the Multimodelling database into %AppData%
        DB = ChemDataBase().copy_multimodelling_db()
        
        for chem in self.chems:
            try:
                Chemical = bst.Chemical(
                        ID = chem,
                        search_db = True,
                        cache = False
                    )
                
            except LookupError:
                # Clean the chemical cache avoiding Assertion errors
                bst.Chemical.chemical_cache.pop(chem, None)

                # Create a dictionary with the compulsory arguments         
                chem_args = {
                    'ID': chem, 
                    'search_db': False, 
                    'cache': False,
                    'Hf': 0
                }                
                    
                # Check if the chemical exists in the multimodelling database, If True get the properties
                if DB.check_chemical(chem):
                    Chem_Properties = DB.get_certain_data_from_db(chem,[
                        "Rho","MW","formula","Phase","Hvap","Cp","V", "Hf"
                    ])

                    for prop, value in Chem_Properties.items():
                        key = Transformed_Keys.get(prop, prop)
                        if isinstance(value,str):
                            # Convert the numbers to float
                            try:
                                chem_args[key] = float(value)
                            except ValueError:
                                chem_args[key] = value
                        else:
                            chem_args[key] = value
                # If the chem is not in any database, get the properties from the dictionary provided
                elif properties and chem in properties:
                    # Add the properties defined in the input dictionary
                    for prop, value in properties[chem].items():
                        key = Transformed_Keys.get(prop, prop)
                        chem_args[key] = value
                else:
                    # if the chemical is not in the ChEDL database, BioSTEAM database, multimodelling database and 
                    # its properties are not defined, it gives back an error
                    raise LookupError("The chemical {} properties must be provided".format(chem))
                    
                # Create the chemical using the chem_args
                Chemical = bst.Chemical(**chem_args)
            
            # Add the chemical       
            chemicals.append(Chemical)                         

        #Compile all defined chemicals
        chemicals.compile(skip_checks=checks)

        # Return the Chemicals object from BioSteam
        return chemicals
    
    def initialize_chemicals(self, chemicalsobj, checks = False):
        """
        This method is used to initialize the thermo properties of the 
        chemicals.
        _________________________________________________________________

        chemicalsobj: This argument correponds to the Chemicals object of BioSteam, obtained
        from the creating_chems method. When the chemicals of the system are 
        provided, this method initialize the thermodynamic property package.

        """
        mixture = bst.IdealMixture.from_chemicals(chemicalsobj)                     #TODO add the feature to use diferent models of mixtures
        mixture.show()
        bst.settings.set_thermo(chemicalsobj,mixture=mixture,skip_checks=checks)
        bst.settings.thermo.show()