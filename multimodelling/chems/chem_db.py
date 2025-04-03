"""
"""
import sqlite3
import pandas as pd

__all__ = ('ChemDataBase')

class ChemDataBase:          #TODO I´d like to create anoter table for chemical composition of feedstocks, probably inside the Multimodelling_Chem.db

    def __init__(self, dbname: str = None):
        """
        
        Create a ChemDataBase object by providing the name of the database in your current
        directory or the name of the database you want to create. This class allows to either
        create or manage a database of chemicals to reuse this chemicals into MultiModelling.
        
        ARGUMENTS:
        
        dbname (str): Name of the database. If the database already exists in your current directory
        write "mydirectory.db". However, a new database could be created by writing a 
        new name "mynewdatabase.db".
    
        """
        # The default name of the database is "MultiModelling_Chem.db"
        self.dbname = dbname if dbname is not None else "MultiModelling_Chem.db"

        # Initialize the connection property
        self._connection = None

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
    
    def create_table(self):
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
                    "MW g/mol" REAL CHECK ("MW g/mol" > 0), 
                    Phase TEXT, 
                    "Cp J/(g*k)", 
                    "Rho kg/m3" REAL CHECK ("Rho kg/m3" > 0), 
                    "Hvap J/mol",
                    "V m3/mol",
                    Creation_Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP                       
        );                                                                                  
        """)
        return self.commit_changes()                                                                #TODO Adjust the CURRENT_TIMESTAMP to the Europe/Madrid timezone usig pytz
                                                                                                    # The idea is to transform this into a property or a class attribute.
    def get_db_cursor(self):
        """

        This method retrieves the database cursor associated with the established 
        connection. Note that this cursor is tied to the connection property.
        
        """
        return self.connection.cursor()

    def verify_creation_new_table(self):
        """

        This method is used to display the tables of the database ensuring
        the creation of Chemical_properties table.
        
        """
        # Setting the cursor
        Cur = self.get_db_cursor()

        # Get the name of the tables inside the database
        Res = Cur.execute("SELECT name FROM sqlite_master")
        return print(Res.fetchone())
    
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
                            V = None):
        """

        This method is used to add data into the database. If certain chemical
        already exists, the code will raise an error.
       
        ARGUMENTS:

        cursor: The cursor of the database which is obtained using the get_db_cursor
        method if the table exists. Otherwise, use create_table method.

        ID (str): The name of the chemical.

        CAS (str): The CAS number of the chemical and the primary key of the database.

        formula (str): The formula of the chemical. Note that it must be a string.

        MW (float): Molecular weight (g/mol).

        Phase (str): The phase of the chemical. Must be one of this: 's','g','l'

        Cp (float): Constant Heat Capacity model (J/g).

        Rho (float): Constant density model (kg/m3).

        Hvap (float): Heat of vaporisation (J/mol) model as function of temperature (K).
        
        """
        # Check if the connection is well initialized 
        if self.connection is None:
            raise ValueError("A connection to database must be provided")
        
        # Setting the cursor
        cur = self.get_db_cursor()

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
            description if description is not None else None,
            MW if MW is not None else None,
            Phase if Phase is not None else None,
            Cp if Cp is not None else None,
            Rho if Rho is not None else None,
            Hvap if Hvap is not None else None,
            V if V is not None else None,

        )

        # Insert the data provided into the database
        cur.execute("""INSERT INTO Chemical_properties (CAS, ID, formula, description, "MW g/mol", Phase, "Cp J/(g*k)", "Rho kg/m3", "Hvap J/mol", "V m3/mol") VALUES(?, ?, ?, ?, ?, ?, ?,?,?,?)""", Add)

        # Commint the changes in the database
        self.commit_changes()
        return print("CAS:{} ID:{}, formula:{}, MW:{}, Phase:{}, Cp:{}, Rho:{}, Hvap:{}, V:{} added to the database".format(CAS, ID, formula, MW, Phase, Cp, Rho, Hvap, V))
    
    def remove_data_from_db(self, ID, CAS):
        """
        
        This method is used to removed certain chemical from the
        database using the ID or CAS as identification. Note that
        the ID is not interpreted in this database as UNIQUE, this 
        only corresponds to CAS number.

        """
        # Get the cursor
        Cur = self.get_db_cursor()

        # Delete the chemical from the database
        Cur.execute("DELETE FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID,CAS))

        # Check if the chemical was succesfully deleted
        if Cur.rowcount == 0:
            print("No matching chemical found in the database")
        else: 
            print("The Chemical {} with CAS: {} was succesfully deleted from the database".format(ID, CAS))

        self.commit_changes()

    def update_data_from_db(self, ID = None, CAS = None, properties: dict = None):
        """
        
        This method is used to update the properties of certain chemical which corresponds 
        to the ID or the CAS number provided. 
        
        PROPERTIES: dictionary with the form {Property: newvalue}. The current properties that
        can be updated are the next:

        ID (str): The name of the chemical.

        CAS (str): The CAS number of the chemical and the primary key of the database.

        formula (str): The formula of the chemical. Note that it must be a string.

        MW (float): Molecular weight (g/mol).

        Phase_ref (str): The phase reference of the chemical. Must be one of this: 's','g','l'

        Cp (float): Constant Heat Capacity model (J/g).

        Rho (float): Constant density model (kg/m3).

        Hvap (float): Heat of vaporisation (J/mol) model as function of temperature (K).
        
        """
        # Setting the cursor
        Cur = self.get_db_cursor()

        # Check if the chemical exist in the database
        Cur.execute("SELECT * FROM Chemical_properties WHERE ID = ? OR CAS = ?",(ID, CAS))
        if not Cur.fetchone():
            raise ValueError("The specified chemical does not exist in the database")

        # Obtaining the column names of the database table
        Cur.execute("PRAGMA table_info(Chemical_properties)")
        Columns_Info = Cur.fetchall()
        Columns_Name = [col[1] for col in Columns_Info]

        # Checking that only valid column names are provided
        for key in properties.keys():
            if key not in Columns_Name:
                raise KeyError("The {} key is not recognised as a valid column".format(key))
            else:
                continue
        
        # Updating the database
        Update_Clause = ",".join(f'"{key}" = ?' for key in properties.keys())
        Query = f"UPDATE Chemical_properties SET {Update_Clause}, Creation_Date = CURRENT_TIMESTAMP WHERE ID = ? OR CAS = ?"
        Query_Parameters = list(properties.values()) + [ID, CAS]
        Cur.execute(Query, Query_Parameters)
        
        # Commit the changes in the database once the loop has ended
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
        defined inside the list "properties".
        
        Properties: (ID, formula, MW, Phase_ref, Cp, Rho, Hvap)
        
        """
        #Setting the cursor
        cur = self.get_db_cursor()

        # Check if a ID is provided
        if ID == None:
            raise ValueError("You must provide the ID of the chemical")

        # Getting the data
        Results = {}
        for element in properties:
                column = f'"{element}"'
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
        Df.to_excel(self.dbname, index = False)
        return Df