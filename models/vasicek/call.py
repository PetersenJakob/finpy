import numpy as np
from scipy.stats import norm

import models.vasicek.zcbond as zcbond
import models.vasicek.options as options
import utils.global_types as global_types
import utils.payoffs as payoffs


class Call(options.VanillaOption):
    """European call option written on zero-coupon bond in Vasicek
    model.
    """

    def __init__(self,
                 kappa: float,
                 mean_rate: float,
                 vol: float,
                 strike: float,
                 expiry: float,
                 maturity: float):
        super().__init__(kappa, mean_rate, vol, strike, expiry)
        self._maturity = maturity
        self._option_type = global_types.InstrumentType.EUROPEAN_CALL

    @property
    def option_type(self) -> global_types.InstrumentType:
        return self._option_type

    @property
    def maturity(self) -> float:
        return self._maturity

    @maturity.setter
    def maturity(self,
                 maturity_: float):
        self._maturity = maturity_

    def payoff(self,
               spot: (float, np.ndarray)) -> (float, np.ndarray):
        """Payoff function."""
        return payoffs.call(spot, self.strike)

    def payoff_dds(self,
                   spot: (float, np.ndarray)) -> (float, np.ndarray):
        """1st order partial derivative of payoff function wrt the
        underlying state."""
        return payoffs.binary_cash_call(spot, self.strike)

    def price(self,
              spot: (float, np.ndarray),
              time: float) -> (float, np.ndarray):
        """Price function: Eq. (3.10), D. Brigo & F. Mercurio 2007."""
        zc1 = zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self.expiry)
        zc1_price = zc1.price(spot, time)
        zc2 = \
            zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self._maturity)
        zc2_price = zc2.price(spot, time)
        s_p = options.sigma_p(time, self.expiry, self._maturity,
                              self.kappa, self.vol)
        h = options.h_factor(zc1_price, zc2_price, s_p, self.strike)
        return zc2_price * norm.cdf(h) \
            - self.strike * zc1_price * norm.cdf(h - s_p)

    def delta(self,
              spot: (float, np.ndarray),
              time: float) -> (float, np.ndarray):
        """1st order price sensitivity wrt the underlying state."""
        zc1 = zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self.expiry)
        zc1_price = zc1.price(spot, time)
        zc1_delta = zc1.delta(spot, time)
        zc2 = \
            zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self._maturity)
        zc2_price = zc2.price(spot, time)
        zc2_delta = zc2.delta(spot, time)
        s_p = options.sigma_p(time, self.expiry, self._maturity,
                              self.kappa, self.vol)
        h = options.h_factor(zc1_price, zc2_price, s_p, self.strike)
        dhdr = (zc2_delta / zc2_price - zc1_delta / zc1_price) / s_p
        return zc2_delta * norm.cdf(h) \
            - self.strike * zc1_delta * norm.cdf(h - s_p) \
            + dhdr * (zc2_price * norm.pdf(h)
                      - self.strike * zc1_price * norm.pdf(h - s_p))

    def gamma(self,
              spot: (float, np.ndarray),
              time: float) -> (float, np.ndarray):
        """2st order price sensitivity wrt the underlying state."""
        zc1 = zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self.expiry)
        zc1_price = zc1.price(spot, time)
        zc1_delta = zc1.delta(spot, time)
        zc1_gamma = zc1.gamma(spot, time)
        zc2 = \
            zcbond.ZCBond(self.kappa, self.mean_rate, self.vol, self._maturity)
        zc2_price = zc2.price(spot, time)
        zc2_delta = zc2.delta(spot, time)
        zc2_gamma = zc2.gamma(spot, time)
        s_p = options.sigma_p(time, self.expiry, self._maturity,
                              self.kappa, self.vol)
        h = options.h_factor(zc1_price, zc2_price, s_p, self.strike)
        dhdr = (zc2_delta / zc2_price - zc1_delta / zc1_price) / s_p
        d2hdr2 = (- zc2_delta ** 2 / zc2_price ** 2
                  + zc2_gamma / zc2_price
                  + zc1_delta ** 2 / zc1_price ** 2
                  - zc1_gamma / zc1_price) / s_p
        return (zc2_gamma * norm.cdf(h)
                - self.strike * zc1_gamma * norm.cdf(h - s_p)) \
            + 2 * dhdr * (zc2_delta * norm.pdf(h)
                          - self.strike * zc1_delta * norm.pdf(h - s_p)) \
            + dhdr ** 2 * (- zc2_price * h * norm.pdf(h)
                           + self.strike * zc1_price * h * norm.pdf(h - s_p)) \
            + d2hdr2 * (zc2_price * norm.pdf(h)
                        - self.strike * zc1_price * norm.pdf(h - s_p))

    def theta(self,
              spot: (float, np.ndarray),
              time: float) -> (float, np.ndarray):
        """1st order price sensitivity wrt time."""
        pass
