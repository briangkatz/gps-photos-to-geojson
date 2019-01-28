# Title: GPS-photos to GeoJSON
# Author: Brian G. Katz
# Organization: College of Earth, Ocean, and Atmospheric Sciences (CEOAS), Oregon State University
# Date: 2019-01-24
# Input: Directory of GPS-tagged images
# Output: GeoJSON file for mapping where and when the images were captured

# https://stackoverflow.com/questions/19804768/interpreting-gps-info-of-exif-data-from-photo-in-python
# https://gist.github.com/snakeye/fdc372dbf11370fe29eb

import os
import csv
import exifread as ef
from geojson import Feature, FeatureCollection, Point
from qgis.core import *

# Declare locals
input_dir = 'inputs'  # directory of GPS-tagged images
output_csv = 'outputs//gpsphoto_output.csv'
output_json = 'outputs//gpsphoto_output.json'
output_geojson = 'outputs//gpsphoto_output.geojson'


# Phase 1: GPS-tagged images to CSV
def _convert_to_degress(value):
    """
    Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
    :param value:
    :type value: exifread.utils.Ratio
    :rtype: float
    """
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)

    return d + (m / 60.0) + (s / 3600.0)


def getGPS(filepath):
    '''
    returns gps data if present other wise returns empty dictionary
    '''
    with open(filepath, 'r') as f:
        tags = ef.process_file(f)
        latitude = tags.get('GPS GPSLatitude')
        latitude_ref = tags.get('GPS GPSLatitudeRef')
        longitude = tags.get('GPS GPSLongitude')
        longitude_ref = tags.get('GPS GPSLongitudeRef')
        if latitude:
            lat_value = _convert_to_degress(latitude)
            if latitude_ref.values != 'N':
                lat_value = -lat_value
        else:
            return {}
        if longitude:
            lon_value = _convert_to_degress(longitude)
            if longitude_ref.values != 'E':
                lon_value = -lon_value
        else:
            return {}
        return {'latitude': lat_value, 'longitude': lon_value}
    return {}


# open a summary CSV file to output image name, lon, lat, and time
with open(output_csv, 'wb') as outfile:
    writer = csv.writer(outfile)
    # write column headings
    header = writer.writerow(['image', 'longitude', 'latitude', 'timestamp'])
    # timestamp format: yyyy-mm-ddThh:mm:ss
    for image in os.listdir(input_dir):
        image_path = input_dir + '//' + image
        ext = str(image[-4:]).lower()  # extension (make lowercase)
        image_name = image[:-4]
        image = image_name + ext  # keeps original file name syntax but with lowercase extension
        # reformat timestamp from image file name syntax to the naming convention we want
        # Samsung photos formatted as yyyymmdd_hhmmss.jpg
        try:
            int(image[0])
            yyyy = str(image[0:4])  # year
            monmon = str(image[4:6])  # month
            dd = str(image[6:8])  # day
            hh = str(image[9:11])  # hour
            minmin = str(image[11:13])  # minute
            ss = str(image[13:15])  # second
            # concatenate timestamp for CSV column
            timestamp = yyyy + '-' + monmon + '-' + dd + 'T' + hh + ':' + minmin + ':' + ss
        # DSLR photos with location information added via smartphone app are formatted differently - an additional string occupies file name indices 0:5
        except:
            yyyy = str(image[5:9])  # year
            monmon = str(image[9:11])  # month
            dd = str(image[11:13])  # day
            hh = str(image[14:16])  # hour
            minmin = str(image[16:18])  # minute
            ss = str(image[18:20])  # second
            # concatenate timestamp for CSV column
            timestamp = yyyy + '-' + monmon + '-' + dd + 'T' + hh + ':' + minmin + ':' + ss
        # extract lat, lon from images
        try:
            gps = getGPS(image_path)
            longitude = str(gps['longitude'])  # lon
            latitude = str(gps['latitude'])  # lat
            # create output row with image name, lon, lat, and time
            row = [image, longitude, latitude, timestamp]
            # write to the summary CSV
            writer.writerow(row)
        except:
            continue
    outfile.close()

print('CSV file successfully written from images\' GPS.')

# Phase 2: CSV to JSON
features = []

with open(output_csv, 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for image, longitude, latitude, timestamp in reader:
        try:
            float(longitude)
            latitude, longitude = map(float, (latitude, longitude))
            features.append(
                Feature(
                    geometry = Point((longitude, latitude)),
                    properties = {
                        'image': image,
                        'timestamp': timestamp
                    }
                )
            )
        except:
            pass

    collection = FeatureCollection(features)
    with open(output_json, 'w') as f:
        f.write('%s' % collection)

print('JSON file successfully created from CSV')

# Phase 3: JSON to GeoJSON
# Create a reference to the QGIS Application
qgs = QgsApplication([], False)

# Load QGIS
qgs.initQgis()

# Load data into QGIS
infile = output_json  # path to json file
vlayer = QgsVectorLayer(infile, 'vlayer', 'ogr')
QgsMapLayerRegistry.instance().addMapLayer(vlayer)

# Check if data loaded OK
if vlayer.isValid():
    print('Converting to GeoJSON in QGIS...')
else:
    print('Problem loading layer into QGIS')

crs = QgsCoordinateReferenceSystem('epsg:4326')

# Save memory layer to file
error = QgsVectorFileWriter.writeAsVectorFormat(vlayer, output_geojson, 'UTF-8', crs, 'GeoJSON')

if error == QgsVectorFileWriter.NoError:
    print('GeoJSON file successfully created from JSON.')

# When your script is complete, call exitQgis() to remove the provider and layer registries from memory
qgs.exitQgis()

print('Complete!')
