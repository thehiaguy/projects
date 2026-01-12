import matplotlib.pyplot as plt
import numpy as np

# Define the vectors
vectors = {
    'u': np.array([3, 2]),
    'v': np.array([2, 3]),
    '-v': np.array([-2, -3]),
    '-2v': np.array([-4, -6]),
    'u+v': np.array([5, 5]),
    'u-v': np.array([1, -1]),
    'u-2v': np.array([-1, -4])
}

# Set up the plot
fig, ax = plt.subplots(figsize=(8, 8))

# Plot each vector as an arrow starting from (0,0)
colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'cyan']
for (name, vec), color in zip(vectors.items(), colors):
    ax.quiver(0, 0, vec[0], vec[1], angles='xy', scale_units='xy', scale=1, color=color, label=name)
    # Add a text label at the tip of the arrow
    ax.text(vec[0] + 0.2, vec[1] + 0.2, name, fontsize=12, color=color, weight='bold')

# Set chart limits and grid
ax.set_xlim(-6, 7)
ax.set_ylim(-7, 7)
ax.axhline(0, color='black', linewidth=1)
ax.axvline(0, color='black', linewidth=1)
ax.grid(True, linestyle='--', alpha=0.6)
ax.set_aspect('equal')
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_title('Exercise 4: Vector Plot')
ax.legend()

plt.show()