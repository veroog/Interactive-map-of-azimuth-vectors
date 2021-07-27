#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 12 13:25:53 2021

@author: veronica
"""
# Import libraries
import pandas as pd
import numpy as np
import math

import datetime
from datetime import date
from datetime import datetime

from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter
from bokeh.models import CategoricalColorMapper
from bokeh.palettes import Dark2_5
from bokeh.io.doc import curdoc
from bokeh.models import Slider, HoverTool, Select, Button
from bokeh.layouts import widgetbox, row, column
from bokeh.models.widgets import DateRangeSlider, DateSlider

from bokeh.models import ColumnDataSource, Label, LabelSet
from bokeh.tile_providers import get_provider, Vendors

from obspy.clients.fdsn import Client


### ===== Change these parameters: ==== ###
stations = ['PB11', 'PB33', 'PB05', 'PB09'] 
client = Client("IRIS")
network = 'TX' # to download stations info
channel='HH*' # to download stations info
scale= 500 #Establishes a zoom scale for the map. This will also determine proportions for hexbins so that everything looks visually appealing. 
data_start_date = date(2019,11,5) # Date corresponds to the start of your dataset/ - change as needed
title = 'SWS - West Texas' #itle of plot
size = 20 # length of dataset if creating dummy points
### Extend of map
minlat=30.5
maxlat=32.1
minlon=-105
maxlon=-102.7
### =================================== ###


## ** If you already have spreadsheets with SWS results, use following lines: ** ## 
       ##  one spreadsheet for all stations ## 
       ## need to duplicate first entry in spreadsheet - see example ##
#df = pd.read_excel('SWS_Splitting_Results.xlsx')
#df['Date']= df['Date'].apply(lambda x: x.date()) 
#df['latitude']=df['Event Latitude'].astype('float')
#df['longitude']=df['Event Longitude'].astype('float')
#df['angles']=df['phi'].astype('float') 

## Let's create dummy datapoints with Lat/Long and SWS angles.
size = 20 
dates = []
dates.append(data_start_date)
dates.append(data_start_date) # need to start script with 2 entries from same date - (not sure why)
for i in range(2,size):
    days = np.arange(0, 450) #range of days from base_date
    start_date = np.datetime64('2019-11-01')
    random_date = start_date + np.random.choice(days)
    dates.append(random_date)

df = pd.DataFrame(columns=['Date', 'latitude', 'longitude', 'angles', 'Station'])
    
df['Date']= dates
df['Date'] = df['Date'].apply(lambda x: x.date()) 
df['latitude']= np.random.uniform(minlat,maxlat, size = size) #creates lat within our study area.
df['longitude']= np.random.uniform(minlon, maxlon, size = size) #creates long  within our study area.
df['angles'] = np.random.uniform(0,360, size = size)
df["Station"] = np.random.choice(stations, size=size)
phi = df['angles']
phi.reset_index()
    
### Since Bokeh uses coordinate system where horizontal == 0/180 degrees counter-clockwise,
#   we will convert our given angles with following functiosn
def determine_quadrant(angle):
    if angle <= 90:
        return 'I'
    elif angle > 90 and angle <= 180:
        return 'II'
    elif angle > 180 and angle <= 270:
        return 'III'
    elif angle > 270 and angle <= 360:
        return 'IV'
def angle_conversion(angle):
    quadrant = determine_quadrant(angle)
    if quadrant == 'I':
        rotated_angle =  90 - angle
    elif quadrant == 'II':
        rotated_angle = angle + (90 - 2*(angle - 90))
    elif quadrant == 'III':
        rotated_angle = 270 - (angle - 180)
    elif quadrant == 'IV':
        rotated_angle =360+  ( angle + (90 - 2*(angle - 90)) )
    else:
        print(str(angle) + 'Angle value error')
    return rotated_angle

## Add new converted angles to our df. 
for index, row in df.iterrows():
    df.at[index,'converted_angles'] = angle_conversion(row['angles'])


## Define column 'Date' as the index to be able to iterate through it 
df.set_index('Date', inplace=True, drop=True) # set the year column to be the index of the df
df = df.sort_index()
k = 6378137
def wgs84_to_mercator(df, lon, lat):
    """Converts decimal longitude/latitude to Web Mercator format"""
    k = 6378137
    df["x"] = df[lon] * (k * np.pi/180.0)
    df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df

df=wgs84_to_mercator(df,'longitude','latitude')

## Plot parameters
#Establishing a zoom scale for the map.  
x=df['x']
y=df['y']
#The range for the map extents is derived from the lat/lon fields. This way the map is automatically centered on the plot elements.
x_min=int(x.mean() - (scale * 350))
x_max=int(x.mean() + (scale * 350))
y_min=int(y.mean() - (scale * 350))
y_max=int(y.mean() + (scale * 350))

# Create ColumnDataSource: source
    
source = ColumnDataSource(data={
        'xs':df.loc[data_start_date].x,
        'ys':df.loc[data_start_date].y,
        'angles': df.loc[data_start_date].converted_angles,
        'station': df.loc[data_start_date].Station
        })

tile_provider=get_provider(Vendors.CARTODBPOSITRON_RETINA)
#tile_provider=get_provider(Vendors.STAMEN_TERRAIN)
plot=figure(
        title=title,
        match_aspect=True,
        tools='wheel_zoom,pan,reset,save',
        x_range=(x_min, x_max),
        y_range=(y_min, y_max),
        x_axis_type='mercator',
        y_axis_type='mercator',
        width=700)

plot.grid.visible=True

map=plot.add_tile(tile_provider)
map.level='underlay'
plot.xaxis.visible = False
plot.yaxis.visible=False
plot.title.text_font_size="20px"

## Plot Stations. 
for i in stations:
    ### Get station coordinates from Obspy
    sta1 = client.get_stations(network= network, station=i, level="channel",channel=channel)
    net = sta1[0]
    sta = net[0]
    x_station = sta.longitude * (k * np.pi/180.0)
    y_station = np.log(np.tan((90 + sta.latitude) * np.pi/360.0)) * k
    labels = Label(x = x_station,y =  y_station, text = sta.code, x_offset=5, y_offset=5)
    plot.inverted_triangle(x_station, y_station,size=15, color="black", line_width=2)
    plot.add_layout(labels)
    
stations_list = df.Station.unique().tolist()
color_mapper = CategoricalColorMapper(factors=stations_list, palette=Dark2_5)

## Plot and update azimuth lines!
#plot.multi_line('xs', 'ys', source = source,line_width=2, color = 'black')
#plot.xaxis.major_label_orientation = "vertical"
plot.ray('xs','ys',length= 17000,angle='angles', source=source,
       angle_units="deg", color=dict(field='station', transform=color_mapper),
       legend = 'station', line_width=2)
plot.legend.location = 'top_right'

# Make a slider object: slider
def update_plot(attr, old, new):
    # Set the yr name to slider.value and new_data to source.data
   
    date_plot = slider.value
    date_plot = datetime.fromtimestamp(date_plot/1000)
    #date_plot = date_plot/1000.0
    year = int(date_plot.strftime('%Y'))
    month = int(date_plot.strftime('%m'))
    day = int(date_plot.strftime('%d')) 
    endtime = date(year, month, day)
     
    new_data = {'xs':df.loc[date(2019,11,5):endtime].x,
                'ys':df.loc[date(2019,11,5):endtime].y,
                'angles':df.loc[date(2019,11,5):endtime].converted_angles,
                'station': df.loc[date(2019,11,5):endtime].Station
               }
    
    source.data = new_data

   # return date_plot

slider = DateSlider(title="Date Range: ", start=date(2019, 11, 5), end=date(2021, 1, 30), value=date(2019, 11, 5), step=1)
slider.on_change('value', update_plot)  

layout= column(plot, widgetbox(slider))
curdoc().add_root(layout)

#show(plot)
