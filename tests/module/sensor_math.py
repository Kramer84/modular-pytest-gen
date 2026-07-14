import numpy as np


def calculate_velocity_profile(raw_data, smoothing_factor=0.5):
    if len(raw_data) == 0:
        return np.array([])
    data_array = np.array(raw_data)
    smoothed = data_array * smoothing_factor
    velocity = np.gradient(smoothed)
    return velocity
