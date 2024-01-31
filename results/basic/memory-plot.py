#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 4))

ax1 = plt.subplot(131)
data = read_data('external/resource-usage-memory.csv')
data = convert_ts_index(smoothen(data))
data = data / (2 ** 20)
data.plot(
    title='External Sharder',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Memory usage in MiB',
    xlim=[0, data.index.max()],
    ylim=[0, 450],
    kind='area',
    stacked=True,
    ax=ax1,
)
ax1.legend(loc='upper left', fontsize='small')

ax2 = plt.subplot(132, sharex=ax1, sharey=ax1)
data = read_data('internal/resource-usage-memory.csv')
data = drop_sharder(data)
data = convert_ts_index(smoothen(data))
data = data / (2 ** 20)
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
data = read_data('singleton/resource-usage-memory.csv')
data = drop_sharder(data)
data = convert_ts_index(smoothen(data))
data = data / (2 ** 20)
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
# plt.suptitle('Memory Usage per Pod', weight='bold')
plt.savefig('memory.pdf', bbox_inches='tight')
plt.savefig('memory.svg', bbox_inches='tight')
