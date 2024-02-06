#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from results.common import *

replicas = [1, 2, 3, 4, 5]
queueData = []
reconcileData = []
for i in replicas:
    dir = f'scale-{i}'

    queueData.insert(i, convert_ts_index(read_data_raw(dir+'/controller-slis-latency-queue.csv').set_index('ts')).rename(columns={'value': f'{i} instances'}))
    reconcileData.insert(i, convert_ts_index(read_data_raw(dir+'/controller-slis-latency-reconciliation.csv').set_index('ts')).rename(columns={'value': f'{i} instances'}))

plt.figure(figsize=(15, 5))

ax1 = plt.subplot(121)
data = pd.concat(queueData, axis=1)
data.plot(
    title='Queue latency (P99)',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='seconds',
    xlim=[0, data.index.max()],
    ax=ax1,
)
ax1.legend(loc='upper left')
ax1.set_yscale('log', base=2)
ax1.yaxis.set_major_formatter(ScalarFormatter())
ax1.set_yticks([0, 0.125, 0.25, 0.5, 1, 2, 4, 8, 10])
ax1.plot([0, data.index.max()], [1, 1], 'k--')

ax2 = plt.subplot(122, sharex=ax1)
data = pd.concat(reconcileData, axis=1)
data.plot(
    title='Reconciliation latency (P99)',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='seconds',
    xlim=[0, data.index.max()],
    ax=ax2,
)
ax2.legend(loc='upper left')
ax2.set_yscale('log', base=2)
ax2.yaxis.set_major_formatter(ScalarFormatter())
ax2.set_yticks([0, 0.125, 0.25, 0.5, 1, 2, 4, 8, 10])
ax2.plot([0, data.index.max()], [5, 5], 'k--')

plt.savefig('slis.pdf', bbox_inches='tight')
plt.savefig('slis.svg', bbox_inches='tight')
