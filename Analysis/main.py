import matplotlib.pyplot as plt

import json
import numpy as np
from itertools import permutations
from scipy.spatial.distance import euclidean
from dtw import dtw


class TeamComparator:
    def __init__(self, delta=0.05):
        self.delta = delta
        self.epsilon = None
        self.ref_trajectories = []
        self.ref_distances = []  # Store reference pairwise distances
        self.test_distances = []  # Store test vs reference distances

    def _load_team_data(self, filepath):
        """Load and validate team trajectory data from JSON file"""
        with open(filepath) as f:
            data = json.load(f)

        trajectories = data['ep_observations']

        # Ensure each state in trajectories is a dictionary
        processed = []
        for traj in trajectories:
            valid_traj = []
            for state in traj:
                # Unpack state if it's inside a singleton list
                if isinstance(state, list) and len(state) == 1:
                    state = state[0]
                # Validate state structure
                if not isinstance(state, dict) or 'players' not in state:
                    raise ValueError("Invalid state format in trajectory")
                valid_traj.append(state)
            processed.append(valid_traj)

        return processed

    def _state_distance(self, s1, s2):
        """Custom distance metric between two game states"""
        # if len(s1[0]['players']) != len(s2[0]['players']):
        #     return float('inf')

        min_dist = float('inf')
        num_players = len(s1[0]['players'])
        for perm in permutations(range(num_players)):
            current_dist = 0
            for i, j in zip(range(num_players), perm):
                p1 = s1[0]['players'][i]
                p2 = s2[0]['players'][j]

                pos_dist = euclidean(p1['position'], p2['position'])
                ori_dist = euclidean(p1['orientation'], p2['orientation'])

                h1 = p1.get('held_object')
                h2 = p2.get('held_object')
                held_dist = 0
                if (h1 is None) != (h2 is None):
                    held_dist = 1
                elif h1 and h2 and (h1['name'] != h2['name']):
                    held_dist = 1

                current_dist += pos_dist + ori_dist + held_dist

            if current_dist < min_dist:
                min_dist = current_dist

        return min_dist

    def _trajectory_distance(self, t1, t2):
        """Dynamic Time Warping distance between trajectories"""
        alignment = dtw(t1, t2, dist_method=self._state_distance)
        # alignment = dtw(t1, t2, dist=self._state_distance)

        return alignment.distance


    def fit_reference(self, ref_file):
        """Calculate conformance threshold from reference team"""
        self.ref_trajectories = self._load_team_data(ref_file)

        for i in range(3):
            self.ref_trajectories.append(self.ref_trajectories[0])

        # Calculate pairwise distances between reference trajectories
        self.ref_distances = []
        for i in range(len(self.ref_trajectories)):
            for j in range(i + 1, len(self.ref_trajectories)):
                d = self._trajectory_distance(self.ref_trajectories[i], self.ref_trajectories[j])
                self.ref_distances.append(d)

        self.epsilon = np.percentile(self.ref_distances, (1 - self.delta) * 100)
        return self.epsilon

    def compare_team(self, test_file):
        """Compare test team against reference"""
        test_trajectories = self._load_team_data(test_file)
        self.test_distances = []
        alerts = []

        for test_traj in test_trajectories:
            min_dist = min(
                self._trajectory_distance(test_traj, ref_traj)
                for ref_traj in self.ref_trajectories
            )
            self.test_distances.append(min_dist)
            alerts.append(1 if min_dist > self.epsilon else 0)

        return alerts

    def plot_distances(self, save_path=None):
        """Visualize distance distributions and threshold"""
        plt.figure(figsize=(10, 6))

        # Plot reference distances
        plt.hist(self.ref_distances, bins=30, alpha=0.7,
                 label='Reference Team Pairwise Distances')

        # Plot test distances if available
        if self.test_distances:
            plt.hist(self.test_distances, bins=30, alpha=0.7,
                     label='Test Team vs Reference Distances')

        # Add threshold line
        if self.epsilon is not None:
            plt.axvline(self.epsilon, color='red', linestyle='--',
                        label=f'Threshold (ε = {self.epsilon:.2f})')

        plt.xlabel('DTW Distance')
        plt.ylabel('Frequency')
        plt.title('Distance Distribution and Conformance Threshold')
        plt.legend()
        plt.grid(True)

        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()


# Modified Usage Example
if __name__ == "__main__":
    comparator = TeamComparator(delta=0.05)
    epsilon = comparator.fit_reference(
        "Cramped_room/Human-aware PPO agent vs Human Keyboard Input 60 sec Cramped Room.json")

    alerts = comparator.compare_team(
        "Cramped_room/Human-aware PPO agent vs Human-aware PPO agent 60 sec Cramped Room.json")

    # Generate and show the histogram
    comparator.plot_distances()
