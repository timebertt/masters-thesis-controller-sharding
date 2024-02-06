#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join('..', '..'))

import matplotlib.pyplot as plt
from results.common import *

replicas = [1, 2, 3, 4, 5]
maxCount = []
maxChurn = []
for i in replicas:
    dir = f'scale-{i}'

    dataCount = convert_ts_index(read_data_raw(dir+'/controller-load-website-count.csv').set_index('ts'))
    dataChurn = convert_ts_index(read_data_raw(dir+'/controller-load-website-churn.csv').pivot(index='ts', columns=['controller'], values='value')).sum(axis=1)

    # calculate max time when cumulative SLIs are still below SLOs
    maxTimestamp = min(
        (convert_ts_index(read_data_raw(dir+'/controller-slis-latency-queue.csv').set_index('ts'))['value'] <= 1)[::-1].idxmax(),
        (convert_ts_index(read_data_raw(dir+'/controller-slis-latency-reconciliation.csv').set_index('ts'))['value'] <= 5)[::-1].idxmax(),
    )
    maxCount.insert(i-1, dataCount.loc[maxTimestamp].value)
    maxChurn.insert(i-1, dataChurn.loc[maxTimestamp])

fig, ax1 = plt.subplots(figsize=(8, 5))
lineCount, = ax1.plot(replicas, maxCount, label='count capacity', color='blue', marker='o', linestyle='--')
ax1.set_xlabel('Instances')
ax1.set_xticks(replicas)
ax1.grid(True)
ax1.set_ylabel('count')
ax1.tick_params(axis='y', labelcolor='blue')

ax2 = ax1.twinx()
lineChurn, = ax2.plot(replicas, maxChurn, label='churn capacity', color='green', marker='s', linestyle='--')
ax2.set_ylabel('ops/s')
ax2.tick_params(axis='y', labelcolor='green')

# combine labels from both axes
lines = [lineCount, lineChurn]
fig.legend(lines, [line.get_label() for line in lines], loc='upper left', bbox_to_anchor=(0.13, 0.87))

plt.savefig('capacity.pdf', bbox_inches='tight')
plt.savefig('capacity.svg', bbox_inches='tight')
