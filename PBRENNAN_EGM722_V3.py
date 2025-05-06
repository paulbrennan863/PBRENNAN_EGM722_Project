# V3 with added API pull from Orbcomm site

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
from tkinter import simpledialog

import rasterio as rio
from rasterio import sample

import urllib3
import requests
from requests.auth import HTTPBasicAuth

# define global variables that are used throughout the program in different functions

# define the tkinter main GUI frame instance
gui = tk.Tk()

# preload with xml test filename
xmlfilename = ""

# global list for parsed xml data
machine_data = []





#create the main GUI window
def CreateGUIframe():
    """
       Initializes and configures the main Tkinter GUI window for the AEMP 2.0 Machine Viewer application.
        GUI size is set for 1500 x 300 pixels.
        Keeping the window always on top, so it is always seen.

       It also creates a `Frame` widget within the GUI window `machinedataframe` for displaying
       the machine data, and places it at a fixed position with a visible border.

       Returns:
           None
       """
    gui.title('AEMP 2.0 Machine Viewer')
    gui.resizable(False, False)
    gui.geometry('1500x300')
    # make sure the GUI form is on top to ensure it is seen
    gui.attributes('-topmost', True)

    machinedataframe=tk.Frame(gui,borderwidth=2, relief=tk.RIDGE)
    machinedataframe.place(x=10, y=50, height=220, width=1450)

def gui_on_closing():
    """
       Handles the closing event when the user clicks the 'X' button on the application window.
       The user is promoted with a confirmation to close messagebox before closing the application. If the user confirms,
       it gracefully terminates the application by calling `gui.destroy()`.

       Returns:
           None
       """

    if mb.askokcancel("Quit", "Do you really want to quit?"):
        # This unloads the application window in a controlled way
        gui.destroy()



def CreateGUIfileopenbutton():
    """
        Creates and places a 'File Open' button on the main GUI window.

        This button allows the user to select and open an AEMP 2.0 XML file.
        When clicked, it triggers the `select_file_to_open` function, which  will parse the XML data

        The button is placed near the top-left corner of the GUI window using the Tkinter 'place' method

        Returns:
            None
        """
    #open button
    open_button = ttk.Button(
    gui,
    text='Open a AEMP2.0 xml File',
    command=select_file_to_open # call the select file to open dialouge function
    )
    open_button.place(x=10, y=10)

def CreateGUICSVSavebutton():
    """
        Creates and places a 'Save to CSV' button on the main GUI window.

        This button allows the user to export the spatial joined machine & bedrock data to a CSV file.
        When clicked, it calls the `save_dataframe_as_csv` function with the

        The button is placed near the top-left corner of the GUI window using the Tkinter 'place' method

        Returns:
            None
        """
    #CSV Save button
    global WriteDataframtoCSV
    save_csv_button = ttk.Button(
    gui,
    text='Save data to CSV file',
    command=lambda: save_dataframe_as_csv(joined_machine_pos_bedrock, xmlfilename)
    )
    save_csv_button.place(x=175, y=10)

def CreateGUI_APIbutton():
    """
        Creates and places a 'Load from API' button on the main GUI window.

        This button allows the user to pull a AEMP xml from an external RESTful API.
        When clicked, it calls the `load_from_API` function

        The button is placed near the top-right corner of the GUI window using the Tkinter 'place' method

        Returns:
            None
        """
    #API Load button
    global WriteDataframtoCSV
    api_load_button = ttk.Button(
    gui,
    text='Load External API data',
    command=lambda: load_RESTfulAPI()
    )
    #place the button beside the others
    api_load_button.place(x=320, y=10)


def get_API_credentials():
    """
       Prompt the user to enter API credentials with 'simpledialogs' input boxes.
       for API endpoint, username, and password.
       The password input is masked with "*" for security.

       Returns:
                Three string tuple containing:
               - endpoint (str): The API endpoint URL.
               - username (str): The username for API authentication.
               - password (str): The password for API authentication.
       """
    # Ask for API endpoint, username and password
    endpoint = simpledialog.askstring("Login", "Enter API endpoint:")
    username = simpledialog.askstring("Login", "Enter username:")
    password = simpledialog.askstring("Login", "Enter password:", show='*')
    print(endpoint)
    #return the entered details back to calling dunction for parsing
    return endpoint, username, password


def select_file_to_open():
    """
        Opens a Tkinter file dialog for the user to select an XML file and processes it.
        Extracts and stores only the base file name (excluding the full path) as a global variable `xmlfilename`.
        The global filename will be used for storing a Folium map HTML file and CSV file elsewhere in the program
        Calls `xml_parse()` function to parse the selected XML file and extract machine data.
        Calls `load_bedrock_shapefile()` function to perform a spatial join with 250K bedrock data for Northern Ireland and the parsed machine data from the AEMP xml file.

        Returns:
            None
        """
    # define the  xmlfile name as the global one to be modified
    global xmlfilename


    filetypes = (('XML files','*.xml'),)
    filename = fd.askopenfilename(title='Open XML file', initialdir='/',filetypes=filetypes)
    # Get just the file name and drop the extension
    filename = os.path.basename(filename)

    # assign the opened filename to the global xmlfilename variable so it can be used by other functions
    xmlfilename=filename
    # call XML Parse function to read the machine data
    xml_parse(filename)
    load_bedrock_shapefile(filename)

def load_RESTfulAPI():
    """
            This function pulls data from an external telematics portal in a AEMP 2.0 format. The file is in xml format
            There is a response value back from the website to acknowledge if the login and read has been successful.
            The returned data is in text format. It is saved as a file to allow it to be parsed by the 'xml_parse()' and load_bedrock_shapefile()` functions
            to perform a spatial join with 250K bedrock data for Northern Ireland and the parsed machine data from the AEMP xml file.

            As this links to the company portal, the login  details are provided in the assignment "Part 1 The How-to guide" pdf file
            The login account expires 31/05/2025

            Returns:
                None
            """

    # call function to return the API endpoint, username and password for external site
    url, username, password = get_API_credentials()

    # using the request function send the login details to the telematics provider RESTful API portal
    private_url_response = requests.get(url=url, verify=False, auth=HTTPBasicAuth(username, password))

    # populate xmlscript with the response content back from the API read
    xmlscript = private_url_response.content


    # read the  response status back from the API read
    restfulAPIresponce = private_url_response.status_code

    # if there is a non-OK response (200) from the API, notify the error and return
    if  restfulAPIresponce != 200:
        mb.showerror("REST API Error", f"Invalid API response:\n{restfulAPIresponce}")
        return



    # setup the API responce xml data to be writtem to a file
    with open("APIresponse.xml", "w", encoding="utf-8") as f:
        f.write(private_url_response.text)
    # save the file as 'APIresponse.xml' and assign to the filename variable
    filename = os.path.basename("APIresponse.xml")

    # call the xml parse function to extract the machine data
    xml_parse(filename)
    # load the bedrosk data
    load_bedrock_shapefile(filename)

# save as dialog to save
def save_dataframe_as_csv(dfcsv, xmlfilename):
    """
        Opens a Tkinter 'file save as' dialog to save the processed xml and bedrock data as a CSV file.
        The 'geometry' column  is removed as Latitude and Longitude data are included as separate columns

        Input Parameters:
            dfcsv (GeoDataFrame): The final GeoDataFrame to be saved as a CSV file.
            xmlfilename (str): The name of the filename that has been  used to parse the machine information  and
            used for the map display
        Returns:
            None
        """
    # remove the .xml extension from the filename that was read in
    filename = os.path.splitext(xmlfilename)[0]
    filetypes = (('CSV files', '*.csv'),)
    filename = fd.asksaveasfilename(title='Save DataFrame as CSV', initialdir='/', initialfile=filename, defaultextension=".csv",filetypes=filetypes)

    if filename:
        # Drop geometry column for writing to CSV file as we have columns for Lat & Long already
        dfcsv = joined_machine_pos_bedrock.drop(columns='geometry', errors='ignore')
        dfcsv.to_csv(filename, index=False)



#write the machine dataframe to the GUI frame
def WriteDataframetoGUI(machinedataframe, joined_machine_pos_bedrock):
    """
       Displays the processed spatially joined xml & bedrock data in a Tkinter Treeview widget inside the main GUI frame.
       formats the column headers to be bold and left-aligned

       Input Parameters:
           machinedataframe (tk.Frame) The Tkinter frame where the Treeview widget will be placed.
           joined_machine_pos_bedrock (GeoDataFrame). The GeoDataFrame containing machine data
               and spatial join bedrock results, which will be displayed in the Treeview.

       Returns:
           None
       """
    # Drop geometry column for display as we have columns for Lat & Long already
    dfgui = joined_machine_pos_bedrock.drop(columns='geometry', errors='ignore')

    # adjust the style values to making headings bold and left justified
    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Arial', 10, 'bold'), anchor='w')  # 'w' = (west) left-justified

    tree = ttk.Treeview(machinedataframe, columns=list(dfgui.columns), show='headings')

    # Add column headers
    for col in dfgui.columns:
        tree.heading(col, text=col, anchor='w')
        tree.column(col, width=150)

    for _, row in dfgui.iterrows():
        tree.insert("", "end", values=list(row))

    #tree.pack(fill='both', expand=True)
    tree.place(x=10, y=50, height=220, width=1450)





# main function of code to process the inputted xml file
def xml_parse(filename):
    """
        Parses an AEMP 2.0 XML file and extracts machine equipment data into a global list.

This function reads the given XML file, extracts relevant information about
each piece of equipment, including Original Equipment Manufacturer (OEM) name, model, serial number, geographic location,
operating hours, fuel usage

An estimated value for CO2 emissions for each machine is calculated based on fuel usage.

The extracted data is stored as a dictionary in the global `machine_data` list.

Error handling:
    - If the file does not exist, a Tkinter messagebox error is shown.
    - If the XML is malformed or cannot be parsed, a parse error is shown.
    - Any other unexpected error during file reading will also trigger an error message.
    - Errors while parsing individual 'Equipment' entries are caught and warned without halting the process.

Input Parameters:
    filename (str): The name of the XML file to be parsed.

Returns:
    None

    """
    global machine_data
    # clear the machine data list at the start of each parse to purge out previous data
    machine_data.clear()

    if not os.path.exists(filename):
        mb.showerror("File Not Found", f"Cannot find file:\n{filename}")
        return

    try:
        xmlparse = ET.parse(filename)
        root = xmlparse.getroot()

        # Remove namespaces from flee tag name (these cause the xml parse to crash)
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]  # Keep only the tag name


    except ET.ParseError as e:
        mb.showerror("XML Parse Error", f"Error while parsing XML:\n{e}")
        return

    except Exception as e:
        mb.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}")
        return

    # Parse the XML file#Iterate over each <Equipment> element in the AEMP XML File
    for equipment in root.findall('Equipment'):
        try:
            # Find  each piece of equipment in the xml file
            equipmentHeader = equipment.find('EquipmentHeader')

            if equipmentHeader is not None:
                # Get the machine attribute data from the <equipmentHeader> tag
                OEMname = equipmentHeader.find('OEMName').text
                model = equipmentHeader.find('Model').text
                serialNumber = equipmentHeader.find('EquipmentID').text


            # Find the location data
            location = equipment.find('Location')
            if location is not None:
                latitude = location.find('Latitude').text
                longitude = location.find('Longitude').text

            # Find the Engine Hours data
            cumulativeoperatinghours = equipment.find('CumulativeOperatingHours')
            if cumulativeoperatinghours is not None:
                hour = cumulativeoperatinghours.find('Hour').text
            else:
                # If no value is found in fuel branch the add in void
                hour = 'Void'

            # Find the Total fuel used by machine
            fuelused = equipment.find('FuelUsed')
            if fuelused is not None:
                fuelunits = fuelused.find('FuelUnits').text
                fuelconsumed = fuelused.find('FuelConsumed').text
            else:
                fuelunits  = 'Void'  # If no value is found in fuel branch then add in void
                fuelconsumed ='0'  # If no value is found in fuel branch then make value 0

            # Calculate the amount of Carbon Dioxide produced by each machine in tonnes
            # Each litre of Diesel produces 2.68kg  of CO2 during combusion then divide by  result by 1000 to get CO2 tonnes
            CO2_produced = (float(fuelconsumed) * 2.680)/1000

            # Append data to the list
            machine_data.append({'OEM Name': OEMname, 'Model': model, 'Serial Number': serialNumber, 'Latitude': latitude, 'Longitude': longitude,'Operating Hours': hour,'Fuel Consumed (litres)': fuelconsumed, 'Fuel Unit': fuelunits, 'C02 output (tonne)': ("%.2f"%CO2_produced)})

        except Exception as e:
            mb.showwarning("Parsing Data Error", f"Problem parsing equipment data:\n{e}")
            continue


def load_bedrock_shapefile(filename):
    """
    Loads the Northern Ireland bedrock geological data and joins it with machine location data, then displays the results.

    This function performs the following steps:
    1. Converts the global `machine_data` into a GeoDataFrame with geographic points from Latitude and Longitude.

    2. Loads the shapefile containing bedrock geological data for Northern Ireland.

    3. Removes unnecessary columns from the bedrock dataset and sets the coordinate reference system.

    4. Performs a spatial join to associate machine data points with bedrock polygons and adds in the type of bedrock each machine is situated on

    5. Displays the joined data on the  Tkinter GUI and creates a Folium map showing machine positions and bedrock areas.

    6. Saves the map as an HTML file named after the current XML  filename.

        Error Handling:
            - Displays popup error messages using `tkinter.messagebox` for various failures, including:
                - Failure to create GeoDataFrame.
                - Geometry creation issues, from missing or corrupted Lat / Long data from machine
                - Shapefile loading or formatting errors.
                - Issues during spatial join or map generation.
            - Catches any unexpected errors and shows a general error message.

        Input Parameters:
        filename (str): The name of the loaded XML file that will be used to create name of Folium map for display and saving.

        Returns:
            None
        """

    try:
        global joined_machine_pos_bedrock


        try:
            #create geodataframe from the machine data
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
            #load in the NI bedrock shape file
            bedrock = gpd.read_file('Datafiles/NI_250k_bedrock_RCS_D_clipped.shp')
        except Exception as e:
            # flag any error that  happen when loading the shapefile dataset
            tk.messagebox.showerror("Shapefile Error", f"Could not load bedrock shapefile: {e}")
            return

        try:
            # Drop columns that are not needed, to try and keep things tidy
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
            # flag any error that happens when dropping columns from the shapefile dataset
            tk.messagebox.showerror("Bedrock Cleanup Error", f"Could not clean up bedrock data columns: {e}")
            return

        try:

            # Original GeoDataFrame in WGS84
            df['geometry'] = df.apply(lambda row: Point(float(row['Longitude']), float(row['Latitude'])), axis=1)
            machine_positions = gpd.GeoDataFrame(
                df[['OEM Name', 'Serial Number', 'Model', 'Operating Hours',
                    'Fuel Consumed (litres)', 'C02 output (tonne)', 'Latitude', 'Longitude']],
                geometry=df['geometry'],
                crs='EPSG:4326'
            )




            #Project to Irish Grid (EPSG:29903) to a metres values rather than lat/long
            machine_positions_metres = machine_positions.to_crs(epsg=29903)
            # Extract elevation values for machine positions from the NI elevation raster
            elevation_values = extract_point_elevations(machine_positions_metres)



            # spatially join machine positions and bedrock. Find which bedrock polygons that 'contain' the machine position
            joined_machine_pos_bedrock = gpd.sjoin(machine_positions, bedrock, predicate='within')
            # Drop columns that are not needed, to try and keep things tidy
            joined_machine_pos_bedrock.drop(columns=['index_right', 'Shape_Leng', 'Shape_Area'], axis=1, inplace=True)


            # Add elevation values to the spatial joined result
            joined_machine_pos_bedrock['Elevation (m)'] = elevation_values

        except Exception as e:
            # flag any errors on the spatial join
            tk.messagebox.showerror("Spatial Join Error", f"Could not perform spatial join: {e}")
            return

        # Populate the GUI data frame with the collated geodataframe results
        WriteDataframetoGUI(machinedataframe, joined_machine_pos_bedrock)

        #Add the machine positions markers to the Folium map, no legend needed to avoid clutter
        m = joined_machine_pos_bedrock.explore('Serial Number', marker_type='marker', popup=True, legend=False, color='red')

        # Add the bedrock shapefile to the Folium map, no legend needed to avoid clutter. Make the bedrock semi transparent, to allow underlyinf features on map to be seen
        m = bedrock.explore('Bedrock Type', m=m, cmap='viridis', opacity=0.01, legend=False,)
        htmlfilename = os.path.splitext(filename)[0] + '.html'# remove the .xml extension from the filename that was read in and replace with .html for saving as a folium map
        #save the html file to the directory
        m.save(htmlfilename)

        # catch any other unknown errors
    except Exception as e:
        tk.messagebox.showerror("Unknown Error", f"An unexpected error occurred: {e}")

    #m.show_in_browser()#
    webbrowser.open_new_tab(htmlfilename)  # This is non-blocking way to show map without locking out tkinter GUI window


def extract_point_elevations(machine_pos_df, raster_path='Datafiles/ni_dtm.tif'):
    """
    Extract elevation values from the NI Elevation raster for the machine point locations.

    Args:
        machine_pos_df (GeoDataFrame): GeoDataFrame with point geometries for machine positions (in same CRS as raster).
        raster_path (str): Path to the DTM raster file.

    Returns:
        List of elevation values.
    """

    #Open the Elevations raster file
    with rio.open(raster_path) as raster_dataset2:
        # Ensure CRS matches, if not make them the same
        if machine_pos_df.crs != raster_dataset2.crs:
            machine_pos_df = machine_pos_df.to_crs(raster_dataset2.crs)

        # Get the machine position coordinate from the geometry dataframe
        machine_coords = [(point.x, point.y) for point in machine_pos_df.geometry]

        # Sample the elevation raster at the machine  coordinates
        elevations = list(raster_dataset2.sample(machine_coords))
        # Flatten list of single-band arrays (divide the value by 10, for some reason the values in the elevation raster are too high)
        elevation_values = [val[0] /10 for val in elevations]  # val[0] since it's usually 1 band

    #return  elevations values for each of the machine positions
    return elevation_values



def create_folium_map():
    """
    Creates a global Folium map centered on Northern Ireland.
    The map instance is stored in the global variable `m`, so it can
    be used or updated elsewhere in the program.

    Returns:
        None
    """
    # let function know it is the global map instance being called
    global m
    # centre the map around Northern Ireland
    m = folium.Map(location=[54.6, -7], zoom_start=9)


#### Main progream starts here ###

# call function to create the main GUI interface using tkinter
machinedataframe = CreateGUIframe() # call function to create the main GUI interface using tkinter

# call function to create tkinter File Open dialogue to open the AEMP 2.0 xml file
CreateGUIfileopenbutton()

# call function to create tkinter 'Save as' dialogue to save the processed xml file and bedrock data as a CSV file
CreateGUICSVSavebutton()

# call function to create tkinter 'API Load' button to pull xml data in form external RESTfulAPI account
CreateGUI_APIbutton()

# call function to initialise the folium map centred around Northern Ireland
create_folium_map()

# Bind the  X button to 'on_closing function' to unload the application gracefully
gui.protocol("WM_DELETE_WINDOW", gui_on_closing)

# run the application gui loop to keep tkinter running to allow button press functions to be acted on.
gui.mainloop()

### End of code ###




















