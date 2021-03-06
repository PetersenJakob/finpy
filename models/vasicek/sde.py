import math
import numpy as np
from typing import Tuple

import models.sde as sde
import utils.global_types as global_types
import utils.misc as misc


class SDE(sde.SDE):
    """SDE for the short rate in the Vasicek model
        dr_t = kappa * (mean_rate - r_t) * dt + vol * dW_t

    - kappa: Speed of mean reversion
    - mean_rate: Long-time mean
    - vol: Volatility
    - event_grid: event dates, i.e., trade date, payment dates, etc.
    - int_step_size: Integration/propagation step size
    """

    def __init__(self,
                 kappa: float,
                 mean_rate: float,
                 vol: float,
                 event_grid: np.ndarray,
                 int_step_size: float = 1 / 365):
        self.kappa = kappa
        self.mean_rate = mean_rate
        self.vol = vol
        self.event_grid = event_grid
        self.int_step_size = int_step_size

        self.model_name = global_types.ModelName.VASICEK

        self.rate_mean = np.zeros((self.event_grid.size, 2))
        self.rate_variance = np.zeros(self.event_grid.size)
        self.discount_mean = np.zeros((self.event_grid.size, 2))
        self.discount_variance = np.zeros(self.event_grid.size)
        self.covariance = np.zeros(self.event_grid.size)

    def __repr__(self):
        return f"{self.model_name} SDE object"

    def initialization(self):
        """Initialize the Monte-Carlo engine by calculating mean and
        variance of the short rate and discount processes, respectively.
        """
        self.calc_rate_mean()
        self.calc_rate_variance()
        self.calc_discount_mean()
        self.calc_discount_variance()
        self.calc_covariance()

    def calc_rate_mean(self):
        """Conditional mean of short rate process.
        Eq. (10.12), L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        exp_kappa = np.exp(-self.kappa * np.diff(self.event_grid))
        self.rate_mean[0, 0] = 1
        self.rate_mean[1:, 0] = exp_kappa
        self.rate_mean[1:, 1] = self.mean_rate * (1 - exp_kappa)

    def calc_rate_variance(self):
        """Conditional variance of short rate process.
        Eq. (10.13), L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        two_kappa = 2 * self.kappa
        exp_two_kappa = np.exp(-two_kappa * np.diff(self.event_grid))
        self.rate_variance[1:] = \
            self.vol ** 2 * (1 - exp_two_kappa) / two_kappa

    def rate_increment(self,
                       spot: (float, np.ndarray),
                       time_idx: int,
                       normal_rand: (float, np.ndarray)) \
            -> (float, np.ndarray):
        """Increment short rate process (the spot rate is subtracted to
        get the increment).
        """
        mean = self.rate_mean[time_idx, 0] * spot + self.rate_mean[time_idx, 1]
        variance = self.rate_variance[time_idx]
        return mean + math.sqrt(variance) * normal_rand - spot

    def calc_discount_mean(self):
        """Conditional mean of discount process, i.e.,
        -int_t^{t+dt} r_u du.
        Eq. (10.12+), L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        dt = np.diff(self.event_grid)
        exp_kappa = np.exp(-self.kappa * dt)
        exp_kappa = (1 - exp_kappa) / self.kappa
        self.discount_mean[1:, 0] = -exp_kappa
        self.discount_mean[1:, 1] = self.mean_rate * (exp_kappa - dt)

    def calc_discount_variance(self):
        """Conditional variance of discount process, i.e.,
        -int_t^{t+dt} r_u du.
        Eq. (10.13+), L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        dt = np.diff(self.event_grid)
        vol_sq = self.vol ** 2
        exp_kappa = np.exp(-self.kappa * dt)
        two_kappa = 2 * self.kappa
        exp_two_kappa = np.exp(-two_kappa * dt)
        kappa_cubed = self.kappa ** 3
        self.discount_variance[1:] = \
            vol_sq * (4 * exp_kappa - 3 + two_kappa * dt
                      - exp_two_kappa) / (2 * kappa_cubed)

    def discount_increment(self,
                           rate_spot: (float, np.ndarray),
                           time_idx: int,
                           normal_rand: (float, np.ndarray)) \
            -> (float, np.ndarray):
        """Increment discount process."""
        mean = self.discount_mean[time_idx, 0] * rate_spot \
            + self.discount_mean[time_idx, 1]
        variance = self.discount_variance[time_idx]
        return mean + math.sqrt(variance) * normal_rand

    def calc_covariance(self):
        """Covariance between between short rate and discount processes.
        Lemma 10.1.11, L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        dt = np.diff(self.event_grid)
        vol_sq = self.vol ** 2
        kappa_sq = self.kappa ** 2
        exp_kappa = np.exp(-self.kappa * dt)
        exp_two_kappa = np.exp(-2 * self.kappa * dt)
        self.covariance[1:] = \
            vol_sq * (2 * exp_kappa - exp_two_kappa - 1) / (2 * kappa_sq)

    def correlation(self,
                    time_idx: int) -> float:
        """Correlation between between short rate and discount
        processes.
        """
        covariance = self.covariance[time_idx]
        rate_var = self.rate_variance[time_idx]
        discount_var = self.discount_variance[time_idx]
        return covariance / math.sqrt(rate_var * discount_var)

    def paths(self,
              spot: float,
              n_paths: int,
              seed: int = None,
              antithetic: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        """Generate paths represented on _event_grid of correlated short
        rate and discount processes using exact discretization.

        antithetic : Antithetic sampling for Monte-Carlo variance
        reduction. Defaults to False.
        """
        rate = np.zeros((self.event_grid.size, n_paths))
        rate[0, :] = spot
        discount = np.zeros((self.event_grid.size, n_paths))
        if seed is not None:
            np.random.seed(seed)
        for time_idx in range(1, self.event_grid.size):
            correlation = self.correlation(time_idx)
            x_rate, x_discount = \
                misc.cholesky_2d(correlation, n_paths, antithetic=antithetic)
            rate[time_idx] = rate[time_idx - 1] \
                + self.rate_increment(rate[time_idx - 1], time_idx, x_rate)
            discount[time_idx] = discount[time_idx - 1] \
                + self.discount_increment(rate[time_idx - 1], time_idx,
                                          x_discount)
        # Get discount factors at event dates
        discount = np.exp(discount)
        return rate, discount
