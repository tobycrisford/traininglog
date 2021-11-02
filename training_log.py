#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 27 10:28:05 2021

@author: tc
"""

import json
import pandas as pd
import datetime
from datetime import timedelta
from flask import Flask, render_template, request
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.colors

list_of_files = ['email_0_summarizedActivities.json','email_1001_summarizedActivities.json']

dfs = []
for f in list_of_files:
    file = open(f,)
    data = json.load(file)
    dfs.append(pd.DataFrame(data[0]['summarizedActivitiesExport']))
df = pd.concat(dfs)
df = df.reset_index()

def total_week_number(d, start):
    day_gap = ((d - start).days)
    first_week_days = 8 - start.isocalendar()[2]
    return math.ceil((1 + day_gap - first_week_days) / 7) + 1

df['datetime'] = df['beginTimestamp'].apply(lambda x: datetime.datetime.fromtimestamp(int(x/1000)))

df['week'] = df['datetime'].apply(lambda x: x.isocalendar()[1])

df['year'] = df['datetime'].apply(lambda x: x.year)

df['weekday'] = df['datetime'].apply(lambda x: x.isocalendar()[2]) - 1

df['year-week'] = [str(df.loc[i,'year']) + '-' + str(df.loc[i,'week']).zfill(2) for i in df.index]

df['total_week_number'] = df['datetime'].apply(lambda x: total_week_number(x.date(), df['datetime'].min().date()))

df['total_day_number'] = df['datetime'].apply(lambda x: (x.date() - df['datetime'].min().date()).days)

df['week_start'] = (df['datetime'] - df['weekday'].apply(lambda x: timedelta(days=x))).apply(lambda x: x.date())

#Some Garmin activities are wrongly duplicated - deal with that here
df = df[~df.duplicated(subset='beginTimestamp',keep='first')]

activities = sorted(list(set(df['activityType'])))

app = Flask(__name__)
print(__name__)

@app.route('/traininglog')
def create_training_log():
    if not (request.args.get('start') is None):
        rows_to_keep = np.array([False for i in range(len(df))])
        for activity in activities:
            rows_to_keep = rows_to_keep | (df['activityType'] == request.args.get(activity))
        df_out = df[rows_to_keep & (df['week_start'] >= datetime.datetime.strptime(request.args.get('start'), '%Y-%m-%d').date()) & \
                    (df['week_start'] <= datetime.datetime.strptime(request.args.get('end'), '%Y-%m-%d').date())].copy()
    else:
        df_out = df[df['activityType'] == '']
        

    
    if request.args.get('measure') == 'distance':
        df_out['output'] = (df['distance'] / 100000) / (1.60934) #Convert from cm to miles
    elif request.args.get('measure') == 'duration':
        df_out['output'] = df['duration'] / (1000*60)
    elif request.args.get('measure') == 'elevation':
        df_out['output'] = df['elevationGain'] / 100.0
        
    
    df_out = df_out.groupby(['year-week','weekday','total_week_number','week_start','total_day_number'])['output'].aggregate(np.sum).reset_index()
    df_out['total_week_number'] = df_out['total_week_number'] - df_out['total_week_number'].min()
    df_out['total_week_number'] = df_out['total_week_number'].max() - df_out['total_week_number'] #Show log going backwards from present
    
    option_values = {'start': sorted(list(set(df['week_start'].astype(str)))),
                     'end': sorted(list(set(df['week_start'].astype(str)))), 'measure': {'distance','duration','elevation'}}
    
    max_val = df_out['output'].max()
    df_out['radius'] = 100 * np.sqrt(df_out['output'] / max_val)
    
    df_out = df_out.sort_values(['total_day_number']).reset_index()
    df_out['moving_average'] = np.array([0 for i in range(len(df_out))])
    ratio = (1/10)**(1/14)
    for i in range(len(df_out)):
        if i == 0:
            df_out['moving_average'].iloc[i] = df_out['output'].iloc[i] * (1-ratio)
        else:
            df_out['moving_average'].iloc[i] = (1-ratio) * df_out['output'].iloc[i] + ratio**(df_out['total_day_number'].iloc[i] - df_out['total_day_number'].iloc[i-1]) * df_out['moving_average'].iloc[i-1]
    
    df_out['moving_average'] = df_out['moving_average'].apply(matplotlib.colors.Normalize(vmin=df_out['moving_average'].min(), vmax=df_out['moving_average'].max()))
    
    def ints_to_string(x):
        s = ''
        for i in x:
            s = s + str(i) + ','
        return s[0:-1]
    df_out['color'] = df_out['moving_average'].apply(lambda x: ints_to_string((np.array(plt.cm.bwr(x)[0:3])*255).round(0).astype(int)))
    
    elapsed_weeks = 1 + df_out['total_week_number'].max() - df_out['total_week_number'].min()
    
    week_totals = df_out.groupby(['week_start','total_week_number'])['output'].aggregate(np.sum).reset_index()
    week_totals['output'] = week_totals['output'].round(1).astype(str)
    
    df_out['output'] = df_out['output'].round(1).astype(str)
    
    return render_template('training_log.html', output = df_out,
                           option_values = option_values, request_args = request.args,
                           elapsed_weeks = elapsed_weeks, week_totals = week_totals,
                           activities = activities)

app.run(debug=True)