#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 5))

ax1 = plt.subplot(131)
data = read_data('external-cpu.csv')
data.plot(
    title='External Sharder',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax1,
)

ax2 = plt.subplot(132, sharex=ax1, sharey=ax1)
data = read_data('internal-cpu.csv')
data.plot(
    title='Internal Sharder',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax2,
)

ax3 = plt.subplot(133, sharex=ax1, sharey=ax1)
data = read_data('singleton-cpu.csv')
data.plot(
    title='Singleton',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax3,
)

plt.ylim(bottom=0)
# plt.suptitle('CPU Usage per Pod', weight='bold')
plt.savefig('cpu.pdf', bbox_inches='tight')
