#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

plt.figure(figsize=(15, 3))

ax1 = plt.subplot(121)
data = read_data_raw('external/controller-load-website-count.csv').set_index('ts')
data = convert_ts_index(data)
data.plot(
    title='Website Count',
    legend=False,
    grid=True,
    xlabel='Time in seconds',
    ylabel='count',
    xlim=[0, data.index.max()],
    kind='area',
    stacked=True,
    ax=ax1,
)

ax2 = plt.subplot(122)
data = read_data_raw('external/controller-load-website-churn.csv').pivot(index='ts', columns=['controller'], values='value')
data = convert_ts_index(data)
data = drop_sharder(data)
data.plot(
    title='Website Churn',
    legend=True,
    grid=True,
    xlabel='Time in seconds',
    ylabel='ops/s',
    xlim=[0, data.index.max()],
    kind='area',
    stacked=True,
    ax=ax2,
)
ax2.legend(loc='upper left', fontsize='small')

plt.ylim(bottom=0)
plt.savefig('load.pdf', bbox_inches='tight')
plt.savefig('load.svg', bbox_inches='tight')
