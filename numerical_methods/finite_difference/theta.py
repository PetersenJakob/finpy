import numpy as np
from scipy.linalg import solve_banded


class SolverOld:
    """Solve parabolic 1-d PDEs using the theta method:
    - theta = 0: Explicit method
    - theta = 1/2: Crank-Nicolson method (default)
    - theta = 1: Fully implicit method"""

    # todo: Choose boundary conditions

    def __init__(self, xmin, xmax, n, theta=0.5):
        self._xmin = xmin
        self._xmax = xmax
        self._n = n
        self._theta = theta
        self._dx = (xmax - xmin) / (n - 1)

    @property
    def xmin(self):
        return self._xmin

    @property
    def xmax(self):
        return self._xmax

    @property
    def n(self):
        return self._n

    @property
    def theta(self):
        return self._theta

    @theta.setter
    def theta(self, val):
        self._theta = val

    @property
    def dx(self):
        return self._dx

    def x_grid(self):
        return self.dx * np.array(range(self.n)) + self.xmin

    def identity(self,
                 vector: np.ndarray = None) -> np.ndarray:
        """Identity matrix on tri-diagonal form:
        - 1st row: Super-diagonal
        - 2nd row: Diagonal
        - 3rd row: Sub-diagonal
        Construct diagonal element-wise from vector."""
        matrix = np.zeros((3, self.n))
        matrix[1, :] = 1
        if vector is None:
            return matrix
        else:
            matrix[1, :] = vector
            return matrix

    def diag_tridiag(self,
                     diagonal: np.ndarray,
                     tridiagonal: np.ndarray) -> np.ndarray:
        """Product of diagonal and tri-diagonal matrices, both in
        tri-diagonal form."""
        product = np.zeros((3, self.n))
        product[0, 1:] = diagonal[1, :-1] * tridiagonal[0, 1:]
        product[1, :] = diagonal[1, :] * tridiagonal[1, :]
        product[2, :-1] = diagonal[1, 1:] * tridiagonal[2, :-1]
        return product

    def tridiag_vec(self,
                    tridiagonal: np.ndarray,
                    vector: np.ndarray) -> np.ndarray:
        """Product of tri-diagonal matrix and column vector."""
        # Contribution from diagonal
        product = tridiagonal[1, :] * vector
        # Contribution from super-diagonal
        product[:-1] += tridiagonal[0, 1:] * vector[1:]
        # Contribution from sub-diagonal
        product[1:] += tridiagonal[2, :-1] * vector[:-1]
        return product

    def ddx(self) -> np.ndarray:
        """Central difference approximation of 1st order derivative
        operator. At the boundaries, forward/backward difference is
        used."""
        matrix = np.zeros((3, self.n))
        # Central difference
        matrix[0, 2:] = 1
        matrix[2, :-2] = -1
        # Forward difference at xmin
        matrix[0, 1] = 2
        matrix[1, 0] = -2
        # Backward difference at xmax
        matrix[1, -1] = 2
        matrix[2, -2] = -2
        return matrix / (2 * self.dx)

    def vector_ddx(self,
                   vector: np.ndarray) -> np.ndarray:
        """Product of input vector and 1st order derivative operator."""
        return self.diag_tridiag(self.identity(vector), self.ddx())

    def x_ddx(self) -> np.ndarray:
        """Product of space coordinate and its 1st order derivative
        operator."""
#        return self.diag_tridiag(self.identity(self.x_grid()), self.ddx())
        return self.vector_ddx(self.x_grid())

    def d2dx2(self) -> np.ndarray:
        """Finite difference approximation of 2nd order derivative
        operator. At the boundaries, the operator is set equal to
        zero."""
        matrix = np.zeros((3, self.n))
        matrix[0, 2:] = 1
        matrix[1, 1:-1] = -2
        matrix[2, :-2] = 1
        return matrix / self.dx ** 2

    def vector_d2dx2(self,
                     vector: np.ndarray) -> np.ndarray:
        """Product of input vector and 2nd order derivative operator."""
        return self.diag_tridiag(self.identity(vector), self.d2dx2())

    def x2_d2dx2(self) -> np.ndarray:
        """Product of space coordinate squared and its 2nd order
        derivative operator."""
#        return self.diag_tridiag(
#            self.identity(self.x_grid() ** 2), self.d2dx2())
        return self.vector_d2dx2(self.x_grid() ** 2)

    def propagation(self,
                    dt: float,
                    diff_operator: np.ndarray,
                    v_vector: np.ndarray) -> np.ndarray:
        """Propagation of v_vector for one time step dt."""
        lhs = self.identity() - self.theta * dt * diff_operator
        rhs = self.identity() + (1 - self.theta) * dt * diff_operator
        return solve_banded((1, 1), lhs, self.tridiag_vec(rhs, v_vector))


class Solver:
    """Solve parabolic 1-d PDEs.
    The general structure of the PDEs is
    dV/dt + drift * dV/dx + 1/2 * diffusion^2 * dV^2/dx^2 = rate * V
    The numerical solution is determined using the theta method.
        - theta = 0   : Explicit Euler method
        - theta = 1/2 : Crank-Nicolson method (default)
        - theta = 1   : Fully implicit method
    The grid in the spatial dimension is assumed equidistant.
    """

    def __init__(self, xmin, xmax, nstates, theta=0.5):
        self._xmin = xmin
        self._xmax = xmax
        self._nstates = nstates
        self._theta = theta

#        self._dx = (xmax - xmin) / (nstates - 1)
        self._dx = (xmax - xmin) / (nstates - 1 - 2)

        self._drift_vec = None
        self._diffusion_vec = None
        self._rate_vec = None
        self._identity_mat = None
        self._propagator_mat = None
        self._boundary_vec = None

    @property
    def xmin(self):
        return self._xmin

    @property
    def xmax(self):
        return self._xmax

    @property
    def nstates(self):
        return self._nstates

    @property
    def theta(self):
        return self._theta

    @theta.setter
    def theta(self, val: float):
        self._theta = val

    @property
    def dx(self):
        return self._dx

    def grid(self):
        """Equidistant grid between _xmin and _xmax, including both end
        points.
        """
#        return self._dx * np.arange(self._nstates) + self._xmin
        return self._dx * np.arange(-1, self._nstates - 1) + self._xmin
#        n_half = (self._nstates - 1) // 2
#        return self._dx * np.arange(-n_half, n_half + 1, 1)

    def set_up_drift_vec(self, vector):
        """Drift vector defined by the underlying stochastic process."""
        self._drift_vec = vector

    def set_up_diffusion_vec(self, vector):
        """Diffusion vector defined by the underlying stochastic
        process.
        """
        self._diffusion_vec = vector

    def set_up_rate_vec(self, vector):
        """Rate vector defined by the underlying stochastic process."""
        self._rate_vec = vector

    def identity_mat(self):
        """Identity matrix on tri-diagonal form.
            - 1st row: Super-diagonal (not including first element)
            - 2nd row: Diagonal
            - 3rd row: Sub-diagonal (not including last element)
        """

#        self._identity_mat = np.zeros((3, self._nstates))
        self._identity_mat = np.zeros((3, self._nstates - 2))

        self._identity_mat[1, :] = 1

    @staticmethod
    def mat_vec_product(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        """Product of tri-diagonal matrix and column vector."""
        # Contribution from diagonal
        product = matrix[1, :] * vector
        # Contribution from super-diagonal
        product[:-1] += matrix[0, 1:] * vector[1:]
        # Contribution from sub-diagonal
        product[1:] += matrix[2, :-1] * vector[:-1]
        return product

    def initialization(self):
        """Initialization step..."""
        # Set up identity matrix
        self.identity_mat()

    def set_up_propagator(self,
                          dt: float,
                          bc_type: str = "Linearity"):
        """Propagator on tri-diagonal form.
            - 1st row: Super-diagonal (not including first element)
            - 2nd row: Diagonal
            - 3rd row: Sub-diagonal (not including last element)
        """
        diffusion_vec_sq = np.square(self._diffusion_vec)
        dx_sq = self._dx ** 2
        # Super-diagonal, diagonal, and sub-diagonal for interior points
        # Eq. (2.7) - (2.9), L.B.G. Andersen & V.V. Piterbarg 2010
        upper = (self._drift_vec / self._dx + diffusion_vec_sq / dx_sq) / 2
        center = - diffusion_vec_sq / dx_sq - self._rate_vec
        lower = (-self._drift_vec / self._dx + diffusion_vec_sq / dx_sq) / 2


        upper = upper[1:-1]
        center = center[1:-1]
        lower = lower[1:-1]


        # Set up propagator matrix consistent with the solve_banded
        # function (scipy.linalg)
        # Eq. (2.11), L.B.G. Andersen & V.V. Piterbarg 2010

#        self._propagator_mat = np.zeros((3, self._nstates))
        self._propagator_mat = np.zeros((3, self._nstates - 2))

        self._propagator_mat[0, 1:] = upper[:-1]
        self._propagator_mat[1, :] = center
        self._propagator_mat[2, :-1] = lower[1:]

        # Choose Boundary conditions
        k1, k2, km_1, km = self.boundary_conditions(bc_type)

        # 1) Instrument value is assumed linear in the underlying price
        # process, i.e., dV^2/dx^2 = 0
        # Eq. (2.12) - (2.13), L.B.G. Andersen & V.V. Piterbarg 2010
#        self._propagator_mat[1, -1] += 2 * upper[-1]
#        self._propagator_mat[2, -2] += - upper[-1]
#        self._propagator_mat[1, 0] += 2 * lower[0]
#        self._propagator_mat[0, 1] += - lower[0]

        self._propagator_mat[1, -1] += km * upper[-1]
        self._propagator_mat[2, -2] += km_1 * upper[-1]
        self._propagator_mat[1, 0] += k1 * lower[0]
        self._propagator_mat[0, 1] += k2 * lower[0]

        # 2) Boundary conditions are determined by the PDE and
        # forward/backward finite difference approximations of the
        # spatial partial derivatives

        idx_0 = 1

        onemtheta_dt = (1 - self._theta) * dt
        d_term = 1 - onemtheta_dt * self._drift_vec[idx_0] / self._dx \
            + onemtheta_dt * diffusion_vec_sq[idx_0] / (2 * dx_sq) \
            - onemtheta_dt * self._rate_vec[idx_0]
        e_term = onemtheta_dt * self._drift_vec[idx_0] / self._dx \
            - onemtheta_dt * diffusion_vec_sq[idx_0] / dx_sq
        f_term = onemtheta_dt * diffusion_vec_sq[idx_0] / (2 * dx_sq)

        theta_dt = self._theta * dt
        a_term = 1 + theta_dt * self._drift_vec[idx_0] / self._dx \
            - theta_dt * diffusion_vec_sq[idx_0] / (2 * dx_sq) \
            + theta_dt * self._rate_vec[idx_0]
        b_term = - theta_dt * self._drift_vec[idx_0] / self._dx \
            + theta_dt * diffusion_vec_sq[idx_0] / dx_sq
        c_term = - theta_dt * diffusion_vec_sq[idx_0] / (2 * dx_sq)

        idx_m = self._nstates - 2

        # Set up boundary vector
#        self._boundary_vec = np.zeros(self._nstates)
        self._boundary_vec = np.zeros(self._nstates - 2)

    def propagation(self,
                    dt: float,
                    vector: np.ndarray,
                    bc_type: str = "Linearity") -> np.ndarray:
        """Propagation of vector for one time step dt."""
        # Eq. (2.19), L.B.G. Andersen & V.V. Piterbarg 2010
        rhs = self._identity_mat + (1 - self.theta) * dt * self._propagator_mat

#        rhs = self.mat_vec_product(rhs, vector) \
#            + (1 - self._theta) * self._boundary_vec
        rhs = self.mat_vec_product(rhs, vector[1:-1]) \
            + (1 - self._theta) * self._boundary_vec

        # Update self._propagator_mat and self._boundary_vec
        # UPDATE DIFFUSION_VEC, DRIFT_VEC, and RATE_VEC before method call...
        # should correspond to end of time step...
        self.set_up_propagator(dt)

        # Eq. (2.19), L.B.G. Andersen & V.V. Piterbarg 2010
        rhs += self._theta * self._boundary_vec
        lhs = self._identity_mat - self.theta * dt * self._propagator_mat

        vector_out = np.zeros(self._nstates)
        vector_out[1:-1] = solve_banded((1, 1), lhs, rhs)

        k1, k2, km_1, km = self.boundary_conditions(bc_type)

        vector_out[0] = k1 * vector_out[1] + k2 * vector_out[2]
        vector_out[-1] = km * vector_out[-2] + km_1 * vector_out[-3]

#        return solve_banded((1, 1), lhs, rhs)
        return vector_out

    @staticmethod
    def fd_delta(grid: np.ndarray,
                 function: np.ndarray):
        """Delta determined by second order finite differences. Assuming
        equidistant and ascending grid.
        """
        dx = grid[1] - grid[0]
        delta = 0 * function.copy()
        # Central finite difference
        delta[1:-1] = (function[2:] - function[:-2]) / (2 * dx)
        # Forward finite difference
        delta[0] = \
            (-function[2] / 2 + 2 * function[1] - 3 * function[0] / 2) / dx
        # Backward finite difference
        delta[-1] = \
            (function[-3] / 2 - 2 * function[-2] + 3 * function[-1] / 2) / dx
        return delta

    @staticmethod
    def fd_gamma(grid: np.ndarray,
                 function: np.ndarray):
        """Gamma determined by second order finite differences. Assuming
        equidistant and ascending grid.
        """
        dx_sq = (grid[1] - grid[0]) ** 2
        gamma = 0 * function.copy()
        # Central finite difference
        gamma[1:-1] = \
            (function[2:] + function[:-2] - 2 * function[1:-1]) / dx_sq
        # Forward finite difference
        gamma[0] = \
            (-function[3] + 4 * function[2]
             - 5 * function[1] + 2 * function[0]) / dx_sq
        # Backward finite difference
        gamma[-1] = \
            (-function[-4] + 4 * function[-3]
             - 5 * function[-2] + 2 * function[-1]) / dx_sq
        return gamma

    def fd_theta(self,
                 dt: float,
                 function: np.ndarray):
        """Theta determined by central finite difference
        approximation.
        """
        self.set_up_propagator(dt)
        forward = self.propagation(-dt, function)
        backward = self.propagation(dt, function)
        return (forward - backward) / (2 * dt)

    def boundary_conditions(self,
                            bc_type: str):
        """..."""
        if bc_type == "Linearity":
            return 2, -1, -1, 2
        else:
            # PDE determined BCs
            return 2, -1, -1, 2

#    def smoothing(self,
#                  strike,
#                  value,
#                  option_type = "Call"):


class SolverNew:
    """Solve parabolic 1-factor PDEs.
    The general structure of the PDEs is
    dV/dt + drift * dV/dx + 1/2 * diffusion^2 * dV^2/dx^2 = rate * V
    The numerical solution is determined using the theta method.
        - theta = 0   : Explicit Euler method
        - theta = 1/2 : Crank-Nicolson method (default)
        - theta = 1   : Fully implicit method
    The grid in the spatial dimension is assumed equidistant.
    """

    def __init__(self,
                 xmin: float,
                 xmax: float,
                 nstates: int,
                 dt: float,
                 theta: float = 0.5,
                 boundary: str = "Linearity"):
        self._xmin = xmin
        self._xmax = xmax
        self._nstates = nstates + 2
        self._dt = dt
        self._theta = theta
        self._boundary = boundary
        self._dx = (xmax - xmin) / (nstates - 1)
        self._vec_drift = None
        self._vec_diff_sq = None
        self._vec_rate = None
        self._vec_solution = None
        self._mat_identity = None
        self._mat_propagator = None
        self._vec_boundary = None

        self._bc = np.zeros(2)

    @property
    def xmin(self) -> float:
        return self._xmin

    @property
    def xmax(self) -> float:
        return self._xmax

    @property
    def nstates(self) -> int:
        # Remove boundary states
        return self._nstates - 2

    @property
    def dt(self) -> float:
        return self._dt

    @dt.setter
    def dt(self, val: float):
        self._dt = val

    @property
    def theta(self) -> float:
        return self._theta

    @theta.setter
    def theta(self, val: float):
        self._theta = val

    @property
    def boundary(self):
        return self._boundary

    @property
    def dx(self) -> float:
        return self._dx

    def grid(self) -> np.ndarray:
        """Equidistant grid between _xmin and _xmax including both
        points. Two boundary points are added at _xmin - _dx and
        _xmax + _dx.
        """
        return self._dx * np.arange(-1, self._nstates - 1) + self._xmin

    def set_drift(self, drift: np.ndarray):
        """Drift vector defined by the underlying stochastic process."""
        self._vec_drift = drift

    def set_diffusion(self, diffusion: np.ndarray):
        """Squared diffusion vector defined by the underlying stochastic
        process.
        """
        self._vec_diff_sq = np.square(diffusion)

    def set_rate(self, rate: np.ndarray):
        """Rate vector defined by the underlying stochastic process."""
        self._vec_rate = rate

    @property
    def solution(self) -> np.ndarray:
        return self._vec_solution

    @solution.setter
    def solution(self, val: np.ndarray):
        self._vec_solution = val

    def identity_matrix(self):
        """Identity matrix on tri-diagonal form.
            - 1st row: Super-diagonal (not including first element)
            - 2nd row: Diagonal
            - 3rd row: Sub-diagonal (not including last element)
        Used in propagation of interior states.
        """
        self._mat_identity = np.zeros((3, self._nstates - 2))
        self._mat_identity[1, :] = 1

    @staticmethod
    def mat_vec_product(matrix: np.ndarray,
                        vector: np.ndarray) -> np.ndarray:
        """Product of tri-diagonal matrix and column vector."""
        # Contribution from diagonal
        product = matrix[1, :] * vector
        # Contribution from super-diagonal
        product[:-1] += matrix[0, 1:] * vector[1:]
        # Contribution from sub-diagonal
        product[1:] += matrix[2, :-1] * vector[:-1]
        return product

    def initialization(self):
        """Initialization step..."""
        # Set up identity matrix
        self.identity_matrix()

    def set_bc_dt(self):
        """..."""
        d, e, f, d_p, e_p, f_p = self.calc_bc_dt()
        self._bc[0] = \
            d * self._vec_solution[0] \
            + e * self._vec_solution[1] \
            + f * self._vec_solution[2]
        self._bc[-1] = \
            d_p * self._vec_solution[-1] \
            + e_p * self._vec_solution[-2] \
            + f_p * self._vec_solution[-3]

    def set_propagator(self):
        """Propagator on tri-diagonal form.
            - 1st row: Super-diagonal (not including first element)
            - 2nd row: Diagonal
            - 3rd row: Sub-diagonal (not including last element)
        boundary: str
            Choose how to handle boundary conditions
        """
        dx_sq = self._dx ** 2
        # Eq. (2.7) - (2.9), L.B.G. Andersen & V.V. Piterbarg 2010
        upper = (self._vec_drift / self._dx + self._vec_diff_sq / dx_sq) / 2
        center = - self._vec_diff_sq / dx_sq - self._vec_rate
        lower = (-self._vec_drift / self._dx + self._vec_diff_sq / dx_sq) / 2
        # Keep elements for interior states
        upper = upper[1:-1]
        center = center[1:-1]
        lower = lower[1:-1]
        # Set up propagator matrix consistent with the solve_banded
        # function (scipy.linalg)
        # Eq. (2.11), L.B.G. Andersen & V.V. Piterbarg 2010
        self._mat_propagator = np.zeros((3, self._nstates - 2))
        self._mat_propagator[0, 1:] = upper[:-1]
        self._mat_propagator[1, :] = center
        self._mat_propagator[2, :-1] = lower[1:]

        # Boundary conditions
        k1, k2, km_1, km, f1, fm = self.boundary_conditions()

        # Adjust propagator matrix for boundary conditions
        # Eq. (2.12) - (2.13), L.B.G. Andersen & V.V. Piterbarg 2010
        self._mat_propagator[1, -1] += km * upper[-1]
        self._mat_propagator[2, -2] += km_1 * upper[-1]
        self._mat_propagator[1, 0] += k1 * lower[0]
        self._mat_propagator[0, 1] += k2 * lower[0]

        # Set boundary vector
        self._vec_boundary = np.zeros(self._nstates - 2)
        self._vec_boundary[0] = lower[0] * f1
        self._vec_boundary[-1] = upper[-1] * fm

    def propagation(self):
        """Propagation of vector for one time step _dt."""

        self.set_bc_dt()

        # Eq. (2.19), L.B.G. Andersen & V.V. Piterbarg 2010
        rhs = self._mat_identity \
            + (1 - self.theta) * self._dt * self._mat_propagator
        rhs = self.mat_vec_product(rhs, self._vec_solution[1:-1]) \
            + (1 - self._theta) * self._dt * self._vec_boundary

        # Update self._mat_propagator and self._vec_boundary
        # UPDATE VEC_DIFF_SQ, VEC_DRIFT, and VEC_RATE before method call...
        # should correspond to end of time step...
        # Propagator and boundary conditions at time t
        self.set_propagator()

        # Eq. (2.19), L.B.G. Andersen & V.V. Piterbarg 2010
        rhs += self._theta * self._dt * self._vec_boundary
        lhs = self._mat_identity - self.theta * self._dt * self._mat_propagator
        # Solve Eq. (2.19), L.B.G. Andersen & V.V. Piterbarg 2010
        self._vec_solution[1:-1] = solve_banded((1, 1), lhs, rhs)

        # Boundary conditions
        k1, k2, km_1, km, f1, fm = self.boundary_conditions()

        # Eq. (2.12) - (2.13), L.B.G. Andersen & V.V. Piterbarg 2010
        self._vec_solution[0] = \
            k1 * self._vec_solution[1] + k2 * self._vec_solution[2] + f1
        self._vec_solution[-1] = \
            km * self._vec_solution[-2] + km_1 * self._vec_solution[-3] + fm

    def boundary_conditions(self):
        """..."""
        if self._boundary == "Linearity":
            return 2, -1, -1, 2, 0, 0
        elif self._boundary == "PDE":
            a, b, c, a_p, b_p, c_p = self.calc_bc()
            k1 = - b / a
            k2 = - c / a
            f1 = self._bc[0] / a
            km = - b_p / a_p
            km_1 = - c_p / a_p
            fm = self._bc[-1] / a_p
            return k1, k2, km_1, km, f1, fm
        else:
            raise ValueError(f"_boundary can be either \"Linearity\" or \"PDE\": {self._boundary}")

    def calc_bc(self):
        """..."""
        dx_sq = self._dx ** 2
        theta_dt = self._theta * self._dt

        a = 1 + theta_dt * self._vec_drift[0] / self._dx \
            - theta_dt * self._vec_diff_sq[0] / (2 * dx_sq) \
            + theta_dt * self._vec_rate[0]
        b = theta_dt * self._vec_diff_sq[0] / dx_sq \
            - theta_dt * self._vec_drift[0] / self._dx
        c = - theta_dt * self._vec_diff_sq[0] / (2 * dx_sq)

        a_p = 1 - theta_dt * self._vec_drift[-1] / self._dx \
            - theta_dt * self._vec_diff_sq[-1] / (2 * dx_sq) \
            + theta_dt * self._vec_rate[-1]
        b_p = theta_dt * self._vec_diff_sq[-1] / dx_sq \
            + theta_dt * self._vec_drift[-1] / self._dx
        c_p = - theta_dt * self._vec_diff_sq[-1] / (2 * dx_sq)

        return a, b, c, a_p, b_p, c_p

    def calc_bc_dt(self):
        """..."""
        dx_sq = self._dx ** 2
        theta_dt = (1 - self._theta) * self._dt

        d = 1 - theta_dt * self._vec_drift[0] / self._dx \
            + theta_dt * self._vec_diff_sq[0] / (2 * dx_sq) \
            - theta_dt * self._vec_rate[0]
        e = - theta_dt * self._vec_diff_sq[0] / dx_sq \
            + theta_dt * self._vec_drift[0] / self._dx
        f = theta_dt * self._vec_diff_sq[0] / (2 * dx_sq)

        d_p = 1 + theta_dt * self._vec_drift[-1] / self._dx \
            + theta_dt * self._vec_diff_sq[-1] / (2 * dx_sq) \
            - theta_dt * self._vec_rate[-1]
        e_p = - theta_dt * self._vec_diff_sq[-1] / dx_sq \
            - theta_dt * self._vec_drift[-1] / self._dx
        f_p = theta_dt * self._vec_diff_sq[-1] / (2 * dx_sq)

        return d, e, f, d_p, e_p, f_p

    def delta_fd(self) -> np.ndarray:
        """Delta calculated by second order finite differences. Assuming
        equidistant and ascending grid.
        """
        delta = np.zeros(self._nstates)
        # Central finite difference
        delta[1:-1] = (self._vec_solution[2:]
                       - self._vec_solution[:-2]) / (2 * self._dx)
        # Forward finite difference
        delta[0] = (- self._vec_solution[2] / 2
                    + 2 * self._vec_solution[1]
                    - 3 * self._vec_solution[0] / 2) / self._dx
        # Backward finite difference
        delta[-1] = (self._vec_solution[-3] / 2
                     - 2 * self._vec_solution[-2]
                     + 3 * self._vec_solution[-1] / 2) / self._dx
        return delta

    def gamma_fd(self) -> np.ndarray:
        """Gamma calculated by second order finite differences. Assuming
        equidistant and ascending grid.
        """
        dx_sq = self._dx ** 2
        gamma = np.zeros(self._nstates)
        # Central finite difference
        gamma[1:-1] = (self._vec_solution[2:]
                       + self._vec_solution[:-2]
                       - 2 * self._vec_solution[1:-1]) / dx_sq
        # Forward finite difference
        gamma[0] = (- self._vec_solution[3]
                    + 4 * self._vec_solution[2]
                    - 5 * self._vec_solution[1]
                    + 2 * self._vec_solution[0]) / dx_sq
        # Backward finite difference
        gamma[-1] = (- self._vec_solution[-4]
                     + 4 * self._vec_solution[-3]
                     - 5 * self._vec_solution[-2]
                     + 2 * self._vec_solution[-1]) / dx_sq
        return gamma

    def theta_fd(self) -> np.ndarray:
        """Theta calculated by central finite difference."""
        self.set_propagator()
        # Save current solution
        solution_copy = self.solution.copy()
        # Forward propagation
        self._dt = - self._dt
        self.propagation()
        forward = self.solution.copy()
        # Backward propagation (two time steps)
        self._dt = - self._dt
        self.propagation()
        self.propagation()
        backward = self.solution.copy()
        # Restore current solution
        self.solution = solution_copy

        return (forward - backward) / (2 * self._dt)
