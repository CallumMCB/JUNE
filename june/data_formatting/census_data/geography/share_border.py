import geopandas as gpd
import json
from june import paths

# File paths
msoa_fp = f"{paths.data_path}/input/geography/msoa_boundaries.geojson"
msoa_output_fp = f"{paths.data_path}/input/geography/msoa_borders.json"
lad_fp = f"{paths.data_path}/input/geography/lad_boundaries.geojson"
lad_output_fp = f"{paths.data_path}/input/geography/lad_borders.json"

def process_file(fp, output_fp, code):
    # Load MSOA boundaries
    gdf = gpd.read_file(fp)

    # Create a dictionary to store the relationships
    borders_dict = {}

    # Iterate through each MSOA boundary and find neighbors
    for index, area in gdf.iterrows():
        # Get neighboring areas
        neighbors = gdf[gdf.geometry.touches(area.geometry)]

        # Store the neighboring MSOAs in a list
        neighbors_list = sorted(neighbors[code].tolist())

        # Store the information in the dictionary
        borders_dict[area[code]] = {
            'neighbors': neighbors_list,
            'num_neighbors': len(neighbors_list)
        }

    # Save the dictionary to a JSON file
    with open(output_fp, 'w') as f:
        json.dump(borders_dict, f, indent=4)

    print(f"Border relationships saved to {output_fp}")

process_file(msoa_fp, msoa_output_fp, 'MSOA21CD')
process_file(lad_fp, lad_output_fp, 'LAD24CD')