#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 8))

ax1 = plt.subplot(231)
data = read_data('external-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='External Sharder: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax1,
)

ax2 = plt.subplot(232, sharex=ax1, sharey=ax1)
data = read_data('internal-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='Internal Sharder: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax2,
)

ax3 = plt.subplot(233, sharex=ax1, sharey=ax1)
data = read_data('singleton-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='Singleton: Receive Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.2],
    # ylim=[0, data.sum(axis=1).max()*1.2],
    # kind='area',
    # stacked=True,
    ax=ax3,
)

plt.ylim(bottom=0)

ax4 = plt.subplot(234)
data = read_data('external-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='External Sharder: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.7],
    # ylim=[0, data.sum(axis=1).max()*1.7],
    # kind='area',
    # stacked=True,
    ax=ax4,
)

ax5 = plt.subplot(235, sharex=ax4, sharey=ax4)
data = read_data('internal-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='Internal Sharder: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.7],
    # ylim=[0, data.sum(axis=1).max()*1.7],
    # kind='area',
    # stacked=True,
    ax=ax5,
)

ax6 = plt.subplot(236, sharex=ax4, sharey=ax4)
data = read_data('singleton-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='Singleton: Transmit Bandwidth',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ylim=[0, data.values.max()*1.7],
    # ylim=[0, data.sum(axis=1).max()*1.7],
    # kind='area',
    # stacked=True,
    ax=ax6,
)

plt.ylim(bottom=0)
# plt.suptitle('Network Bandwidth per Pod', weight='bold')
plt.savefig('network.pdf', bbox_inches='tight')
