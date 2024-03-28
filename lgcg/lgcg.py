import numpy as np
import logging
from typing import Callable
from lib.default_values import *
from lib.ssn import SSN

logging.basicConfig(
    level=logging.DEBUG,
)


class LGCG:
    def __init__(
        self,
        M: float,
        y_true: np.ndarray = None,
        K: np.ndarray = None,
        alpha: float = None,
        gamma: float = None,
        L: float = None,
        norm_K_star: float = None,
        Omega: np.ndarray = None,
    ) -> None:
        self.M = M
        self.y_true = y_true if not y_true is None else np.random.rand(5)
        self.K = K if not K is None else get_default_K(self.y_true)
        self.f = get_default_f(self.K, self.y_true)
        self.p = get_default_p(self.K, self.y_true)
        self.alpha = alpha if not alpha is None else 1
        self.g = get_default_g(self.alpha)
        self.gamma = gamma if not gamma is None else 1
        self.L = L if not L is None else 1
        self.norm_K_star = (
            norm_K_star
            if not norm_K_star is None
            else max([np.linalg.norm(row) for row in np.transpose(self.K)])
        )  # the 2,inf norm of the transpose of K
        self.Omega = Omega if not Omega is None else get_default_Omega(self.K)
        self.C = self.L * self.M**2
        self.j = lambda u: self.f(u) + self.g(u)

    def update_epsilon(self, eta: float, epsilon: float) -> float:
        return (self.M * epsilon + 0.5 * self.C * eta**2) / (self.M + self.M * eta)

    def explicit_Phi(self, p: np.ndarray, u: np.ndarray, v: np.ndarray) -> float:
        # <p(u),v-u>+g(u)-g(v)
        return np.matmul(p, v - u) + self.g(u) - self.g(v)

    def Phi(self, p_u: np.ndarray, u: np.ndarray, x: int) -> float:
        # M*max{0,||p_u||-alpha}+g(u)-<p_u,u>
        return (
            self.M * (max(0, np.absolute(p_u[x]) - self.alpha))
            + self.g(u)
            - np.matmul(p_u, u)
        )

    def optimize(self, tol: float) -> dict:
        support = np.array([])
        u = np.zeros(self.K.shape[1])
        p_u = self.p(u)
        x = np.argmax(np.absolute(p_u))
        epsilon = self.j(u) / self.M
        Psi = self.gamma * self.alpha**2 / (4 * self.norm_K_star**2 * self.L**2)
        k = 1
        while self.Phi(p_u, u, x) > tol:
            eta = 4 / (k + 3)
            epsilon = self.update_epsilon(eta, epsilon)
            Psi = min(Psi, self.M * epsilon)
            if x in support:
                support_half = support
                Psi = Psi / 2
            else:
                support_half = np.unique(
                    np.append(support, x).astype(int)
                )  # returns sorted
            v = self.M * np.sign(p_u[x]) * np.eye(1, self.K.shape[1], x)[0]
            if self.explicit_Phi(p=p_u, u=u, v=v) >= self.M * epsilon:
                u = (1 - eta) * u + eta * v
            elif (
                self.explicit_Phi(p=p_u, u=u, v=np.zeros(self.K.shape[1]))
                >= self.M * epsilon
            ):
                u = (1 - eta) * u

            # P_A step
            K_support = self.K[:, support_half]
            ssn = SSN(K=K_support, alpha=self.alpha, y_true=self.y_true, M=self.M)
            u_raw = ssn.solve(tol=Psi, u_0=u[support_half])

            support = support_half[u_raw != 0]
            u = np.zeros(len(u))
            for ind, pos in enumerate(support):
                u[pos] = u_raw[ind]
            p_u = self.p(u)
            x = np.argmax(np.absolute(p_u))
            k += 1
            logging.info(
                f"k:{k},  suppor:{support},  u_raw:{u_raw},  Ku:{np.matmul(self.K,u)}"
            )
