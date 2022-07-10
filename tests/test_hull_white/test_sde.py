import matplotlib.pyplot as plt
import numpy as np
import unittest

import models.hull_white.sde as sde
import models.hull_white.zero_coupon_bond as zcbond
import models.hull_white.call as call
import utils.misc as misc


class SDE(unittest.TestCase):

    def test_y_function(self):
        """In the case of both constant speed of mean reversion and
        constant volatility, the y-function has a closed form.
        Proposition 10.1.7, L.B.G. Andersen & V.V. Piterbarg 2010.
        """
        kappa_const = 0.05
        two_kappa = 2 * kappa_const
        vol_const = 0.02
        event_grid = np.arange(0, 30, 2)
        y_analytical = \
            vol_const ** 2 * (1 - np.exp(-two_kappa * event_grid)) / two_kappa
        # Speed of mean reversion strip
        kappa = np.array([np.arange(2), kappa_const * np.ones(2)])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip
        vol = np.array([np.arange(2), vol_const * np.ones(2)])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid (not used)
        forward_rate = 0.02 * np.ones(event_grid.size)
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE object
        hull_white = sde.SDE(kappa, vol, discount_curve, event_grid)
        hull_white.setup_int_grid()
        hull_white.setup_kappa_vol_y()
        for idx, y_numerical in enumerate(hull_white.y_event_grid):
            if idx >= 1:
                diff = abs(y_analytical[idx] - y_numerical) / y_analytical[idx]
                # print("test_y_function: ", idx, y_analytical[idx], diff)
                self.assertTrue(diff < 2.8e-4)

    def test_zero_coupon_bond_pricing(self):
        """Compare analytical and numerical calculation of zero-coupon
        bonds with different maturities.
        """
        event_grid = np.arange(11)
        # Speed of mean reversion strip
        kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([2, 1, 2])])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip
        vol = np.array([np.arange(10),
                        0.01 * np.array([1, 2, 3, 1, 1, 5, 6, 6, 3, 3])])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid
        forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE object
        n_paths = 1000
        hull_white = sde.SDE(kappa, vol, discount_curve, event_grid)
        hull_white.initialization()
        rate, discount = hull_white.paths(0, n_paths, seed=0, antithetic=True)
        # Threshold
        threshold = np.array([1e-10, 4.0e-7, 3e-6, 1e-4, 3e-4,
                              5e-4, 6e-4, 6e-4, 4e-4, 3e-3, 5e-3])
        for event_idx in range(event_grid.size):
            # Analytical result
            price_a = discount_curve.values[event_idx]
            # Monte-Carlo estimate
            price_n = np.sum(discount[event_idx, :]) / n_paths
            price_n *= discount_curve.values[event_idx]
            diff = abs((price_n - price_a) / price_a)
            # print("test_zero_coupon_bond_pricing: ", event_idx, price_a, diff)
            self.assertTrue(abs(diff) < threshold[event_idx])

    def test_coupon_bond_pricing(self):
        """Compare analytical and numerical calculation of 10Y
        coupon bond with yearly coupon frequency.
        """
        coupon = 0.03
        event_grid = np.arange(11)
        # Speed of mean reversion strip
        kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([2, 1, 2])])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip
        vol = np.array([np.arange(10),
                        0.01 * np.array([1, 2, 3, 1, 1, 5, 6, 6, 3, 3])])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid
        forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE object
        n_paths = 10000
        hull_white = sde.SDE(kappa, vol, discount_curve, event_grid)
        hull_white.initialization()
        rate, discount = hull_white.paths(0, n_paths, seed=0, antithetic=True)
        price_a_c = 0
        price_a_p = 0
        price_n_c = 0
        price_n_p = 0
        for event_idx in range(1, event_grid.size):
            discount_a = discount_curve.values[event_idx]
            discount_n = np.sum(discount[event_idx, :]) / n_paths
            discount_n *= discount_curve.values[event_idx]
            # Coupon
            price_a_c += coupon * discount_a
            price_n_c += coupon * discount_n
            # Principal
            if event_idx == event_grid.size - 1:
                price_a_p = discount_a
                price_n_p = discount_n
        diff_c = abs(price_n_c - price_a_c) / price_a_c
        diff_p = abs(price_n_p - price_a_p) / price_a_p
        # print("test_coupon_bond_pricing:", price_a_c, diff_c)
        # print("test_coupon_bond_pricing:", price_a_p, diff_p)
        self.assertTrue(diff_c < 2e-4)
        self.assertTrue(diff_p < 2e-3)

    def test_sde_objects(self):
        """Compare SDE objects for calculation of call options written
        on zero coupon bonds.
        """
        event_grid = np.arange(11)
        # Speed of mean reversion strip -- constant kappa!
        kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([1, 1, 1])])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip -- constant vol!
        vol = np.array([np.arange(10),
                        0.003 * np.array([2, 2, 2, 2, 2, 2, 2, 2, 2, 2])])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid
        forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE objects
        n_paths = 1000
        hw = sde.SDE(kappa, vol, discount_curve, event_grid)
        hw.initialization()
        hw_const = sde.SDEConstant(kappa, vol, discount_curve, event_grid)
        hw_const.initialization()
        # Pseudo rate and discount factors
        rate_pseudo, discount_pseudo = hw.paths(0, n_paths, seed=0)
        rate_pseudo_const, discount_pseudo_const = \
            hw_const.paths(0, n_paths, seed=0)
        # Compare trajectories
        for n in range(n_paths):
            diff_rate = np.abs(rate_pseudo[1:, n] - rate_pseudo_const[1:, n])
            diff_rate = np.abs(diff_rate / rate_pseudo_const[1:, n])
            diff_discount = \
                np.abs(discount_pseudo[1:, n] - discount_pseudo_const[1:, n])
            diff_discount = \
                np.abs(diff_discount / discount_pseudo_const[1:, n])
            # print(n, np.max(diff_rate), np.max(diff_discount))
            self.assertTrue(np.max(diff_rate) < 3e-2)
            self.assertTrue(np.max(diff_discount) < 4e-5)
        # Compare mean and variance of pseudo short rate and discount
        # processes, respectively
        for n in range(1, event_grid.size):
            diff_rate_mean = \
                np.abs((hw.rate_mean[n] - hw_const.rate_mean[n])
                       / hw_const.rate_mean[n])
            diff_rate_variance = \
                np.abs((hw.rate_variance[n] - hw_const.rate_variance[n])
                       / hw_const.rate_variance[n])
            diff_discount_mean = \
                np.abs((hw.discount_mean[n] - hw_const.discount_mean[n])
                       / hw_const.discount_mean[n])
            diff_discount_variance = \
                np.abs((hw.discount_variance[n]
                        - hw_const.discount_variance[n])
                       / hw_const.discount_variance[n])
            diff_covariance = \
                np.abs((hw.covariance[n] - hw_const.covariance[n])
                       / hw_const.covariance[n])
            # print("Rate mean:", n, hw_const.rate_mean[n], diff_rate_mean)
            # print("Rate variance:", n, hw_const.rate_variance[n], diff_rate_variance)
            # print("Discount mean:", n, hw_const.discount_mean[n], diff_discount_mean)
            # print("Discount variance:", n, hw_const.discount_variance[n], diff_discount_variance)
            # print("Covariance:", n, hw_const.covariance[n], diff_covariance)
            self.assertTrue(diff_rate_mean[0] < 1e-10)
            self.assertTrue(diff_rate_mean[1] < 6e-5)
            self.assertTrue(diff_rate_variance < 3e-10)
            self.assertTrue(diff_discount_mean[0] < 3e-5)
            self.assertTrue(diff_discount_mean[1] < 6e-5)
            self.assertTrue(diff_discount_variance < 2e-3)
            self.assertTrue(diff_covariance < 3e-5)

    def test_call_option_pricing_1(self):
        """Compare analytical and numerical calculation of call options
        written on zero coupon bonds. Also compare SDE classes...
        """
        event_grid = np.arange(11)
        # Speed of mean reversion strip -- constant kappa!
        kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([1, 1, 1])])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip -- constant vol!
        vol = np.array([np.arange(10),
                        0.003 * np.array([2, 2, 2, 2, 2, 2, 2, 2, 2, 2])])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid
        forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE objects
        n_paths = 10000
        hw = sde.SDE(kappa, vol, discount_curve, event_grid)
        hw.initialization()
        hw_const = sde.SDEConstant(kappa, vol, discount_curve, event_grid)
        hw_const.initialization()
        # Pseudo rate and discount factors
        rate_pseudo, discount_pseudo = \
            hw.paths(0, n_paths, seed=0, antithetic=True)
        rate_pseudo_const, discount_pseudo_const = \
            hw_const.paths(0, n_paths, seed=0, antithetic=True)
        # Call option
        maturity_idx = event_grid.size - 1
        strike = 0.65
        expiry_idx = 5
        call_1 = call.Call(kappa, vol, discount_curve, event_grid,
                           strike, expiry_idx, maturity_idx)
        # Zero-coupon bond
        bond = \
            zcbond.ZCBond(kappa, vol, discount_curve, event_grid, maturity_idx)
        # Threshold
        threshold = np.array([3e-4, 4e-4, 4e-4, 5e-4, 6e-4,
                              2e-3, 3e-3, 8e-3, 2e-2, 3e-2])
        for s in range(2, 12, 1):
            # New discount curve on event_grid
            spot = 0.001 * s
            forward_rate = spot * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
            discount_curve = np.exp(-forward_rate * event_grid)
            discount_curve = \
                misc.DiscreteFunc("discount curve", event_grid,
                                  discount_curve, interp_scheme="linear")
            # Update discount curves
            call_1.discount_curve = discount_curve
            call_1._zcbond.discount_curve = discount_curve
            bond.discount_curve = discount_curve
            # Call option price, analytical
            call_price_a = call_1.price(0, 0)
            # Call option price, numerical
            discount = discount_pseudo[expiry_idx, :] \
                * discount_curve.values[expiry_idx]
            bond_price = bond.price(rate_pseudo[expiry_idx, :], expiry_idx)
            payoff = np.maximum(bond_price - strike, 0)
            call_price_n = np.sum(discount * payoff) / n_paths
            diff = abs((call_price_a - call_price_n) / call_price_a)
            discount = discount_pseudo_const[expiry_idx, :] \
                * discount_curve.values[expiry_idx]
            bond_price = \
                bond.price(rate_pseudo_const[expiry_idx, :], expiry_idx)
            payoff = np.maximum(bond_price - strike, 0)
            call_price_n_const = np.sum(discount * payoff) / n_paths
            diff_const = \
                abs((call_price_a - call_price_n_const) / call_price_a)
            # print(s, call_price_a, call_price_n, diff, call_price_n_const, diff_const)
            self.assertTrue(diff < threshold[s - 2])
            self.assertTrue(diff_const < threshold[s - 2])

    def test_call_option_pricing_2(self):
        """Compare analytical and numerical calculation of call options
        written on zero coupon bonds.
        """
        event_grid = np.arange(11)
        # Speed of mean reversion strip -- constant kappa!
        kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([1, 1, 1])])
        kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
        # Volatility strip
        vol = np.array([np.arange(10),
                        0.003 * np.array([3, 2, 3, 1, 1, 5, 6, 6, 3, 3])])
        vol = misc.DiscreteFunc("vol", vol[0], vol[1])
        # Discount curve on event_grid
        forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
        discount_curve = np.exp(-forward_rate * event_grid)
        discount_curve = \
            misc.DiscreteFunc("discount curve", event_grid,
                              discount_curve, interp_scheme="linear")
        # SDE objects
        n_paths = 10000
        hw = sde.SDE(kappa, vol, discount_curve, event_grid)
        hw.initialization()
        # Pseudo rate and discount factors
        rate_pseudo, discount_pseudo = \
            hw.paths(0, n_paths, seed=0, antithetic=True)
        # Call option
        maturity_idx = event_grid.size - 1
        strike = 0.65
        expiry_idx = 5
        call_1 = call.Call(kappa, vol, discount_curve, event_grid,
                           strike, expiry_idx, maturity_idx)
        # Zero-coupon bond
        bond = \
            zcbond.ZCBond(kappa, vol, discount_curve, event_grid, maturity_idx)
        # Threshold
        threshold = np.array([5e-4, 6e-4, 7e-4, 8e-4, 2e-3,
                              3e-3, 4e-3, 7e-3, 2e-2, 5e-2])
        for s in range(2, 12, 1):
            # New discount curve on event_grid
            spot = 0.001 * s
            forward_rate = spot * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
            discount_curve = np.exp(-forward_rate * event_grid)
            discount_curve = \
                misc.DiscreteFunc("discount curve", event_grid,
                                  discount_curve, interp_scheme="linear")
            # Update discount curves
            call_1.discount_curve = discount_curve
            call_1._zcbond.discount_curve = discount_curve
            bond.discount_curve = discount_curve
            # Call option price, analytical
            call_price_a = call_1.price(0, 0)
            # Call option price, numerical
            discount = \
                discount_pseudo[expiry_idx, :] * discount_curve.values[expiry_idx]
            bond_price = bond.price(rate_pseudo[expiry_idx, :], expiry_idx)
            payoff = np.maximum(bond_price - strike, 0)
            call_price_n = np.sum(discount * payoff) / n_paths
            diff = abs((call_price_a - call_price_n) / call_price_a)
            # print(s, call_price_a, call_price_n, diff)
            self.assertTrue(diff < threshold[s - 2])


if __name__ == '__main__':

    event_grid = np.arange(11)
    # Spped of mean reversion strip
    kappa = np.array([np.array([2, 3, 7]), 0.01 * np.array([2, 1, 2])])
    kappa = misc.DiscreteFunc("kappa", kappa[0], kappa[1])
    # Volatility strip
    vol = np.array([np.arange(10),
                    0.003 * np.array([3, 2, 3, 1, 1, 5, 6, 6, 3, 3])])
    vol = misc.DiscreteFunc("vol", vol[0], vol[1])
    # Discount curve on event_grid
    forward_rate = 0.02 * np.array([1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6])
    discount_curve = np.exp(-forward_rate * event_grid)
    discount_curve = misc.DiscreteFunc("discount curve", event_grid,
                                       discount_curve, interp_scheme="linear")
    # Plot Monte-Carlo scenarios
    event_grid_plot = 0.01 * np.arange(0, 1001)
    # SDE object
    n_paths = 10
    hull_white = sde.SDE(kappa, vol, discount_curve, event_grid_plot)
    hull_white.initialization()
    rate, discount = hull_white.paths(0, n_paths, seed=0)
    d_curve = discount_curve.interpolation(event_grid_plot)
    for n in range(n_paths):
        plt.plot(event_grid_plot, rate[:, n])
        plt.plot(event_grid_plot, discount[:, n])
        plt.plot(event_grid_plot, discount[:, n] * d_curve)
    plt.show()
