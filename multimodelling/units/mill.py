"""
"""
import biosteam as bst

__all__ = ("Mill",)

class Mill(bst.Unit):
    """

    Create a Mill object by providing the losses associated to this process. The impact of
    size reduction should be simulated in the following updates. 

    ARGUMENTS:

    - ID (str): This ID refers to the name of this unit.

    - ins (list): List of input streams. In this case, there is only 1 input.

    - outs (list): List of output streams. In this case, there is 2 possible outputs. However, the
    losses stream could be avoided when no losses are being considering.[Out, Losses]
        
    - losses (float): The losses associated to this process. This parameter is represented as (g losses/
    g feed) and it is treated as a separation factor.

    """

    _N_ins = 1
    _N_outs = 2
    _units = 'kg/hr'
    
    def _init(self, losses):
        # The _init method is used to add input parameters to the AbstractUnit
        if not (0 <= losses <= 1):
            raise ValueError("Losses must be between 0 and 1 (fractional value).")
        self.losses = losses

    def _run(self):
        """
        
        This method runs the unit. The milla mass balance is simulated following the next equation:
        Output = sfi * Input {sfi = losses for Losses stream and sfi = (1-losses) for Out stream} 
        

        """
        # Defining the inlet
        feed = self.ins[0]

        #Defining the Outlet
        Out = self.outs[0]
        Losses = self.outs[1]

        # Running the Unit
        ## This Unit is simulated basically as OUT = sfi * IN where the sfi represents the losses
        Out.copy_like(feed)
        Out.F_mass = (1-self.losses)*feed.F_mass
        Losses.copy_like(feed)
        Losses.F_mass = (self.losses)*feed.F_mass

    def _design(self):
        pass

    def _cost(self):
        pass