from chem_db import ChemDataBase
import tkinter as tk

__all__ = (
    ""
)

class MultiModellingDB(tk.Tk):
    """
    """
    def __init__(self, 
                 screenName = None, 
                 baseName = None, 
                 className = "Tk", 
                 useTk = True, 
                 sync = False, 
                 use = None
                 ):
        super().__init__(screenName, baseName, className, useTk, sync, use)
        """
        """
        self.title("Multimodelling database")
        self.geometry("1920x1080")
        self._build_widgets()

    def database_query(self):
        """
        """

    def execute_query(self):
        """
        """
    
    def database_query_results(self):
        """
        """

    @property
    def build_widgets(self):
        """
        """

app = MultiModellingDB()
app.mainloop()