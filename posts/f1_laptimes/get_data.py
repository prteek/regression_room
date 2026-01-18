#%%
import fastf1
import pandas as pd
import duckdb
import os

#%%
schedule = fastf1.get_event_schedule(2025)
print(schedule.get(['RoundNumber', 'EventDate', 'Location', 'OfficialEventName']))

session_type = 'Race'
season_laps = pd.DataFrame()
for i, event in schedule.iterrows():
  if event['EventFormat'] == 'testing':
    continue
  else:
    session = fastf1.get_session(2025, event['RoundNumber'], session_type)
    session.load()
    event_session_laps = (session
                    .laps
                    .assign(
                        RoundNumber=event['RoundNumber']
                        , Location=event['Location']
                        , EventName=event['EventName']
                        , EventFormat=event['EventFormat']
                        , EventDate=event['EventDate'].date()
                        , SessionType=session_type
                        )
                    .reset_index(drop=True)
    )
    season_laps = pd.concat([season_laps, event_session_laps]).reset_index(drop=True)

#%%

season_laps.to_csv(os.path.join(
    'posts',
    'f1_laptimes',
  'data',
  f'season_{session_type.lower()}.csv'), index=False)

#%%
