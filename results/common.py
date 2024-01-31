import pandas as pd

def read_data(filename):
    data = read_data_raw(filename)

    # pivot to get one column per pod with timestamp index
    data = data.pivot(index='ts', columns=['pod'], values='value').dropna(axis=1, how='any')

    # sort columns by their max value (useful for stacked area plots)
    data = data[data.max().sort_values().index]

    return data

def read_data_raw(filename):
    data = pd.read_csv(
        filename,
        parse_dates=['ts'],
        date_parser=lambda col: pd.to_datetime(col, utc=True, unit='s'),
    )

    # calculate relative timestamps (need to be converted to float before plotting via convert_ts_index)
    ts_min = data.ts.min()
    data.ts = (data.ts - ts_min)

    return data

def drop_sharder(data):
    return data[[ x for x in data.columns if not x.startswith('sharder-') ]]

def smoothen(data):
    return data.resample('5s').asfreq().interpolate(method='cubic').applymap(lambda x: max(0, x))

def convert_ts_index(data):
    data.index = data.index.astype('timedelta64[s]')
    return data
