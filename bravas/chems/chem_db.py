"""

This script contains all the code used to build the multimodelling chemical database
which is used to store all the chemicals from the case studies. As consequence, when a new chemical
is created it will be searched in the two databases included in BioSTEAM and in the multimodelling
database. If the chemical is not in one of them, then it must be defined.

This code also allows the user to create its own database and _build_database could be taken as a
template.

"""
import sqlite3
import pandas as pd
from datetime import datetime
import pytz
from appdirs import user_data_dir
import os
import shutil

__all__ = ("ChemDataBase",)

class ChemDataBase:          #TODO I´d like to create anoter table for chemical composition of feedstocks, probably inside the Multimodelling_Chem.db
    
    Column_Keys = {
        "MW_g_per_mol":["MW","Mol_weight"],
        "Cp_J_per_g_K":["Cp","cp"],
        "Rho_kg_per_m3":["rho","Rho","Density","density"],
        "Hvap_J_per_mol":["Hvap","hvap"],
        "V_m3_per_mol":["V", "MolarVolume","v"],
        "formula":["Formula","formula"],
        "description":["Description","description"],
        "ID":["ID"],
        "CAS":["CAS"],
        "Phase":["Phase","phase"],
        "Last_Modification": ["Last_Modification"],
        "Hf_J_per_mol":["Hf"]
    }

    def __init__(self, dbname: str = None):
        """
        
        Database for chemicals commonly used in biorefineries.

        Create a ChemDataBase object which allows the user to build a SQL database for chemical
        properties in the file path provided as the database name. This is the same code used for 
        creating the multimodelling database. 
        
        Parameters
        ----------
        dbname : str
            Name of the database. If the database already exists in your current directory
            write "mydirectory.db". However, a new database could be created by writing a 
            new name "mynewdatabase.db".
    
        """
        # The default name of the database is "MultiModelling_Chem.db"
        self.dbname = dbname if dbname is not None else "MultiModelling_Chem.db"

        # Initialize the connection property
        self._connection = None

        # Initialize the set_timezone property
        self._timezone = None

    @property
    def timezone(self):
        """

        This property defines the timezone for the time stamp.
        It could be changed following the example.

        Example
        -------
        >>> import pytz
        >>> MyDB = ChemDataBase()
        >>> MyDB.timezone = pytz.timezone('Europe/Madrid')

        """
        if self._timezone is None:
            self._timezone = pytz.timezone('Europe/Madrid')
            return self._timezone
    
    @property
    def current_timestamp(self):
        """
        
        This property uses the timezone defined and returns the
        data and time in the format used by SQL.

        """
        return datetime.now(self.timezone).isoformat(sep=' ', timespec='seconds')

    @property
    def connection(self):
        """

        The connection with the database is treated like a property ensuring
        that the same connection is used in all methods.
        
        """
        # Create the connection with database when the class is initialized 
        if self._connection is None:
            self._connection = sqlite3.connect(self.dbname)
        return self._connection
    
    @classmethod
    def copy_multimodelling_db(cls, dest_path: str = None):
        """

        This method is used to copy the Multimodelling database from the package
        installation to a destination folder.

        Parameters
        ----------
        dest_path : str, optional
            Custom path where the database should be copied. If not provided, it will be
            copied to the user data directory (%AppData%).

        Returns
        -------
        ChemDataBase
            Instance of ChemDataBase connected to the destination database.

        """
        DB_Filename = "Multimodelling_Chem.db"
        Appname = "Multimodelling_Database"
    
        # Source DB path from installed package
        Current_Directory = os.path.dirname(__file__)
        Internal_DB_Path = os.path.join(Current_Directory, "database", DB_Filename)
        if not os.path.exists(Internal_DB_Path):
            raise FileNotFoundError(f"The internal database could not be found in: {Internal_DB_Path}")
        
        # Determine destination path
        if dest_path is None:
            User_Dir = user_data_dir(Appname, appauthor=False)
            os.makedirs(User_Dir, exist_ok=True)
            Final_Destination = os.path.join(User_Dir, DB_Filename)
        else:
            Final_Destination = os.path.abspath(dest_path)
            os.makedirs(os.path.dirname(Final_Destination), exist_ok=True)
    
        # Copy if not exists
        if not os.path.exists(Final_Destination):
            shutil.copy(Internal_DB_Path, Final_Destination)
            print(f"Database copied to: {Final_Destination}")
        else:
            print(f"Database already exists at: {Final_Destination}")
    
        return cls(Final_Destination)

    @classmethod
    def delete_multimodelling_db(cls):
        """

        This method deletes the Multimodelling database previously created using
        the method called copy_multimodelling_db.

        """
        # Name of the App
        Appname = "Multimodelling_Database"

        # Get the user directory
        User_Dir = user_data_dir(Appname, appauthor = False)

        if os.path.exists(User_Dir):
            shutil.rmtree(User_Dir)
            print("User database folder deleted: {}".format(User_Dir))
        else:
            print("User database folder does not exist: {}".format(User_Dir))

    def commit_changes(self):
        """

        This method is used to commit the changes inside the database
        
        """
        self.connection.commit()
    
    def close_connection(self):
        """

        This method is used to close the connection with the database. This
        should be done when the work with the database is done.
        
        """
        # Close the connection after ensuring that exists
        if self._connection is not None:
            self._connection.close()
            self._connection = None
    
    def create_table_chemical_properties(self):
        """

        This method is used to create the table of chemical properties if it 
        does not exist. So, this must only be used to create a new database file.
        
        """
        # Setting the cursor to modify the table
        Cur = self.get_db_cursor()

        # Create the table if there is no table                                    
        Cur.execute("""                                                                         
                    CREATE TABLE IF NOT EXISTS Chemical_properties(
                    CAS TEXT UNIQUE,
                    ID TEXT PRIMARY KEY, 
                    formula TEXT,
                    Description TEXT,
                    MW_g_per_mol REAL CHECK (MW_g_per_mol > 0), 
                    Phase TEXT, 
                    Cp_J_per_g_K REAL, 
                    Rho_kg_per_m3 REAL CHECK (Rho_kg_per_m3 > 0), 
                    Hvap_J_per_mol REAL,
                    V_m3_per_mol REAL,
                    Hf_J_per_mol REAL,
                    Last_Modification TEXT                       
        );                                                                                  
        """)
        return self.commit_changes()
                                                                    
    def get_db_cursor(self):
        """

        This method retrieves the database cursor associated with the established 
        connection. Note that this cursor is tied to the connection property.
        
        """
        return self.connection.cursor()

    def get_table_names(self):
        """

        This method is used to display the tables of the database ensuring
        the creation of Chemical_properties table.
        
        """
        # Setting the cursor
        Cur = self.get_db_cursor()

        # Get the name of the tables inside the database
        Res = Cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return print(Res)
    
    def insert_data_into_db(self,   
                            ID = None,
                            CAS = None, 
                            formula = None,
                            description = None, 
                            MW = None, 
                            Phase = None, 
                            Cp = None, 
                            Rho = None, 
                            Hvap = None,
                            Hf = None,
                            V = None):
        """

        This method is used to add data into the database. If certain chemical
        already exists, the code will raise an error.
       
        Parameters
        ----------
        ID : str 
            The name of the chemical.

        CAS : str
            The CAS number of the chemical.

        formula : str 
            The formula of the chemical. Note that it must be a string.

        MW : float 
            Molecular weight (g/mol).

        Phase : str
            The phase of the chemical. Must be one of this: 's','g','l'

        Cp : float
            Constant Heat Capacity model (J/g).

        Rho : float
            Constant density model (kg/m3).

        Hvap : float
            Heat of vaporisation (J/mol) model as function of temperature (K).

        V : float
            Molar volume (m3/mol).
        
        Hf : float
            Enthalpy of formation (J/mol).
        
        """
        # Check if the connection is well initialized 
        if self.connection is None:
            raise ValueError("A connection to database must be provided")

        # Setting the cursor
        cur = self.get_db_cursor()

        # Setting timezone
        Timestamp = self.current_timestamp

        # Check if the chemical already exists in the database
        cur.execute("SELECT * FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID,CAS))
        Doitexists = cur.fetchone()
        if Doitexists:
            print("{} (CAS: {}) already exists in the database".format(ID,CAS))
            return 
            
        # Check which data is not provided and subtitutes it for "None"
        Add = (
            CAS if CAS is not None else None,
            ID if ID is not None else None,
            formula if formula is not None else None,
            description if description is not None else 0,
            MW if MW is not None else 1,
            Phase if Phase is not None else None,
            Cp if Cp is not None else 0,
            Rho if Rho is not None else 0,
            Hvap if Hvap is not None else 0,
            Hf if Hvap is not None else 0,
            V if V is not None else 0,
        )

        # Insert the data provided into the database
        cur.execute("""INSERT INTO Chemical_properties 
                    (CAS, ID, formula, description, MW_g_per_mol, Phase, Cp_J_per_g_K, Rho_kg_per_m3, Hvap_J_per_mol, Hf_J_per_mol, V_m3_per_mol, Last_Modification) 
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", Add + (Timestamp,))

        # Commint the changes in the database
        self.commit_changes()
        return print("CAS:{} ID:{}, formula:{}, MW:{}, Phase:{}, Cp:{}, Rho:{}, Hvap:{}, Hf: {}, V:{} added to the database".format(CAS, ID, formula, MW, Phase, Cp, Rho, Hvap, Hf, V))
    
    def remove_data_from_db(self, ID: str = None, CAS: str = None):
        """
        
        This method is used to removed certain chemical from the
        database using the ID or CAS as identification. Note that
        the ID is not interpreted in this database as UNIQUE, this 
        only corresponds to CAS number. However, the ID remains as
        the primary key.

        """
        if ID is None and CAS is None:
            raise ValueError("At least one of ID or CAS must be provided")

        # Get the cursor
        Cur = self.get_db_cursor()

        # Delete the chemical from the database
        Cur.execute("DELETE FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID,CAS))

        # Check if the chemical was succesfully deleted
        if Cur.rowcount == 0:
            print("No matching chemical found in the database")
        elif ID is None: 
            print("The Chemical with CAS: {} was succesfully deleted from the database".format(CAS))
        elif CAS is None:
            print("The Chemical {} was succesfully deleted from the database".format(ID))
        else:
            print("The Chemical {} with CAS: {} was succesfully deleted from the database".format(ID,CAS))

        self.commit_changes()

    def update_data_from_db(self, ID = None, CAS = None, properties: dict = None):
        """
        
        This method is used to update the properties of certain chemical which corresponds 
        to the ID or the CAS number provided. 
        
        Parameters
        ----------
        properties : dict 
            dictionary with the form {Property: newvalue}. The properties available
            are exposed above.

        Properties
        ----------
        ID : str 
            The name of the chemical.

        CAS : str
            The CAS number of the chemical.

        formula : str 
            The formula of the chemical. Note that it must be a string.

        MW : float 
            Molecular weight (g/mol).

        Phase : str
            The phase of the chemical. Must be one of this: 's','g','l'

        Cp : float
            Constant Heat Capacity model (J/g).

        Rho : float
            Constant density model (kg/m3).

        Hvap : float
            Heat of vaporisation (J/mol) model as function of temperature (K).

        V : float
            Molar volume (m3/mol).
        
        Hf : float
            Enthalpy of formation (J/mol).
        
        """
        # Setting the cursor
        Cur = self.get_db_cursor()

        # Setting the timestamp
        Timestamp = self.current_timestamp

        # Check if the chemical exist in the database
        Cur.execute("SELECT * FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID, CAS))
        if not Cur.fetchone():
            raise ValueError("The specified chemical does not exist in the database")

        # Obtaining the column names of the database table
        Cur.execute("PRAGMA table_info(Chemical_properties)")
        Columns_Info = Cur.fetchall()
        Columns_Name = [col[1] for col in Columns_Info]

        # Convert arguments to table names
        Properties_Translated = self.translate_column_alias_dict(properties)

        # Checking that only valid column names are provided
        for key in Properties_Translated.keys():
            if key not in Columns_Name:
                raise KeyError("The {} key is not recognised as a valid column".format(key))
            else:
                continue
        
        # Updating the database
        Update_Clause = ",".join(f'"{key}" = ?' for key in Properties_Translated.keys())
        Query = f"UPDATE Chemical_properties SET {Update_Clause}, Last_Modification = ? WHERE ID = ? OR CAS = ?"
        Query_Parameters = list(Properties_Translated.values()) + [Timestamp,ID, CAS]
        Cur.execute(Query, Query_Parameters)
        
        # Commit the changes in the database
        self.commit_changes()

        return print(f"The {','.join(properties.keys())} properties of {','.join(filter(None, [ID,CAS]))} have been updated")

    def get_whole_data_from_db(self):
        """

        This method is used to get all the data inside the database. This allows to query the whole database
        getting all the data inside it.
        
        """
        # Setting the cursor
        cur = self.get_db_cursor()

        # Select the whole data from the Chemical_properties table
        cur.execute("SELECT * FROM Chemical_properties")

        # Save this data inside the 'data' variable
        data = cur.fetchall()
        return data
    
    def get_certain_data_from_db(self, ID = None, properties: list = None):
        """

        This method is used to return the selected properties of the chemical whose CAS
        is provided. The properties that the user wants to extract from database must be
        defined inside the list "properties" as a str.
        
        Properties
        ----------
        ID : str 
            The name of the chemical.

        CAS : str
            The CAS number of the chemical.

        formula : str 
            The formula of the chemical. Note that it must be a string.

        MW : float 
            Molecular weight (g/mol).

        Phase : str
            The phase of the chemical. Must be one of this: 's','g','l'

        Cp : float
            Constant Heat Capacity model (J/g).

        Rho : float
            Constant density model (kg/m3).

        Hvap : float
            Heat of vaporisation (J/mol) model as function of temperature (K).

        V : float
            Molar volume (m3/mol).
        
        Hf : float
            Enthalpy of formation (J/mol).
        
        Example
        -------
        >>> DB = ChemDatabase.copy_multimodelling_db()
        >>> Peptide = DB.get_certain_data_from_db(
        >>>                 ID = 'Peptides', 
        >>>                 properties = ['Cp','Rho'] 
        >>>                 )
        >>> print(Peptide)
        {'Cp': 1.365, 'rho': 1350}   

        """
        #Setting the cursor
        cur = self.get_db_cursor()

        # Check if a ID is provided
        if ID == None:
            raise ValueError("You must provide the ID of the chemical")

        # Translate the list to match the column names
        Properties_Translated = self.translate_column_alias_list(properties)

        # Getting the data
        Results = {}
        for element in Properties_Translated:
                column = element
                cur.execute("SELECT {} FROM Chemical_properties WHERE ID = ?".format(column), (ID,))
                data = cur.fetchone()
                Results[element] = data[0] if data else None
        return Results

    def get_dataframe_from_db(self):
        """

        This method allows to transform the mydatabase.db file to a excel file and returning also
        a pandas DataFrame.

        """
        # Read the SQL database converting it into a pandas DataFrame
        Df = pd.read_sql_query("Select * FROM Chemical_properties", self.connection)

        # Save the pandas DataFrame as an excel
        Excel_Filename = self.dbname.replace(".db",".xlsx") 
        Df.to_excel(Excel_Filename, index = False)
        return Df
    
    def check_chemical(self, ID: str = None, CAS: str = None):
        """

        This method is used to check if the chemical provided exists in the database.

        Parameters
        ----------
        ID : str 
            The name of the chemical.

        CAS : str 
            The CAS number of the chemical.

        """
        if ID is None and CAS is None:
            raise ValueError("At least one of 'ID' or 'CAS' must be provided")
        
        Cur = self.get_db_cursor()
        
        if ID is not None and CAS is not None:
            Cur.execute("SELECT 1 FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID, CAS))
        elif ID is not None:
            Cur.execute("SELECT 1 FROM Chemical_properties WHERE ID = ?",(ID,))
        else:
            Cur.execute("SELECT 1 FROM Chemical_properties WHERE CAS = ?",(CAS,))
        
        return Cur.fetchone() is not None
    
    def translate_column_alias_dict(self, input_dict: dict = None):
        """

        This method is used to translate the keys of the dictionary provided
        to match the column names of the database. Note that the dictionary used 
        to translate this dictionary is a class attribute.

        Parameters
        ----------
        input_dict : dict 
            This dictionary contains the {column: value} pair

        """
        # Check if the input dictionary is provided
        if input_dict is None:
            raise ValueError("No input dictionary for translating it")
        
        # Build the alias map
        Alias_Map = {}
        for real_name, aliases in self.Column_Keys.items():
            for alias in aliases:
                Alias_Map[alias.lower()] = real_name
        
        # Translate
        Translated = {}
        for key, value in input_dict.items():
            Translated_Key = Alias_Map.get(key.lower(), key)
            Translated[Translated_Key] = value
        
        return Translated
    
    def translate_column_alias_list(self, input_list: list = None):
        """

        This method is used to translate a list of names to match the 
        column names of the database. Note that the dictionary used to 
        translate this list is a class attribute.

        Parameters
        ----------
        input_list : list 
            This list contains the alias of the column names.

        

        """
        # Check if the input list is provided
        if input_list is None:
            raise ValueError("No input list for translating it")
        
        # Build the alias map
        Alias_Map = {}
        for real_name, aliases in self.Column_Keys.items():
            for alias in aliases:
                Alias_Map[alias.lower()] = real_name
        
        # Return the list with the translated column names
        return [Alias_Map.get(str(col).lower(), str(col)) for col in input_list]