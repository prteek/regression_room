#%%
import fastf1
import pandas as pd
from plotnine import *
import duckdb
import os

#%%
schedule = fastf1.get_event_schedule(2025)
print(schedule.get(['RoundNumber', 'EventDate', 'Location', 'OfficialEventName']))

#%%
session = fastf1.get_session(2025, 7, 'R')
session.load()

print(session.event['EventName'])
print(session.event['EventDate'])
#%%
laps_data = session.laps
ver_nor = (laps_data
            .query("Driver in ('VER', 'NOR')")
            .assign(LapTime = lambda x: x['LapTime'].dt.total_seconds())
            .get(['Driver', 'LapNumber', 'LapTime'])
        )

ver_nor.to_csv(os.path.join('posts', 'f1_laptimes' , 'data', 'sample_laptimes.csv'), index=False)

#%%
