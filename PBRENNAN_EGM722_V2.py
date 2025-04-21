import os
import xml.etree.ElementTree as ET
import csv
import numpy as np  # for using pandas
import geopandas as gpd
from shapely.geometry import Point, Polygon
import folium
from folium.plugins import MiniMap
import webbrowser

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
import tkinter.messagebox as mb

# define global variables and instances that are used throughout the program in different functions
gui = tk.Tk() #define the tkinter main GUI frame instance
xmlfilename = "" #preload with xml test filename
machine_data = []  # global list for parsed xml data



def create_folium_map():
    global m # let function know it is the global map instance being called
    m = folium.Map(location=[54.6, -7], zoom_start=9) # centre the map around Northern Ireland
    mini_map = MiniMap()
    m.add_child(mini_map)

def select_file_to_open():
    global xmlfilename # define the  xmlfile name as the global one to be modified
    filetypes = (('XML files','*.xml'),)
    filename = fd.askopenfilename(title='Open XML file', initialdir='/',filetypes=filetypes)
    # Get just the file name and drop the extension
    filename = os.path.basename(filename) #only use the filename and not the full path

    # call XML Parse function to read the machine data
    xml_pasrse(filename)
    load_bedrock_shapefile()




def save_dataframe_as_csv(dfcsv):
    filetypes = (('CSV files', '*.csv'),)
    filename = fd.asksaveasfilename(title='Save DataFrame as CSV', initialdir='/', defaultextension=".csv",filetypes=filetypes)

    if filename:
        # Drop geometry column for writing to CSV file as we have columns for Lat & Long already
        dfcsv = joined_machine_pos_bedrock.drop(columns='geometry', errors='ignore')
        dfcsv.to_csv(filename, index=False)



#write the machine dataframe to the GUI frame
def WriteDataframetoGUI(machinedataframe, joined_machine_pos_bedrock):
    # Drop geometry column for display as we have columns for Lat & Long already
    dfgui = joined_machine_pos_bedrock.drop(columns='geometry', errors='ignore')

    # adjust the style values to making headings bold and left justified
    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Arial', 10, 'bold'), anchor='w')  # 'w' = (west) left-justify

    tree = ttk.Treeview(machinedataframe, columns=list(dfgui.columns), show='headings')

    # Add column headers
    for col in dfgui.columns:
        tree.heading(col, text=col, anchor='w')
        tree.column(col, width=150)

    for _, row in dfgui.iterrows():
        tree.insert("", "end", values=list(row))

    #tree.pack(fill='both', expand=True)
    tree.place(x=10, y=50, height=220, width=1450)




#create the main GUI window
def CreateGUIframe():

    gui.title('AEMP 2.0 Machine Viewer')
    gui.resizable(False, False)
    gui.geometry('1500x300')
    gui.attributes('-topmost', True) #make sure the GUI fram is on top to ensure it is seen

    machinedataframe=tk.Frame(gui,borderwidth=2, relief=tk.RIDGE)
    machinedataframe.place(x=10, y=50, height=220, width=1450)





def CreateGUIfileopenbutton():
    #open button
    open_button = ttk.Button(
    gui,
    text='Open a AEMP2.0 xml File',
    command=select_file_to_open # call the select file to open dialouge function
    )
    open_button.place(x=10, y=10)

def CreateGUICSVSavebutton():
    #CSV Save button
    global WriteDataframtoCSV
    save_csv_button = ttk.Button(
    gui,
    text='Save data to CSV file',
    command=lambda: save_dataframe_as_csv(joined_machine_pos_bedrock)
    )
    save_csv_button.place(x=175, y=10)



def xml_pasrse(filename):
    global machine_data

    if not os.path.exists(filename):
        mb.showerror("File Not Found", f"Cannot find file:\n{filename}")
        return

    try:
        xmlparse = ET.parse(filename)
        root = xmlparse.getroot()

    except ET.ParseError as e:
        mb.showerror("XML Parse Error", f"Error while parsing XML:\n{e}")
        return

    except Exception as e:
        mb.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}")
        return

    # Parse the XML file#Iterate over each <Equipment> element in the AEMP XML File
    for equipment in root.findall('Equipment'):
        try:
            # Find the location data
            equipmentHeader = equipment.find('EquipmentHeader')

            if equipmentHeader is not None:

                OEMname = equipmentHeader.find('OEMName').text
                model = equipmentHeader.find('Model').text
                serialNumber = equipmentHeader.find('EquipmentID').text  # Get the datetime attribute from the <Location> tag


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

            # Calculate the amount of Carbon Dioxide produced by each machine in tonnes
            CO2_produced = (float(fuelconsumed) * 2.680)/1000 #Each litre of Diesel produces 2.68kg  of CO2 during combusion then divide by 1000 to get CO2 tonnes

            # Append data to the list
            machine_data.append({'OEM Name': OEMname, 'Model': model, 'Serial Number': serialNumber, 'Latitude': latitude, 'Longitude': longitude,'Operating Hours': hour,'Fuel Consumed (litres)': fuelconsumed, 'Fuel Unit': fuelunits, 'C02 output (tonne)': ("%.2f"%CO2_produced)})

        except Exception as e:
            mb.showwarning("Parsing Data Error", f"Problem parsing equipment data:\n{e}")
            continue


def load_bedrock_shapefile():
    try:
        global joined_machine_pos_bedrock

        try:
            df = gpd.GeoDataFrame(machine_data)
        except Exception as e:
            tk.messagebox.showerror("GeoDataFrame Error", f"Could not create GeoDataFrame: {e}")
            return
        try:
            # Create geometry column from Latitude and Longitude
            df['geometry'] = df.apply(lambda row: Point(float(row['Longitude']), float(row['Latitude'])), axis=1)
            # Set Coordinate Reference System (CRS)
            df = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        except Exception as e:
            tk.messagebox.showerror("Geometry Error", f"Could not create lat / long points: {e}")
            return


        try:
            bedrock = gpd.read_file('Datafiles/NI_250k_bedrock_RCS_D_clipped.shp')
        except Exception as e:
            tk.messagebox.showerror("Shapefile Error", f"Could not load bedrock shapefile: {e}")
            return

        try:
            bedrock.drop(
                columns=['LEX', 'LEX_D', 'LEX_RCS', 'RCS', 'RCS_X', 'RANK', 'BED_EQ', 'BED_EQ_D', 'MB_EQ', 'MB_EQ_D', 'FM_EQ',
                        'FM_EQ_D', 'SUBGP_EQ', 'SUBGP_EQ_D', 'GP_EQ', 'GP_EQ_D', 'SUPGP_EQ', 'SUPGP_EQ_D', 'MAX_TIME_D',
                        'MIN_TIME_D', 'MAX_TIME_Y', 'MIN_TIME_Y', 'MAX_INDEX', 'MIN_INDEX', 'MAX_AGE', 'MIN_AGE', 'MAX_EPOCH',
                        'MIN_EPOCH', 'MAX_SUBPER', 'MIN_SUBPER', 'MAX_PERIOD', 'MIN_PERIOD', 'MAX_ERA', 'MIN_ERA', 'MAX_EON',
                        'MIN_EON', 'PREV_NAME', 'BGSTYPE', 'LEX_RCS_I', 'LEX_RCS_D', 'BGSREF', 'BGSREF_LEX', 'BGSREF_FM',
                        'BGSREF_GP', 'BGSREF_RK', 'SHEET', 'VERSION', 'RELEASED', 'NOM_SCALE', 'NOM_OS_YR', 'NOM_BGS_YR',
                        'MSLINK', 'LEX_ROCK'], axis=1, inplace=True)
            bedrock.to_crs(crs='epsg:4326', inplace=True)
            bedrock.rename(columns={"RCS_D": "Bedrock Type"}, inplace=True)
        except Exception as e:
            tk.messagebox.showerror("Bedrock Cleanup Error", f"Could not clean up bedrock data columns: {e}")
            return

        try:
            geometry = gpd.points_from_xy(df['Longitude'], df['Latitude'], crs='epsg:4326')
            machine_positions = gpd.GeoDataFrame(df[['OEM Name','Serial Number', 'Model', 'Operating Hours', 'Fuel Consumed (litres)', 'C02 output (tonne)', 'Latitude', 'Longitude']], # add in the main columns from geo data frame of AEMP xml file
                                geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']), # set the geometry using points_from_xy
                                crs='epsg:4326') # set the CRS using a text representation of the EPSG code for WGS84 lat/lon
            # Perform the spatial join, using 'contains' to find bedrock polygons that contain the machine position point
            joined_machine_pos_bedrock = gpd.sjoin(machine_positions, bedrock, predicate='within')
            joined_machine_pos_bedrock.drop(columns=['index_right', 'Shape_Leng', 'Shape_Area'], axis=1, inplace=True)
        except Exception as e:
            tk.messagebox.showerror("Spatial Join Error", f"Could not perform spatial join: {e}")
            return


        WriteDataframetoGUI(machinedataframe, joined_machine_pos_bedrock)

        m = joined_machine_pos_bedrock.explore('Serial Number', marker_type='marker', popup=True, legend=False, color='red')
        m = bedrock.explore('Bedrock Type', m=m, cmap='viridis', opacity=0.01, legend=False,)

        htmlfilename = os.path.splitext(xmlfilename)[0] + '.html'# remove the .xml extension from the filename that was read in and replace with .html for saving as a folium map
        print(htmlfilename)
        m.save(htmlfilename)
    except Exception as e: # catch any other unknown errors
        tk.messagebox.showerror("Unknown Error", f"An unexpected error occurred: {e}")

    #m.show_in_browser()#
    webbrowser.open_new_tab(htmlfilename)  # This is non-blocking way to show map without locking out tkinter GUI window




#### Main progream starts here ###
create_folium_map()
machinedataframe = CreateGUIframe()
CreateGUIfileopenbutton()
CreateGUICSVSavebutton()
# run the application gui loop to keep tkinter running
gui.mainloop()

### End of code ###




















