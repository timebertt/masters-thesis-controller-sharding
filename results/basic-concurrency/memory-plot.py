#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(10, 5))

ax1 = plt.subplot(121)
data = read_data('5-workers-memory.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Memory usage in MiB',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(122, sharex=ax1, sharey=ax1)
data = read_data('5-workers-v1-memory.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers v1',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Memory usage in MiB',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)
# plt.suptitle('Memory Usage per Pod', weight='bold')
plt.savefig('memory.pdf', bbox_inches='tight')
