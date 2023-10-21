#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(10, 5))

ax1 = plt.subplot(121)
data = read_data('5-workers-cpu.csv')
data.plot(
    title='5 Workers',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(122, sharex=ax1, sharey=ax1)
data = read_data('15-workers-cpu.csv')
data.plot(
    title='15 Workers',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)
# plt.suptitle('CPU Usage per Pod', weight='bold')
plt.savefig('cpu.pdf', bbox_inches='tight')
