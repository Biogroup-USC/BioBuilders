"""
"""
import biosteam as bst

__all__ = ("SprayDryer",)

class SprayDryer(bst.Unit):
    """
    """
    _N_ins = 1
    _N_outs = 2

    def _init(self, 
              moisture_content: float = None,
              split: float = None,
              operating_T: float = None,
              ):
        """
        """
        self.moisture = moisture_content if moisture_content is not None else 0.15
        self.split = split
        self._operating_T = operating_T

    @property
    def operating_T(self):
        """
        """
        if self._operating_T is None:
            self._operating_T = (273.15 + 100)
        return self._operating_T
        
    @operating_T.setter
    def operating_T(self,value):
        """
        """
        self._operating_T = value

    def _run(self):
        """
        """
        # Define the streams 
        Feed = self.ins[0]
        Dryed, Water = self.outs
        
        # Define the temperature of the outlet streams
        Dryed.T = 273.1 + 100 if self.operating_T <= (273.15 + 100) else self.operating_T
        Water.T = 273.1 + 100 if self.operating_T <= (273.15 + 100) else self.operating_T

        # Water balance
        

    def _design(self):
        """
        """
        pass

    def _cost(self):
        """
        """
        pass