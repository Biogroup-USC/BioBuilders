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
from math import ceil

__all__ = (
    'RotaryVacuumFilter',
    'MembraneConcentration',
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
        'Membrane module': 3,
    }

    auxiliary_unit_names = ('pump',)

    # Number of input streams
    _N_ins = 1
    # Number of output streams
    _N_outs = 2
    # Results units
    _units = {
        "Area (total)": "m2",
        "Module area": "m2",
        "Modules": "membrane modules",
        "LMH": "L/(m2 * h)",
        "Mass flux": "kg/(m2 * h)",
        "Volumetric flow": "m3/h",
    }

    def _init(
        self,
        rejection: dict[str, float] | None = None,
        pressure_drop: float = 120_000,
        permeate_pressure: float = 101_325,
        TMP: float | None = None,
        LMH: float | None = None,
        module_area: float | None = None,
        solvent_IDs: tuple[str, ...] | None = None,
    ):
        self.rejection = (
            {} if rejection is None else rejection.copy()
        )
        self.pressure_drop = pressure_drop
        self.permeate_pressure = permeate_pressure
        self.TMP = TMP
        self.LMH = LMH
        self.module_area = module_area
        self.solvent_IDs = (
            ("Water",)
            if solvent_IDs is None
            else tuple(solvent_IDs)
        )

        self._base_cost = None
        self._base_n_cost = None
        self._base_area = None
        self._CE_base = None

        self._load_auxiliaries()

    def _load_auxiliaries(self):
        self.pump = self.auxiliary(
            "pump",
            bst.Pump,
            ins = self.ins[0],
        )

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
        p_retentate = p_inlet - p_permeate

        if p_retentate <= 0:
            raise ValueError(
                f"{self.ID}: calculated retentate pressure must be "
                f"positive; received {p_retentate:.6g} Pa. "
                "Decrease pressure_drop, increase TMP, or increase "
                "permeate_pressure."
            )

        return p_inlet

    def _design(self):
        """
        """
        # The area is calculated using the permeate following the next
        # equation: LMH = Q/A
        permeate = self.outs[0]
        
        LMH = self.LMH
        module_area = self.module_area

        if LMH is None or LMH <= 0:
            raise ValueError(
                f"{self.ID}: LMH must be greater than zero."
            )

        if module_area is None or module_area <= 0:
            raise ValueError(
                f"{self.ID}: module_area must be greater than zero."
            )

        A = permeate.F_vol * 1000 / LMH
        mass_flux = LMH * 1e-3 * permeate.rho   # kg/m2/h

        if module_area <= 0:
            raise ValueError("Module area must be greater than zero.")

        modules = ceil(A / module_area)

        # Design results
        design = self.design_results
        design["Area (total)"] = A
        design["LMH"] = LMH
        design["Mass flux"] = mass_flux
        design["Volumetric flow"] = permeate.F_vol  # m3/h
        design["Module area"] = module_area
        design["Modules"] = modules

        # Auxiliary pump design
        self.pump._design()

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
    def CE_base(self):
        """
        """
        if self._CE_base is None:
            self._CE_base = 1000
        return self._CE_base

    @CE_base.setter
    def CE_base(self, value):
        """
        """
        self._CE_base = value

    def _cost(self):
        """
        """
        # Load all the design parameters needed to calculate the costs
        area = self.design_results["Area (total)"]

        # Calculate the baseline purchase cost for membrane module
        ## Reference: Rules of the Thumb in Engineering Practice: Appendix D / DOI: 10.1002/9783527611119.
        membranes_module = self.base_cost * (area/self.base_area)**self.base_n_cost

        self.baseline_purchase_costs['Membrane module'] = membranes_module

        ## The material, pressure and temperature factors are assumed to be 1
        self.F_D['Membrane module'] = self.F_M['Membrane module'] = self.F_P['Membrane module'] = 1

        ## The Bare module factor which account for installation costs is calculated as the sum of delivery, installation,
        ## piping, instrumentation and controls. The percentages are obtained from the Chapter 6 of the next book:
        ## Peters, Max S, Klaus D Timmerhaus, and Ronald E West. Plant Design and Economics for Chemical Engineers. 5th ed International. New York: McGraw-Hill, 2004.
        ### Factors
        Delivery = 0.10
        Installation = 0.80             # Filters
        Instrumentation_Control = 0.50
        Piping = 0.31                   # Solid-Fluid   
        ### Calculate the bare module
        Bare_Module = (1 + (Delivery + Installation + Instrumentation_Control + Piping))
        self.F_BM['Membrane module'] = Bare_Module

        ## Scale the costs using CEPCI
        self.baseline_purchase_costs['Membrane module'] *= bst.CE/self.CE_base
        self.equipment_lifetime['Membrane module'] = self._default_equipment_lifetime['Membrane module']

        # Auxiliar pump cost
        self.pump._cost()

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
        solvent_to_solids_ratio: float | None = None,
        module_area: float | None = None,
        solids_IDs: tuple[str, ...] | None = None,
        solvent_IDs: tuple[str, ...] | None = None,
    ):
        super()._init(
            rejection=rejection,
            pressure_drop=pressure_drop,
            permeate_pressure=permeate_pressure,
            TMP=TMP,
            LMH=LMH,
            module_area=module_area,
            solvent_IDs=solvent_IDs,
        )

        if (VCF is None) == (solvent_to_solids_ratio is None):
            raise ValueError(
                f"{self.ID}: define exactly one of "
                "'VCF' or 'solvent_to_solids_ratio'."
            )

        self.VCF = VCF
        self.solvent_to_solids_ratio = solvent_to_solids_ratio
        self.solids_IDs = (
            () if solids_IDs is None else tuple(solids_IDs)
        )

    def _run(self):
        feed, = self.ins
        permeate, retentate = self.outs

        # Initially, all feed components are placed in the permeate
        permeate.copy_like(feed)

        # Start with an empty retentate
        retentate.copy_like(feed)
        retentate.empty()

        for chem, retentate_fraction in self.rejection.items():

            # Solvents are distributed later to meet the VCF
            # or solvent-to-solids ratio
            if chem in self.solvent_IDs:
                continue

            if not 0.0 <= retentate_fraction <= 1.0:
                raise ValueError(
                    f"{self.ID}: rejection for {chem!r} must be "
                    f"between 0 and 1; received {retentate_fraction}."
                )

            retained_mass = (
                retentate_fraction * feed.imass[chem]
            )

            retentate.imass[chem] = retained_mass
            permeate.imass[chem] = (
                feed.imass[chem] - retained_mass
            )

        liquid_solute_IDs = [
            chem.ID
            for chem in feed.chemicals
            if chem.ID not in self.solvent_IDs
            and chem.ID not in self.rejection
            and feed.imass[chem.ID] > 0
        ]

        # Solvents and unspecified solutes are distributed together
        mobile_IDs = [
            *self.solvent_IDs,
            *liquid_solute_IDs,
        ]

        solvent_mass_in = sum(
            feed.imass[chem]
            for chem in self.solvent_IDs
        )

        if self.solvent_to_solids_ratio is not None:

            if self.solvent_to_solids_ratio < 0:
                raise ValueError(
                    f"{self.ID}: solvent_to_solids_ratio "
                    "cannot be negative."
                )

            if solvent_mass_in <= 0:
                raise ValueError(
                    f"{self.ID}: no solvent is available in the feed. "
                    f"solvent_IDs={self.solvent_IDs}."
                )

            retained_solids = sum(
                retentate.imass[chem]
                for chem in self.solids_IDs
            )

            target_solvent_mass = (
                self.solvent_to_solids_ratio
                * retained_solids
            )

            mobile_fraction = (
                target_solvent_mass
                / solvent_mass_in
            )

            if not 0.0 <= mobile_fraction <= 1.0:
                raise ValueError(
                    f"{self.ID}: target solvent retention is infeasible. "
                    f"Available solvent: {solvent_mass_in:.6g} kg/h; "
                    f"required solvent: {target_solvent_mass:.6g} kg/h; "
                    f"calculated fraction: {mobile_fraction:.6g}."
                )

        else:

            if self.VCF is None or self.VCF < 1.0:
                raise ValueError(
                    f"{self.ID}: VCF must be greater than or equal to 1."
                )

            target_retentate_volume = (
                feed.F_vol / self.VCF
            )

            # Volume already occupied by components with an explicit
            # retentate fraction
            fixed_retentate_volume = retentate.F_vol

            # Initial volume of solvents and solutes following the liquid
            mobile_volume_in = sum(
                feed.ivol[chem]
                for chem in mobile_IDs
            )

            if mobile_volume_in <= 0:
                raise ValueError(
                    f"{self.ID}: no mobile liquid is available "
                    "to satisfy the specified VCF."
                )

            required_mobile_volume = (
                target_retentate_volume
                - fixed_retentate_volume
            )

            mobile_fraction = (
                required_mobile_volume
                / mobile_volume_in
            )

            if mobile_fraction < 0:

                maximum_VCF = (
                    feed.F_vol / fixed_retentate_volume
                    if fixed_retentate_volume > 0
                    else float("inf")
                )

                raise ValueError(
                    f"{self.ID}: target retentate volume "
                    f"({target_retentate_volume:.6g} m3/h) is smaller "
                    f"than the volume occupied by retained components "
                    f"({fixed_retentate_volume:.6g} m3/h). "
                    f"Maximum feasible VCF: {maximum_VCF:.6g}."
                )

            if mobile_fraction > 1:
                raise ValueError(
                    f"{self.ID}: target retentate volume requires "
                    "retaining more mobile liquid than is available. "
                    f"Calculated mobile fraction: "
                    f"{mobile_fraction:.6g}."
                )

        for chem in mobile_IDs:

            retained_mass = (
                mobile_fraction * feed.imass[chem]
            )

            retentate.imass[chem] = retained_mass
            permeate.imass[chem] = (
                feed.imass[chem] - retained_mass
            )

        P_inlet = self._solve_pressure()

        permeate.P = self.permeate_pressure
        retentate.P = (
            P_inlet - self.pressure_drop
        )

        self.pump.P = P_inlet
        self.pump._run()

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

class Diafiltration(AbstractMembraneFiltration):
    """
    """
    def _init(self):
        pass

    def _run(self):
            pass