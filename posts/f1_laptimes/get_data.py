#%%
import fastf1
import pandas as pd
import duckdb
import os

#%%
schedule = fastf1.get_event_schedule(2025)
print(schedule.get(['RoundNumber', 'EventDate', 'Location', 'OfficialEventName']))

race_laps = pd.DataFrame()
for i, event in schedule.iterrows():
  if event['EventFormat'] == 'testing':
    continue
  else:
    event_round = event['RoundNumber']
    session = fastf1.get_session(2025, 1, 'R')
    session.load()
    race_laps = pd.concat([race_laps, session.laps])

#%%
