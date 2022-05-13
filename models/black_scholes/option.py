import abc
import numpy as np
from typing import Tuple

import models.black_scholes.sde as sde
import instruments.options as options


class VanillaOption(options.VanillaOption, sde.SDE):
    """Vanilla option in Black-Scholes model."""

    def __init__(self,
                 rate: float,
                 vol: float,
                 strike: float,
                 expiry: float,
                 dividend: float = 0):
        super().__init__(rate, vol, dividend)
        self._strike = strike
        self._expiry = expiry

    @property
    @abc.abstractmethod
    def option_type(self) -> str:
        pass

    @property
    def strike(self) -> float:
        return self._strike

    @strike.setter
    def strike(self, strike_):
        self._strike = strike_

    @property
    def expiry(self) -> float:
        return self._expiry

    @expiry.setter
    def expiry(self, expiry_):
        self._expiry = expiry_

    @abc.abstractmethod
    def payoff(self,
               state: (float, np.ndarray)) -> (float, np.ndarray):
        """Payoff function."""
        pass

    @abc.abstractmethod
    def payoff_dds(self,
                   state: (float, np.ndarray)) -> (float, np.ndarray):
        """1st order partial derivative of payoff function wrt the
        underlying state."""
        pass

    @abc.abstractmethod
    def price(self,
              spot: (float, np.ndarray),
              time: float) -> (float, np.ndarray):
        """Price function."""
        pass

    def d1d2(self,
             spot: (float, np.ndarray),
             time: (float, np.ndarray)) \
            -> (Tuple[float, float], Tuple[np.ndarray, np.ndarray]):
        """Factors in Black-Scholes formula.
        - Returns Tuple[float, float] if spot and time are floats
        - Returns Tuple[np.ndarray, np.ndarray] if only spot is a float
        - Returns Tuple[np.ndarray, np.ndarray] if only time is a float
        - Doesn't work if both spot and time are np.ndarrays
        """
        d1 = np.log(spot / self._strike) \
            + (self.rate - self.dividend + self.vol ** 2 / 2) \
            * (self._expiry - time)
        d1 /= self.vol * np.sqrt(self._expiry - time)
        return d1, d1 - self.vol * np.sqrt(self._expiry - time)
