from biosteam import Model
from biosteam.evaluation._utils import var_columns, var_indices, indices_to_multiindex
from warnings import warn
import numpy as np
import pandas as pd

class ExtendedModel(Model):
    """"""
    def __init__(
        self, 
        system, 
        indicators=None, 
        specification=None, 
        parameters=None, 
        retry_evaluation=None, 
        exception_hook=None
    ):
        super().__init__(
            system, 
            indicators, 
            specification, 
            parameters, 
            retry_evaluation, 
            exception_hook
        )

    def standardised_regression_coefficients(
        self,
        parameters = None,
        indicators = None,
        filter = None,
        tol = 1e-12,
        return_r2 = False,
    ):
        """"""
        pass