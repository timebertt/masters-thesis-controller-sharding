#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

replicas = [1, 2, 3, 4, 5]
queueData = []
reconcileData = []
for i in replicas:
    dir = f'scale-{i}'

    queueData.insert(i, convert_ts_index(read_data_raw(dir+'/controller-slis-latency-queue.csv').set_index('ts')).rename(columns={'value': f'{i} instances'}))
    reconcileData.insert(i, convert_ts_index(read_data_raw(dir+'/controller-slis-latency-reconciliation.csv').set_index('ts')).rename(columns={'value': f'{i} instances'}))

plt.figure(figsize=(15, 6))

ax1 = plt.subplot(121)
data = pd.concat(queueData, axis=1)
data.plot(
    title='Queue latency (P99)',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='seconds',
    xlim=[0, data.index.max()],
    ylim=[0, 10.5],
    ax=ax1,
)
ax1.legend(loc='upper left', fontsize='small')
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
    ylim=[0, 10.5],
    ax=ax2,
)
ax2.legend(loc='upper left', fontsize='small')
ax2.plot([0, data.index.max()], [5, 5], 'k--')

plt.savefig('slos.pdf', bbox_inches='tight')
plt.savefig('slos.svg', bbox_inches='tight')
