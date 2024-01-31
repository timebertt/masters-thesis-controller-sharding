#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 8))

ax1 = plt.subplot(231)
data = read_data('external/resource-usage-network_receive.csv')
data = convert_ts_index(smoothen(data))
data = data / (2 ** 20)
data.plot(
    title='External Sharder: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, 12],
    kind='area',
    stacked=True,
    ax=ax1,
)
ax1.legend(loc='upper left', fontsize='small')

ax2 = plt.subplot(232, sharex=ax1, sharey=ax1)
data = read_data('internal/resource-usage-network_receive.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data = data / (2 ** 20)
data.plot(
    title='Internal Sharder: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax2,
)
ax2.legend(loc='upper left', fontsize='small')

ax3 = plt.subplot(233, sharex=ax1, sharey=ax1)
data = read_data('singleton/resource-usage-network_receive.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data = data / (2 ** 20)
data.plot(
    title='Singleton: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax3,
)
ax3.legend(loc='upper left', fontsize='small')

plt.ylim(bottom=0)

ax4 = plt.subplot(234)
data = read_data('external/resource-usage-network_transmit.csv')
data = convert_ts_index(smoothen(data))
data = data / (2 ** 20)
data.plot(
    title='External Sharder: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, 12],
    kind='area',
    stacked=True,
    ax=ax4,
)
ax4.legend(loc='upper left', fontsize='small')

ax5 = plt.subplot(235, sharex=ax4, sharey=ax4)
data = read_data('internal/resource-usage-network_transmit.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data = data / (2 ** 20)
data.plot(
    title='Internal Sharder: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax5,
)
ax5.legend(loc='upper left', fontsize='small')

ax6 = plt.subplot(236, sharex=ax4, sharey=ax4)
data = read_data('singleton/resource-usage-network_transmit.csv')
data = convert_ts_index(smoothen(data))
data = drop_sharder(data)
data = data / (2 ** 20)
data.plot(
    title='Singleton: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    kind='area',
    stacked=True,
    ax=ax6,
)
ax6.legend(loc='upper left', fontsize='small')

plt.ylim(bottom=0)
# plt.suptitle('Network Bandwidth per Pod', weight='bold')
plt.savefig('network.pdf', bbox_inches='tight')
plt.savefig('network.svg', bbox_inches='tight')
