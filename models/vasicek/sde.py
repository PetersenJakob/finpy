import math
import numpy as np
from scipy.stats import norm

import models.sde as sde
import utils.global_types as global_types


class SDE(sde.SDE):
    """Vasicek SDE:
    dr_t = kappa * ( mean_rate - r_t) * dt + vol * dW_t
    """

    def __init__(self,
                 kappa: float,
                 mean_rate: float,
                 vol: float):
        self._kappa = kappa
        self._mean_rate = mean_rate
        self._vol = vol
        self._model_name = global_types.ModelName.VASICEK

    def __repr__(self):
        return f"{self._model_name} SDE object"

    @property
    def kappa(self) -> float:
        return self._kappa

    @kappa.setter
    def kappa(self, kappa_):
        self._kappa = kappa_

    @property
    def mean_rate(self) -> float:
        return self._mean_rate

    @mean_rate.setter
    def mean_rate(self, mean_rate_):
        self._mean_rate = mean_rate_

    @property
    def vol(self) -> float:
        return self._vol

    @vol.setter
    def vol(self, vol_):
        self._vol = vol_

    @property
    def model_name(self) -> global_types.ModelName:
        return self._model_name

    def mean(self,
             spot: (float, np.ndarray),
             delta_t: float) -> (float, np.ndarray):
        """Conditional mean of stochastic process."""
        exp_kappa = math.exp(- self._kappa * delta_t)
        return spot * exp_kappa + self._mean_rate * (1 - exp_kappa)

    def variance(self,
                 delta_t: (float, np.ndarray)) -> (float, np.ndarray):
        """Conditional variance of stochastic process."""
        two_kappa = 2 * self._kappa
        return \
            self._vol ** 2 * (1 - np.exp(- two_kappa * delta_t)) / two_kappa

    def path(self,
             spot: (float, np.ndarray),
             time: float,
             n_paths: int,
             antithetic: bool = False) -> (float, np.ndarray):
        """Generate paths(s), at t = time, of Ornstein-Uhlenbeck motion
        using analytic expression.

        antithetic : Antithetic sampling for Monte-Carlo variance
        reduction. Defaults to False.
        """
        if antithetic:
            if n_paths % 2 == 1:
                raise ValueError("In antithetic sampling, "
                                 "n_paths should be even.")
            realizations = norm.rvs(size=n_paths // 2)
            realizations = np.append(realizations, -realizations)
        else:
            realizations = norm.rvs(size=n_paths)
        return self.mean(spot, time) \
            + math.sqrt(self.variance(time)) * realizations

    def path_time_grid(self,
                       spot: float,
                       time_grid: np.ndarray) -> np.ndarray:
        """Generate one path, represented on time_grid, of
        Ornstein-Uhlenbeck motion using analytic expression.
        """
        delta_t = time_grid[1:] - time_grid[:-1]
        realizations = norm.rvs(size=delta_t.shape[0])
        realizations = np.sqrt(self.variance(delta_t)) * realizations
        spot_moved = np.zeros(delta_t.shape[0] + 1)
        spot_moved[0] = spot
        for count, e in enumerate(np.column_stack(delta_t, realizations)):
            spot_moved[count + 1] = self.mean(spot_moved[count], e[0]) + e[1]
        return spot_moved
