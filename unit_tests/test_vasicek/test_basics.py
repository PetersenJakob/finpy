import matplotlib.pyplot as plt
import numpy as np
import unittest

import models.vasicek.sde as sde
import models.vasicek.call as call
import models.vasicek.put as put
import models.vasicek.zcbond as zcbond
import utils.plots as plots


class SDE(unittest.TestCase):

    def test_getters_and_setters(self):
        """..."""
        kappa = 0.1
        mean_rate = 0.3
        vol = 0.2
        vasicek = sde.SDE(kappa, mean_rate, vol)

        self.assertEqual(vasicek.kappa, kappa)
        self.assertEqual(vasicek.mean_rate, mean_rate)
        self.assertEqual(vasicek.vol, vol)

    def test_zcbond_mc_pricing(self):
        """Test pricing of zero-coupon bond by Monte-Carlo."""
        spot = 0.02
        kappa = 1
        mean_rate = 0.04
        vol = 0.02
        vasicek = sde.SDE(kappa, mean_rate, vol)
        t_max = 10
        n_paths = 100000
        spot_vector = np.arange(-5, 6, 1) * spot
        bond = zcbond.ZCBond(kappa, mean_rate, vol, t_max)
        for s in spot_vector:
            paths = vasicek.path(s, t_max, n_paths)
            numerical = np.sum(np.exp(paths[1])) / n_paths
            analytical = bond.price(s, 0)
            relative_diff = abs((numerical - analytical) / analytical)
            self.assertTrue(relative_diff < 1.0e-3)


if __name__ == '__main__':

    spot = 0.02
    kappa = 1
    mean_rate = 0.02
    vol = 0.05
    vasicek = sde.SDE(kappa, mean_rate, vol)
    t_min = 0
    t_max = 10
    t_steps = 301
    dt = (t_max - t_min) / (t_steps - 1)
    time_grid = dt * np.arange(0, t_steps)
    path = vasicek.path_time_grid(spot, time_grid)
#    plots.plot_path(time_grid, path)

    n_paths = 10000
    spot_vector = np.arange(-5, 6, 1) * spot
    bond = zcbond.ZCBond(kappa, mean_rate, vol, t_max)
    for s in spot_vector:
        paths = vasicek.path(s, t_max, n_paths)
        numerical = np.sum(np.exp(paths[1])) / n_paths
        analytical = bond.price(s, 0)
        space = " "
        if s < 0:
            space = ""
        print("Spot rate: " + space, "{:.3e}".format(s),
              "  Monte-Carlo price: ", "{:.5e}".format(numerical),
              "  Analytical price: ", "{:.5e}".format(analytical),
              "  Relative difference: ",
              "{:.3e}".format(abs((numerical - analytical) / analytical)))

    # Zero-coupon bond
    bond_price_n = spot_vector * 0
    bond_price_a = spot_vector * 0

    # Call option
    strike = 1.3
    expiry = t_max / 2
    call_option = call.Call(kappa, mean_rate, vol, strike, expiry, t_max)
    call_price_n = spot_vector * 0
    call_price_a = spot_vector * 0

    # Put option
    put_option = put.Put(kappa, mean_rate, vol, strike, expiry, t_max)
    put_price_n = spot_vector * 0
    put_price_a = spot_vector * 0

    for idx, s in enumerate(spot_vector):

        bond_price_a[idx] = bond.price(s, 0)
        paths = vasicek.path(s, t_max, n_paths)
        bond_price_n[idx] = np.sum(np.exp(paths[1])) / n_paths

        call_price_a[idx] = call_option.price(s, 0)
        put_price_a[idx] = put_option.price(s, 0)

        paths = vasicek.path(s, expiry, n_paths)
        bond_new = zcbond.ZCBond(kappa, mean_rate, vol, t_max - expiry)

        call_option_values = np.maximum(bond_new.price(paths[0], 0) - strike, 0)
        call_price_n[idx] = np.sum(np.exp(paths[1]) * call_option_values) / n_paths

        put_option_values = np.maximum(strike - bond_new.price(paths[0], 0), 0)
        put_price_n[idx] = np.sum(np.exp(paths[1]) * put_option_values) / n_paths

    plt.plot(spot_vector, bond_price_a, '-b')
    plt.plot(spot_vector, bond_price_n, 'bo')

    plt.plot(spot_vector, call_price_a, '-r')
    plt.plot(spot_vector, call_price_n, 'ro')

    plt.plot(spot_vector, put_price_a, '-g')
    plt.plot(spot_vector, put_price_n, 'go')

    plt.show()

    unittest.main()
