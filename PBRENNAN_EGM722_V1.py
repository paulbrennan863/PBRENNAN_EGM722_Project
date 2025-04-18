#import time
#import boto3
#from datetime import datetime, timezone
#import json
#from os import listdir
#from os.path import isfile, join
#import urllib3
#import requests
import os
import xml.etree.ElementTree as ET
import csv
import numpy as np  # for using pandas
import geopandas as gpd
from shapely.geometry import Point, Polygon
import folium
from folium.plugins import MiniMap

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
#from tkinter.messagebox import showinfo

gui = tk.Tk()
ElementTag = []
ElementText = []
EquipmentIDArray = []
EquipmentLat = []
EquipmentLong = []

xmlfilename = "orbcomm6.xml"

def create_folium_map():
    global m
    m = folium.Map(location=[54.6, -7], zoom_start=9)
    mini_map = MiniMap()
    m.add_child(mini_map)

def select_file():
    global xmlfilename # define the the xmlfile name is the global one to be modified
    filetypes = (('XML files','*.xml'),)
    filename = fd.askopenfilename(title='Open XML file', initialdir='/',filetypes=filetypes)
    # Get just the file name
    filename = os.path.basename(filename) #only use the filename and not the full path
    xmlfilename=filename

    #showinfo(title='Selected File', message=filename)


def printFilename():
    print(xmlfilename)


#create the root window
def CreateGUIframe():

    gui.title('Tkinter Open File Dialog')
    gui.resizable(False, False)
    gui.geometry('300x150')
    gui.attributes('-topmost', True) #make sure the GUI fram is on top to ensure it is seen

def CreateGUIfileopenbutton():
    #open button
    open_button = ttk.Button(
    gui,
    text='Open a AEMP2.0 xml File',
    command=select_file
    )
    open_button.pack(expand=True)

def CreateGUIfileprintoutput():
    #open button
    print_button = ttk.Button(
    gui,
    text='Print Name of xml File',
    command=printFilename
    )
    print_button.pack(expand=True)
#### Main progream starts here ###
create_folium_map()
CreateGUIframe()
CreateGUIfileopenbutton()
CreateGUIfileprintoutput()



# run the application
gui.mainloop()
#import re
#from datetime import date
#from requests.auth import HTTPBasicAuth


#def xml_branch_value_extract(img, pmin=0., pmax=100.):




x#mlfilename = fd.askopenfilename()





xmlscriptFile = open("orbcomm6.xml")
print(xmlscriptFile)
xmlparse = ET.parse(xmlscriptFile)

xmlparse = ET.parse('orbcomm6.xml')
root = xmlparse.getroot()

# Parse the XML file#Iterate over each <Equipment> element in the AEMP XML File
for equipment in root.findall('Equipment'):


    # Find the location data
    equipmentHeader = equipment.find('EquipmentHeader')

    if equipmentHeader is not None:
        OEMname = equipmentHeader.find('OEMName').text
        model = equipmentHeader.find('Model').text
        serialNumber = equipmentHeader.find('EquipmentID').text  # Get the datetime attribute from the <Location> tag

        # Append data to the list
        #data.append({'OEMName': OEMname, 'Model': model, 'SerialNumber': serialNumber})

    # Find the location data
    location = equipment.find('Location')
    if location is not None:
        latitude = location.find('Latitude').text
        longitude = location.find('Longitude').text

    # Find the Engine Running data
    cumulativeoperatinghours = equipment.find('CumulativeOperatingHours')
    if cumulativeoperatinghours is not None:
        hour = cumulativeoperatinghours.find('Hour').text
    else:
        hour = 'Void'# If no value is found in fuel branch the add in void

    # Find the Total fuel used by machine
    fuelused = equipment.find('FuelUsed')
    if fuelused is not None:
        fuelunits = fuelused.find('FuelUnits').text
        fuelconsumed = fuelused.find('FuelConsumed').text
    else:
        fuelunits  = 'Void'  # If no value is found in fuel branch the addin void
        fuelconsumed ='0'  # If no value is found in fuel branch the addin void

    # Calculate the amount of Carbon Dioxide produced by each machine
    Co2_produced = float(fuelconsumed) * 2.68 #Each litre of Diesel produces 2.68kg  of C0S during combusion

    # Append data to the list
    data.append({'OEMName': OEMname, 'Model': model, 'SerialNumber': serialNumber, 'Latitude': latitude, 'Longitude': longitude,'Hour': hour,'FuelConsumed': fuelconsumed, 'Fuel Unit': fuelunits, 'C02 Produced Kg': ("%.2f"%Co2_produced)})
    print(data)


df = gpd.GeoDataFrame(data)


#bedrock=gpd.read_file('Datafiles/NI_250k_bedrock_RCS_D.shp')
bedrock=gpd.read_file('Datafiles/NI_250k_bedrock_RCS_D_clipped.shp')
bedrock.drop(columns=['LEX', 'LEX_D', 'LEX_RCS', 'RCS', 'RCS_X', 'RANK', 'BED_EQ', 'BED_EQ_D', 'MB_EQ', 'MB_EQ_D', 'FM_EQ', 'FM_EQ_D', 'SUBGP_EQ', 'SUBGP_EQ_D', 'GP_EQ', 'GP_EQ_D', 'SUPGP_EQ', 'SUPGP_EQ_D', 'MAX_TIME_D', 'MIN_TIME_D', 'MAX_TIME_Y', 'MIN_TIME_Y', 'MAX_INDEX', 'MIN_INDEX', 'MAX_AGE', 'MIN_AGE', 'MAX_EPOCH', 'MIN_EPOCH', 'MAX_SUBPER', 'MIN_SUBPER', 'MAX_PERIOD', 'MIN_PERIOD', 'MAX_ERA', 'MIN_ERA', 'MAX_EON', 'MIN_EON', 'PREV_NAME', 'BGSTYPE', 'LEX_RCS_I', 'LEX_RCS_D', 'BGSREF', 'BGSREF_LEX', 'BGSREF_FM', 'BGSREF_GP', 'BGSREF_RK', 'SHEET', 'VERSION', 'RELEASED', 'NOM_SCALE', 'NOM_OS_YR', 'NOM_BGS_YR', 'MSLINK', 'LEX_ROCK'], axis=1, inplace=True)
bedrock.to_crs(crs='epsg:4326',inplace=True)
bedrock.rename(columns={"RCS_D" : "Bedrock Type"},inplace=True)




geometry = gpd.points_from_xy(df['Longitude'], df['Latitude'], crs='epsg:4326')



machine_positions = gpd.GeoDataFrame(df[['SerialNumber', 'Model', 'Hour', 'FuelConsumed', 'C02 Produced Kg']], # use the csv data, but only the name/website columns
                            geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']), # set the geometry using points_from_xy
                            crs='epsg:4326') # set the CRS using a text representation of the EPSG code for WGS84 lat/lon



# Perform the spatial join, using 'contains' to find bedrock polygons that contain the machine position point
joined_machine_pos_bedrock = gpd.sjoin(machine_positions, bedrock, predicate='within')





joined_machine_pos_bedrock.drop(columns=['index_right', 'Shape_Leng', 'Shape_Area'], axis=1, inplace=True)


m = joined_machine_pos_bedrock.explore('SerialNumber', marker_type='marker', popup=True, legend=False, color='red')
m = bedrock.explore('Bedrock Type', m=m, cmap='viridis', opacity=0.01, legend=False,)


m.save('map2.html')
m.show_in_browser()










#csvline=[Longitude.text, Latitude.text, Longitude.text]
#csvfile_writer.writerow(csvline)
#csvfile.close()