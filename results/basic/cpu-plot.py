#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 4))

ax1 = plt.subplot(131)
data = read_data('external/resource-usage-cpu.csv')
data = convert_ts_index(smoothen(data))
data.plot(
    title='External Sharder',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='CPU usage in cores',
    xlim=[0, data.index.max()],
    ylim=[0, 1.8],
    kind='area',
    stacked=True,
    ax=ax1,
)
ax1.legend(loc='upper left', fontsize='small')

ax2 = plt.subplot(132, sharex=ax1, sharey=ax1)
data = read_data('internal/resource-usage-cpu.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data.plot(
    title='Internal Sharder',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax2,
)
ax2.legend(loc='upper left', fontsize='small')

ax3 = plt.subplot(133, sharex=ax1, sharey=ax1)
data = read_data('singleton/resource-usage-cpu.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data.plot(
    title='Singleton',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax3,
)
ax3.legend(loc='upper left', fontsize='small')

plt.ylim(bottom=0)
# plt.suptitle('CPU Usage per Pod', weight='bold')
plt.savefig('cpu.pdf', bbox_inches='tight')
plt.savefig('cpu.svg', bbox_inches='tight')
