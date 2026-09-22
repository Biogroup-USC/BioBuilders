"""
References:
[1] D. W. Green and R. H. Perry, Eds., “Membrane separation processes,” in Perry’s 
Chemical Engineers’ Handbook, 8th ed., sec. 20, “Alternative Separation Processes.” 
New York, NY, USA: McGraw-Hill, 2008

[2] D. R. Woods, “Membranes and membrane configurations,” in Rules of Thumb in Engineering 
Practice, ch. 4, “Homogeneous Separation.” Weinheim, Germany: Wiley-VCH, 2007, sec. 4.15, 
pp. 123–128.
"""

import biosteam as bst
import numpy as np
from .centrifuge import SolidsSeparator
from typing import Literal
from math import ceil, exp

__all__ = (
    'RotaryVacuumFilter',
    'MembraneConcentration',
    'MembraneDiafiltration',
)
class RotaryVacuumFilter(SolidsSeparator):
    """
    Create a RotaryVacuumFilter object.
    
    Parameters
    ----------
    ins : 
        * [0] Feed
        * [1] Wash water
    outs :  
        * [0] Retentate
        * [1] Permeate
    split : array_like or dict[str, float]
           Component splits.
    moisture_content : float
                       Fraction of water in retentate.
    
    """
    _F_BM_default = {'Vessels': 2.32,}
   
    #: Revolutions per second
    rps = 20/3600
    
    #: Radius of the vessel (m)
    radius = 1
    
    #: Suction pressure (Pa)
    P_suction = 1500.
    
    #: For crystals (lb/day-ft^2)
    filter_rate = 6000
    
    _kwargs = {'moisture_content': 0.80} # fraction
    _bounds = {'Individual area': (2, 100)}
    _units = {'Area': 'ft^2',
              'Individual area': 'ft^2'}

    def _init(self,
              split,
              order=None,
              moisture_content=0.40,
              moisture_ID=None,
              solute_ID=None,
              strict_moisture_content=None,
              solids=None,
            ):
        SolidsSeparator._init(
            self,
            moisture_content=moisture_content,
            split=split,
            order=order,
            moisture_ID=moisture_ID,
            solute_ID=solute_ID,
            strict_moisture_content=strict_moisture_content,
        )

        self.solids = solids

        self._kWh_per_kg = None

        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._base_CE = None
    
    @property
    def kWh_per_kg(self):
        """
        """
        if self._kWh_per_kg is None:
            self._kWh_per_kg = 0.0055   # mean value from http://dx.doi.org/10.1016/j.jclepro.2016.06.164
        return self._kWh_per_kg

    @kWh_per_kg.setter
    def kWh_per_kg(self,value):
        """
        """
        self._kWh_per_kg = value

    def _design(self):
        flow = sum([stream.F_mass for stream in self.outs])
        self.design_results['Area'] = self._calc_Area(flow, self.filter_rate)
        
        if self.solids is not None:
            total_solids = sum(i.imass[self.solids].sum() for i in self.ins)
            self.add_power_utility(self.kWh_per_kg*total_solids)
    
    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 280000     # USD
        return self._base_cost   

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 22.0       # m3
        return self._base_area
    
    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 0.65
        return self._base_n_cost
    
    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value
    
    @property
    def base_CE(self):
        """
        """
        if self._base_CE is None:
            self._base_CE = 1000.0
        return self._base_CE
    
    @base_CE.setter
    def base_CE(self, value):
        """
        """
        self._base_CE = value

    def _cost(self):
        Design = self.design_results
        Area = Design['Area']
        ub = self._bounds['Individual area'][1]
        N_vessels = np.ceil(Area/ub)
        iArea = Area/N_vessels # individual vessel
        self.parallel['self'] = N_vessels
        Design['Individual area'] = iArea
        
        # Calculate the baseline purchase costs for the Rotatory Vacuum Drum Filter
        ## The base cost accounts for a rotatory drum filter, vacuum with discharger,
        ## filtrate pumps, vacuum system, motor and drive.
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        Filter_Purchase_Cost = self.base_cost * ((Area * 0.092903)/self.base_area)**self.base_n_cost
        self.baseline_purchase_costs['Vessels'] = Filter_Purchase_Cost * bst.CE/self.base_CE

    @staticmethod
    def _calc_Area(flow, filter_rate):
        """Return area in ft^2 given flow in kg/hr and filter rate in lb/day-ft^2."""
        return flow * 52.91 / filter_rate


class AbstractMembraneFiltration(bst.Unit, isabstract = True):
    """

    """
    _default_equipment_lifetime = {
        'Membrane train': 3,
    }

    # Number of input streams
    _N_ins = 1
    # Number of output streams
    _N_outs = 2
    # Results units
    _units = {
        "Area (active total)": "m2",
        "Area (per train)": "m2",
        "Area (installed total)": "m2",
        "Active trains": "",
        "Standby trains": "",
        "Installed trains": "",
        "LMH": "L/(m2 * h)",
        "Mass flux": "kg/(m2 * h)",
        "Volumetric flow": "m3/h",
        "Pump power per train": "kW",
    }

    def _init(
        self,
        rejection: dict[str, float] | None = None,
        pressure_drop: float = 120_000,
        permeate_pressure: float = 101_325,
        TMP: float | None = None,
        LMH: float | None = None,
        N_trains: int = 2,
        N_standby: int = 1,
        pump_efficiency: float = 0.70,
        
        solvent_IDs: tuple[str, ...] | None = None,
    ):
        self.rejection = (
            {} if rejection is None else rejection.copy()
        )
        self.pressure_drop = pressure_drop
        self.permeate_pressure = permeate_pressure
        self.TMP = TMP
        self.LMH = LMH
        self.N_trains = N_trains
        self.N_standby = N_standby
        self.pump_efficiency = pump_efficiency
        self.solvent_IDs = (
            ("Water",)
            if solvent_IDs is None
            else tuple(solvent_IDs)
        )

        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._base_CE = None

    def _solve_pressure(self):
        p_drop = self.pressure_drop         # Pa, P_inlet - P_retentate
        tmp = self.TMP                      # Pa, average TMP
        p_permeate = self.permeate_pressure # Pa, permeate pressure

        if p_drop is None or p_drop < 0:
            raise ValueError(
                f"{self.ID}: pressure_drop must be non-negative."
            )

        if tmp is None or tmp <= 0:
            raise ValueError(
                f"{self.ID}: TMP must be greater than zero."
            )

        if p_permeate is None or p_permeate <= 0:
            raise ValueError(
                f"{self.ID}: permeate_pressure must be greater than zero."
            )

        p_inlet = tmp + p_permeate + p_drop / 2
        p_retentate = p_inlet - p_drop

        if p_retentate <= 0:
            raise ValueError(
                f"{self.ID}: calculated retentate pressure must be "
                f"positive; received {p_retentate:.6g} Pa. "
                "Decrease pressure_drop, increase TMP, or increase "
                "permeate_pressure."
            )

        return p_inlet

    def _recovery(self, rejection, vcf):
        sieving = 1 - rejection
        return (1 / (1 + sieving * (vcf - 1)))
    
    def _design(self):
        """
        """
        # The area is calculated using the permeate following the next
        # equation: LMH = Q/A
        permeate, retentate = self.outs
        feed, = self.ins
        
        LMH = self.LMH

        if LMH is None or LMH <= 0:
            raise ValueError(
                f"{self.ID}: LMH must be greater than zero."
            )

        A = permeate.F_vol * 1000 / LMH         # m2
        mass_flux = LMH * 1e-3 * permeate.rho   # kg/m2/h

        # Scheduling
        N_backup = self.N_standby
        N_duty = self.N_trains
        N_installed = N_duty + N_backup
        self.parallel['Membrane train'] = N_installed

        # Total installed
        active_area = A
        required_area_per_train = active_area / N_duty
        total_installed_area = required_area_per_train * N_installed

        # Pump
        self.parallel['Pump'] = N_installed
        Q_per_active_train = feed.F_vol / N_duty
        P_obj = self._solve_pressure()

        deltaP_per_train = P_obj - feed.P
        power_per_train = deltaP_per_train * Q_per_active_train / (3.6e6 * self.pump_efficiency)
        power_filtration = power_per_train * N_duty
        self.add_power_utility(power_filtration)

        # Design results
        design = self.design_results
        design["Area (active total)"] = active_area
        design["Area (per train)"] = required_area_per_train
        design["Area (installed total)"] = total_installed_area
        design["Active trains"] = self.N_trains
        design["Standby trains"] = N_backup
        design["Installed trains"] = N_installed
        design["LMH"] = permeate.F_vol * 1000 / A
        design["Mass flux"] = mass_flux
        design["Volumetric flow"] = permeate.F_vol
        design["Pump power per train"] = power_per_train

    @property
    def base_cost(self):
        """
        """
        if self._base_cost is None:
            self._base_cost = 240    # $ for membrane and housing
        return self._base_cost

    @base_cost.setter
    def base_cost(self, value):
        """
        """
        self._base_cost = value

    @property
    def base_n_cost(self):
        """
        """
        if self._base_n_cost is None:
            self._base_n_cost = 1.0
        return self._base_n_cost

    @base_n_cost.setter
    def base_n_cost(self, value):
        """
        """
        self._base_n_cost = value

    @property
    def base_area(self):
        """
        """
        if self._base_area is None:
            self._base_area = 1         # m2
        return self._base_area

    @base_area.setter
    def base_area(self, value):
        """
        """
        self._base_area = value

    @property
    def base_CE(self):
        """
        """
        if self._base_CE is None:
            self._base_CE = 1000
        return self._base_CE

    @base_CE.setter
    def base_CE(self, value):
        """
        """
        self._base_CE = value

    def _cost(self):
        """
        """
        # Load all the design parameters needed to calculate the costs
        area = self.design_results["Area (per train)"]

        # Calculate the baseline purchase cost for membrane module
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        membrane_train = self.base_cost * (area/self.base_area)**self.base_n_cost

        self.baseline_purchase_costs['Membrane train'] = membrane_train

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Membrane train'] = self.F_M['Membrane train'] = self.F_P['Membrane train'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.80             # Filters
        Instrumentation_Control = 0.50
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        bare_module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Membrane train'] = bare_module

        ## Scale the costs using CEPCI
        self.baseline_purchase_costs['Membrane train'] *= bst.CE/self.base_CE
        self.equipment_lifetime['Membrane train'] = self._default_equipment_lifetime['Membrane train']

        # Auxiliar pump cost
        power_per_train = self.design_results['Pump power per train']
        if power_per_train < 23.:
            pump = 9500 * (power_per_train / 23.) ** 0.29
        else:
            pump = 9500 * (power_per_train / 23.) ** 0.79

        self.baseline_purchase_costs['Pump'] = pump
        self.baseline_purchase_costs['Pump'] *= bst.CE/self.base_CE

        self.F_D["Pump"] = 1.
        self.F_M["Pump"] = 1.
        self.F_P["Pump"] = 1.

        Delivery = 0.10
        Installation = 0.60
        Instrumentation_Control = 0.50
        Piping = 0.31

        self.F_BM["Pump"] = (1 + (Delivery + Installation + Instrumentation_Control + Piping))

class MembraneConcentration(AbstractMembraneFiltration):
    """

    """
    # Number of input streams
    _N_ins = 1

    # Results units
    _units = {
        **AbstractMembraneFiltration._units,
        "VCF": "times",
    }

    def _init(
        self,
        rejection: dict[str, float] | None = None,
        pressure_drop: float = 120_000,
        permeate_pressure: float = 101_325,
        TMP: float | None = None,
        LMH: float | None = None,
        VCF: float | None = None,
        N_trains: int = 2,
        N_standby: int = 1,
        solvent_IDs: tuple[str, ...] | None = None,
        pump_efficiency: float = 0.70,
    ):
        super()._init(
            rejection=rejection,
            pressure_drop=pressure_drop,
            permeate_pressure=permeate_pressure,
            TMP=TMP,
            LMH=LMH,
            N_trains=N_trains,
            N_standby=N_standby,
            solvent_IDs=solvent_IDs,
            pump_efficiency=pump_efficiency,
        )

        self.VCF = VCF

    def _run(self):
        feed, = self.ins
        permeate, retentate = self.outs

        # Initially, all feed components are placed in the permeate
        permeate.copy_like(feed)

        # Start with an empty retentate
        retentate.copy_like(feed)
        retentate.empty()

        # Distribute solutes based on rejection
        vcf = self.VCF
        for chem in feed.chemicals:
            chem_id = chem.ID

            if chem_id in self.solvent_IDs:
                continue
            elif chem_id in self.rejection:
                rejection = self.rejection[chem_id]
            else:
                rejection = 0.

            if not 0.0 <= rejection <= 1.0:
                raise ValueError(
                    f"{self.ID}: rejection for {chem_id!r} must be "
                    f"between 0 and 1; received {rejection}."
                )
            
            recovery = self._recovery(rejection, vcf)
            
            retentate.imass[chem_id] = recovery * feed.imass[chem_id]
            permeate.imass[chem_id] = feed.imass[chem_id] - retentate.imass[chem_id]

        # Distribute solvents
        Q_F = feed.F_vol
        Q_solutes_R = retentate.F_vol
        Q_solvent_R = (Q_F - Q_solutes_R * vcf) / vcf

        Q_solvent_F = sum(feed.ivol[ID] for ID in self.solvent_IDs)
        solvent_fraction_R = Q_solvent_R / Q_solvent_F
        for chem_id in self.solvent_IDs:
            retentate.imass[chem_id] = solvent_fraction_R * feed.imass[chem_id]
            permeate.imass[chem_id] = feed.imass[chem_id] - retentate.imass[chem_id]

        P_inlet = self._solve_pressure()

        permeate.P = self.permeate_pressure
        retentate.P = (
            P_inlet - self.pressure_drop
        )

    def _design(self):
        """
        """
        super()._design()
        feed, = self.ins
        retentate = self.outs[1]

        if retentate.F_vol <= 0:
            raise ValueError(
                f"{self.ID}: retentate volume must be greater than zero."
            )

        self.design_results["VCF"] = (
            feed.F_vol / retentate.F_vol
        )

class MembraneDiafiltration(AbstractMembraneFiltration):
    """
    """
    _N_ins = 2

    auxiliary_unit_names = ()

    _units = {
        **AbstractMembraneFiltration._units,
        "Batch volume": "m3",
        "Batch scheduling interval": "h",
        "Cycle time": "h",
        "Diafiltration time": "h",
        "Permeate flow per train": "m3/h",
        "Recirculation flow per train": "m3/h",
        "Recirculation pressure rise": "Pa",
        "Recirculation power per train": "kW",
        "Average recirculation power": "kW",
        "Average active trains": "",
        "Total process vessel volume": "m3",
        "Working volume fraction": "",
        "Agitator power per train": "kW",
    }

    def _init(
        self,
        rejection,
        batch_volume,
        diavolumes,
        loading_time,
        unloading_time,
        buffer_composition,
        old_solvent_id,
        new_solvent_id,
        pressure_drop: float = 120_000.0,
        permeate_pressure: float = 101_325.0,
        TMP: float = None,
        LMH: float = None,
        LMH_feed_flow: float = None,
        N_trains: int = 2,
        N_standby: int = 1,        
        pump_efficiency: float = 0.70,
    ):

        super()._init(
            rejection=rejection,
            pressure_drop=pressure_drop,
            permeate_pressure=permeate_pressure,
            TMP=TMP,
            LMH=LMH,
            N_trains=N_trains,
            N_standby=N_standby,
            pump_efficiency=pump_efficiency,
            solvent_IDs = (old_solvent_id, new_solvent_id),
        )

        if diavolumes <= 0.:
            raise ValueError("diavolumes must be greater than zero.")

        self.batch_volume = batch_volume
        self.N_trains = N_trains
        self.diavolumes = diavolumes
        self.loading_time = loading_time
        self.unloading_time = unloading_time
        self.old_solvent_id = old_solvent_id
        self.new_solvent_id = new_solvent_id
        self.buffer_composition = buffer_composition
        self.LMH_feed_flow = LMH_feed_flow

        self._kW_per_m3 = None
        self._W_volume = None

    def _run(self):

        feed, buffer = self.ins
        permeate, retentate = self.outs

        retentate.empty()
        permeate.empty()

        # Diafiltration buffer
        Q_feed_avg = feed.F_vol
        N = self.diavolumes

        # Total buffer volume
        Q_buffer_avg = N * Q_feed_avg

        # Buffer composition
        w_buffer = self.buffer_composition

        # Build buffer and scale it
        buffer.empty()

        for chem, w in w_buffer.items():
            buffer.imass[chem] = w

        scale = Q_buffer_avg / buffer.F_vol

        buffer.F_mass *= scale

        for chem in feed.chemicals:

            chem_ID = chem.ID

            if chem_ID in self.rejection:
                Ri = self.rejection[chem_ID]
                Si = 1. - Ri
            else:
                # Solvents are distributed equally
                # Solutes with no specific rejection are assumed to be washed
                Si = 1.

            if Si > 1e-12: 
                wash_factor = exp(-Si * N)

                mass_retained = (
                    feed.imass[chem_ID] * wash_factor +
                    (buffer.imass[chem_ID] / (Si * N)) * (1 - wash_factor)
                )     
            else:
                mass_retained = feed.imass[chem_ID] + buffer.imass[chem_ID]

            total_mass_in = feed.imass[chem_ID] + buffer.imass[chem_ID]
            retentate.imass[chem_ID] = mass_retained
            permeate.imass[chem_ID] = total_mass_in - mass_retained

        # Outlet pressure
        permeate.P = retentate.P = self.permeate_pressure

        # Outlet temperature
        mixture = bst.Stream(None)
        mixture.mix_from([feed,buffer])

        permeate.T = retentate.T = mixture.T

    def _design(self):

        feed = self.ins[0]

        design = self.design_results
        N = self.diavolumes
        V_batch = self.batch_volume

        N_duty = self.N_trains
        N_standby = self.N_standby
        N_installed = N_duty + N_standby
        self.parallel["Membrane train"] = N_installed
        
        delta_t_batch = V_batch/feed.F_vol
        t_cycle = N_duty * delta_t_batch

        t_aux = self.loading_time + self.unloading_time
        t_df = t_cycle - t_aux

        if t_df <= 0.:
            raise ValueError(
                f"{self.ID}: infeasible batch scheduling. "
                f"Cycle time ({t_cycle:.3g} h) must be greater than "
                f"loading + unloading time ({t_aux:.3g} h)."
            )

        Q_p_train = N * V_batch / t_df

        A_train = 1000 * (Q_p_train/self.LMH)
        A_required = A_train * N_duty
        A_total_installed = A_train * N_installed

        design["Batch volume"] = V_batch
        design["Batch scheduling interval"] = delta_t_batch
        design["Cycle time"] = t_cycle
        design["Diafiltration time"] = t_df

        design["Permeate flow per train"] = Q_p_train

        design["Area (per train)"] = A_train
        design["Area (active total)"] = A_required
        design["Area (installed total)"] = A_total_installed

        design["Active trains"] = N_duty
        design["Standby trains"] = N_standby
        design["Installed trains"] = N_installed

        # Pump
        self.parallel['Pump'] = N_installed
        f_overlap = t_df / delta_t_batch
        Q_recirc_train = self.LMH_feed_flow * A_train / 1000

        P_memb_in = self._solve_pressure()
        P_tank = 101325

        P_memb_out = P_memb_in - self.pressure_drop
        if P_memb_out < P_tank:
            raise ValueError(
                f"{self.ID} membrane outlet pressure "
                f"({P_memb_out:.3g} Pa) is lower than the tank pressure "
                f"({P_tank:.3g} Pa)."
            )

        deltaP = P_memb_in - P_tank
        power_recirc_train = Q_recirc_train * deltaP / (3.6e6 * self.pump_efficiency)
        power_recirc_pump = power_recirc_train * f_overlap

        # Agitator
        self.parallel["Agitator"] = N_installed
        power_agitator = self.kW_per_m3 * V_batch * f_overlap

        self.add_power_utility(power_recirc_pump+power_agitator)

        design["Average active trains"] = f_overlap
        design["Recirculation flow per train"] = Q_recirc_train
        design["Recirculation pressure rise"] = deltaP
        design["Recirculation power per train"] = power_recirc_train
        design["Average recirculation power"] = power_recirc_pump
        design["Pump power per train"] = power_recirc_train
        design["Total process vessel volume"] = V_batch / self.W_volume
        design["Working volume fraction"] = self.W_volume
        design["Agitator power per train"] = power_agitator/f_overlap

        # Process vessel
        self.parallel["Process vessel"] = N_installed

    @property
    def kW_per_m3(self):
        """
        Volumetric power [kW/m3] of the process tank.
        """
        if self._kW_per_m3 is None:
            self._kW_per_m3 = (0.2 + 1.5)/2 # Rules of the Thumb
        return self._kW_per_m3
    @kW_per_m3.setter
    def kW_per_m3(self, value):
        """
        Volumetric power [kW/m3] of the process tank.
        """
        self._kW_per_m3 = value

    @property
    def W_volume(self):
        """
        Working volume ratio of the process tank.
        """
        if self._W_volume is None:
            self._W_volume = 0.85
        return self._W_volume
    @W_volume.setter
    def W_volume(self, value):
        """
        Working volume ratio of the process tank.
        """
        self._W_volume = value

    def _cost(self):
        super()._cost()

        # Process vessel cost
        V_total = self.design_results['Batch volume'] / self.W_volume
        process_vessel = 14_000 * (V_total / 20.)**0.71
        
        self.baseline_purchase_costs['Process vessel'] = process_vessel
        self.baseline_purchase_costs['Process vessel'] *= bst.CE/self.base_CE

        self.F_D["Process vessel"] = 1.
        self.F_M["Process vessel"] = 2.0
        self.F_P["Process vessel"] = 1.

        Delivery = 0.10
        Installation = 0.60
        Instrumentation_Control = 0.50
        Piping = 0.31

        self.F_BM["Process vessel"] = (1 + (Delivery + Installation + Instrumentation_Control + Piping))

        # Agitator cost
        kW = self.kW_per_m3 * self.design_results['Batch volume']
        n_agitator = 0.42 if kW < 1.75 else 0.52
        agitator = 6_000 * (kW / 1.75)**n_agitator

        self.baseline_purchase_costs['Agitator'] = agitator
        self.baseline_purchase_costs['Agitator'] *= bst.CE/self.base_CE

        self.F_D["Agitator"] = 1.
        self.F_M["Agitator"] = 1.19
        self.F_P["Agitator"] = 1.
        self.F_BM["Agitator"] = 1.