import abc
import math

import instruments.bonds as bonds
import models.cox_ingersoll_ross.sde as sde


class Bond(bonds.Bond, sde.SDE):
    """Bond class in CIR model."""

    def __init__(self,
                 kappa: float,
                 mean_rate: float,
                 vol: float,
                 event_grid: np.ndarray,
                 maturity_idx: int):
        super().__init__(kappa, mean_rate, vol, event_grid)
        self._maturity_idx = maturity_idx

    @property
    @abc.abstractmethod
    def bond_type(self):
        pass

    @property
    def maturity(self) -> float:
        return self.event_grid[self._maturity_idx]

    @property
    def maturity_idx(self) -> int:
        return self._maturity_idx

    @maturity_idx.setter
    def maturity_idx(self,
                     maturity_idx_: int):
        self._maturity_idx = maturity_idx_


def a_factor(time1: float,
             time2: float,
             kappa: float,
             mean_rate: float,
             vol: float) -> float:
    """Eq. (3.25), Brigo & Mercurio 2007."""
    h = math.sqrt(kappa ** 2 + 2 * vol ** 2)
    exp_kappa_h = math.exp((kappa + h) * (time2 - time1) / 2)
    exp_h = math.exp(h * (time2 - time1))
    exponent = 2 * kappa * mean_rate / vol ** 2
    return exponent \
        * math.log(2 * h * exp_kappa_h / (2 * h + (kappa + h) * (exp_h - 1)))


def b_factor(time1: float,
             time2: float,
             kappa: float,
             vol: float) -> float:
    """Eq. (3.25), Brigo & Mercurio 2007."""
    h = math.sqrt(kappa ** 2 + 2 * vol ** 2)
    exp_h = math.exp(h * (time2 - time1))
    return 2 * (exp_h - 1) / (2 * h + (kappa + h) * (exp_h - 1))


def dadt(time1: float,
         time2: float,
         kappa: float,
         mean_rate: float,
         vol: float) -> float:
    """Time derivative of A: Eq. (3.25), Brigo & Mercurio 2007."""
    h = math.sqrt(kappa ** 2 + 2 * vol ** 2)
    exp_kappa_h = math.exp((kappa + h) * (time2 - time1) / 2)
    exp_h = math.exp(h * (time2 - time1))
    exponent = 2 * kappa * mean_rate / vol ** 2
    return (exponent / math.exp(a_factor(time1, time2, kappa, mean_rate, vol) / exponent)) \
        * (- h * (kappa + h) * exp_kappa_h / (2 * h + (kappa + h) * (exp_h - 1))
           + 2 * h ** 2 * (kappa + h) * exp_h * exp_kappa_h / (2 * h + (kappa + h) * (exp_h - 1)) ** 2)


def dbdt(time1: float,
         time2: float,
         kappa: float,
         vol: float) -> float:
    """Time derivative of B: Eq. (3.25), Brigo & Mercurio 2007."""
    h = math.sqrt(kappa ** 2 + 2 * vol ** 2)
    exp_h = math.exp(h * (time2 - time1))
    return - 2 * h * exp_h / (2 * h + (kappa + h) * (exp_h - 1)) \
        + 2 * (exp_h - 1) * h * (kappa + h) * exp_h \
        / (2 * h + (kappa + h) * (exp_h - 1)) ** 2
