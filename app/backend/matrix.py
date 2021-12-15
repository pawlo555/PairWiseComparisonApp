from typing import List

import numpy as np
import pandas as pd
from sympy import Matrix

RI = {1: 10**-8, 2: 10**-8, 3: 0.58, 4: 0.9, 5: 1.12, 6: 1.21, 7: 1.32, 8: 1.41, 9: 1.46, 10: 1.49}


class VotingMatrix:
    """
    The idea is to keep data as numpy matrix and if necessary convert them to pandas_frame.
    Format of array is:
      x/y   Movie 1 Movie 2 Movie 3
    Movie 1   1        4       2
    Movie 2   1/4      1      1/2
    Movie 3   1/2     1/2      1
    """

    def __init__(self, names: List[str]):
        self.names = names
        array = np.ones((len(names), len(names)))
        self.matrix = np.diag(array)

    def add_comparison(self, x: int, y: int, value: float):
        assert value != 0, "Value cannot be 0"
        self.matrix[x][y] = value
        self.matrix[y][x] = 1/value

    def calc_ranking(self, method: str = "EVM") -> np.ndarray:
        """
        Calc matrix ranking based on voter preferences
        :param method: Method of ranking calculation EVM or GMM
        :return: np.array of results: 1 - movie1, 2 - movie2
        """
        if method == "EVM":
            return self.__calc_ranking_evm()
        else:
            return self.__calc_ranking_gmm()

    def __calc_ranking_evm(self) -> np.ndarray:
        """
        Calc matrix ranking based on voter preferences
        :return: np.array of results: 1 - movie1, 2 - movie2
        """
        if np.allclose((self.matrix + self.matrix.T) / 2, self.matrix):
            return np.ones(shape=(1, self.matrix.shape[0])) / self.matrix.shape[0]
        if (self.matrix == 0).any():
            self.__feed_empty_values_evm()

        val, vectors = np.linalg.eig(self.matrix)
        max_val = np.max(val)
        vectors = np.real(vectors)
        index = np.where(val == max_val)[0]
        return (vectors[:, index] / np.sum(vectors[:, index])).T

    def __feed_empty_values_evm(self):
        for i in range(self.matrix.shape[0]):
            self.matrix[i, i] = np.count_nonzero(self.matrix[:, i] == 0) + 1

    def __calc_ranking_gmm(self) -> np.ndarray:
        """
        Calc matrix GMM ranking based on voter preferences
        :return: np.array of results: 1 - movie1, 2 - movie2
        """
        if np.any(self.matrix == 0):
            helping = np.copy(self.matrix)
            helping[helping == 0] = 1
            r = np.log(helping)
            r = np.sum(r, axis=-1)
            self.__feed_empty_values_gmm()
            w = np.linalg.solve(self.matrix, r)
            w = np.exp(w)
            return w/np.sum(w)
        else:
            n = self.matrix.shape[-1]
            geometric_average = np.array([np.prod(self.matrix, axis=-1) ** (1 / n)])
            return geometric_average / np.sum(geometric_average)

    def __feed_empty_values_gmm(self):
        matrix = np.zeros(self.matrix.shape)
        matrix[self.matrix == 0] = 1
        for i in range(self.matrix.shape[0]):
            matrix[i, i] = self.matrix.shape[0] - np.count_nonzero(self.matrix[:, i] == 0)
        self.matrix = matrix

    def calc_inconsistency(self, method: str = "EVM") -> np.array:
        n = self.matrix.shape[-1]
        cv = np.matmul(self.matrix, self.calc_ranking(method).T)
        cv_lambda = np.sum(cv)
        ci = (cv_lambda - n) / (n - 1)
        return ci / RI[n]

    def to_dataframe(self) -> pd.DataFrame:
        """
        :return: Returns data frame to display on app
        """
        return pd.DataFrame(data=self.matrix, index=self.names, columns=self.names)

    def get_filled_dataframe(self, filled_df: pd.DataFrame):
        self.matrix = filled_df.to_numpy()

    @staticmethod
    def aggregate_matrices(voting_matrices: List['VotingMatrix']) -> 'VotingMatrix':
        """
        Perform aggregation of matrices using geometric average in order to aggregate different experts
        :param voting_matrices: List of voting matrices
        :return: Aggregated matrix
        """
        matrices = [voting_matrix.matrix for voting_matrix in voting_matrices]
        last_dim = len(matrices)
        matrices = np.stack(matrices, axis=-1)
        matrices = np.power(matrices, 1/last_dim)
        aggregated_matrix = np.prod(matrices, axis=-1)
        voting_matrix = VotingMatrix(voting_matrices[0].names)
        voting_matrix.matrix = aggregated_matrix
        return voting_matrix
