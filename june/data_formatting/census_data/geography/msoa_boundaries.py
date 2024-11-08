from june import paths
import folium

latitude = 54.7768  # Example for Durham, UK
longitude = -1.5757

# Create a map centered around some coordinates
m = folium.Map(location=[latitude, longitude], zoom_start=10)

# Add the GeoJSON layer
folium.GeoJson(f"{paths.data_path}/input/geography/MSOA_Dec_2011_Boundaries_Generalised_Clipped_BGC_EW_V3_2022_-5730664396045573288.geojson").add_to(m)

# Display the map
m.save("map.html")