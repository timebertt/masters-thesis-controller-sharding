#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(10, 8))

ax1 = plt.subplot(221)
data = read_data('5-workers-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers: Receive Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax1,
)

ax2 = plt.subplot(222, sharex=ax1, sharey=ax1)
data = read_data('5-workers-v1-network_receive.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers v1: Receive Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Receive Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax2,
)

plt.ylim(bottom=0)

ax3 = plt.subplot(223)
data = read_data('5-workers-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers: Transmit Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax3,
)

ax4 = plt.subplot(224, sharex=ax3, sharey=ax3)
data = read_data('5-workers-v1-network_transmit.csv')
data = data / (2 ** 20)
data.plot(
    title='5 Workers v1: Transmit Bandwidth',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='Transmit Bandwidth in MiB/s',
    xlim=[0, data.index.max()],
    ax=ax4,
)

plt.ylim(bottom=0)
# plt.suptitle('Network Bandwidth per Pod', weight='bold')
plt.savefig('network.pdf', bbox_inches='tight')
