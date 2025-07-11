from skyfield.api import load, EarthSatellite, wgs84, Topos
from datetime import datetime, timedelta
import requests
from datetime import datetime, timezone
import os 
import pdb
import glob 
import pandas as pd
import argparse


# Extract timestamp from filename and sort
def extract_datetime_from_filename(f):
    basename = os.path.basename(f)
    date_str = basename.replace(f"tle_", "").replace(".txt", "")
    return datetime.strptime(date_str, "%Y-%m-%d_%H%M").replace(tzinfo=timezone.utc)


######################
def predict(observer_lat, observer_lon, observer_elev, satellite_names):
    
    # Create empty DataFrame with specified column types
    df = pd.DataFrame({
        "satname": pd.Series(dtype="str"),
        "timeoverpass": pd.Series(dtype="datetime64[ns]"),
        "view_angle": pd.Series(dtype="float"),
    })


    #observer_lat = 41.39  # Example: Barcelona
    #observer_lon = 2.15
    #observer_elev = 50     # meters
    observer = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon, elevation_m=observer_elev)  # Barcelona

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(days=1)

    # Load TLE from Celestrak
    tle_url = ["https://celestrak.org/NORAD/elements/gp.php?GROUP=resource&FORMAT=tle", 
               "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle"
               ]
    
    # Get all matching files
    files = glob.glob(os.path.join(dirTLE, f"tle_*.txt"))

    # Sort files by timestamp
    files_sorted = sorted(files, key=extract_datetime_from_filename)

    # Get latest file
    latest_file = files_sorted[-1] if files_sorted else None

    # Extract datetime from filename
    if latest_file:
        latest_datetime = extract_datetime_from_filename(latest_file)
        print("Latest tle file used:", latest_file)
        flag_tle = 'found' 
    else:
       flag_tle = 'nodata' 
    
    deltatime = 6
    if flag_tle == 'found':
        deltatime = (start_time - latest_datetime).total_seconds()/3600

    if deltatime > 3.:
        #update tle data
        tle_data = []
        for tle_url_ in tle_url:
            print(tle_url_)
            utc_now = datetime.now(timezone.utc)

            
            tle_data_ = requests.get(tle_url_).text.splitlines()
            tle_data.append(tle_data_)
        tle_data = [item for sublist in tle_data for item in sublist]
        with open(f"{dirTLE}/tle_{utc_now.strftime('%Y-%m-%d_%H%M')}.txt", 'w') as f: 
            f.writelines(line + '\n' for line in tle_data)
    
    else: 
        with open(latest_file) as f: 
            tle_data=f.readlines()

    for satellite_name in satellite_names:
        # Extract TLE for the target satellite
        for i in range(0, len(tle_data), 3):
            name = tle_data[i].strip()
            if name.upper() == satellite_name.upper():
                tle_line1 = tle_data[i+1].strip()
                tle_line2 = tle_data[i+2].strip()
                tle_dict = {} 
                tle_dict['tle_line1'] = tle_line1
                tle_dict['tle_line2'] = tle_line2
                break

        tle_line1, tle_line2 = tle_dict['tle_line1'], tle_dict['tle_line2']
        # Propagate Orbit
        ts = load.timescale()
        sat = EarthSatellite(tle_line1, tle_line2, satellite_name, ts)
        location = wgs84.latlon(observer_lat, observer_lon, elevation_m=observer_elev)

        t0 = ts.utc(start_time)
        t1 = ts.utc(end_time)

        # Find passes over observer location
        t_events, events = sat.find_events(location, t0, t1, altitude_degrees=5.0)
            
        # ------------------
        # Display Overpasses + Elevation at Culmination
        # ------------------

        #print(f"\nOverpass events for {satellite_name} at lat={observer_lat}, lon={observer_lon}\n")
        
        for t, e in zip(t_events, events):
            evt = ['rise', 'culminate', 'set'][e]
            time_str = t.utc_strftime('%Y-%m-%d %H:%M:%S')

            if evt == 'culminate':
                alt, az, distance = (sat - observer).at(t).altaz()
                df.loc[len(df)] = {
                                    'satname': satellite_name,
                                    'timeoverpass': t.utc_datetime(),
                                    'view_angle': 90 - alt.degrees,
                                  }
            #else:
            #    print(f"{evt:10s}: {time_str} UTC")
    
    return df


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='predic sat overpass as given location')
    parser.add_argument('-lat','--latitude', help='latitude in degree',required=True)
    parser.add_argument('-lon','--longitude', help='longitude in degree',required=True)
    parser.add_argument('-alt','--altitude', help='altitude in meter',required=True)

    args = parser.parse_args()

    observer_lat =  args.latitude
    observer_lon =  args.longitude
    observer_elev = args.altitude
    
    # ------------------
    # Configuration
    # ------------------
    dirTLE = '../tle/'
    os.makedirs(dirTLE, exist_ok=True)
    satellite_names = ["SENTINEL-3A", "SENTINEL-3B",  "METOP-B", "METOP-C", "EARTHCARE", "FOREST-2"]  # Options: "SENTINEL-3A", "SENTINEL-3B", "METOP-B", etc.
    
    observer_lat = 43.6043  # Example: Barcelona
    observer_lon = 1.44384
    observer_elev = 100     # meters
    
    #observer_lat = 41.39  # Example: Barcelona
    #observer_lon = 2.15
    #observer_elev = 50     # meters

    result = predict(observer_lat, observer_lon, observer_elev, satellite_names)

    print(result)
