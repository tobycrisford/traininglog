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

df['week_start'] = (df['datetime'] - df['weekday'].apply(lambda x: timedelta(days=x))).apply(lambda x: x.date())

app = Flask(__name__)
print(__name__)

@app.route('/traininglog')
def create_training_log():
    df_out = df[(df['activityType'] == request.args.get('activity')) & \
                (df['week_start'] >= datetime.datetime.strptime(request.args.get('start'), '%Y-%m-%d').date()) & \
                (df['week_start'] <= datetime.datetime.strptime(request.args.get('end'), '%Y-%m-%d').date())].copy()
        

    
    if request.args.get('measure') == 'distance':
        df_out['output'] = (df['distance'] / 100000) / (1.60934) #Convert from cm to miles
    else:
        df_out['output'] = df['duration'] / (1000*60)
        
    
    df_out = df_out.groupby(['year-week','weekday','total_week_number','week_start'])['output'].aggregate(np.sum).reset_index()
    df_out = df_out.sort_values(['year-week','weekday'])
    df_out['total_week_number'] = df_out['total_week_number'] - df_out['total_week_number'].min()
    df_out['total_week_number'] = df_out['total_week_number'].max() - df_out['total_week_number'] #Show log going backwards from present
    
    option_values = {'activity': sorted(list(set(df['activityType']))), 'start': sorted(list(set(df['week_start'].astype(str)))),
                     'end': sorted(list(set(df['week_start'].astype(str)))), 'measure': {'distance','duration'}}
    
    max_val = df_out['output'].max()
    df_out['radius'] = 100 * np.sqrt(df_out['output'] / max_val)
    
    elapsed_weeks = 1 + df_out['total_week_number'].max() - df_out['total_week_number'].min()
    
    week_totals = df_out.groupby(['week_start','total_week_number'])['output'].aggregate(np.sum).reset_index()
    week_totals['output'] = week_totals['output'].round(1).astype(str)
    
    df_out['output'] = df_out['output'].round(1).astype(str)
    
    return render_template('training_log.html', output = df_out,
                           option_values = option_values, request_args = request.args,
                           elapsed_weeks = elapsed_weeks, week_totals = week_totals)

app.run(debug=True)