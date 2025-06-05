import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.distance import geodesic

# ====== CONFIGURATION ======
CENTER_LAT = 14.21622939   # Replace with your central plant's latitude
CENTER_LON = 80.08945027  # Replace with your central plant's longitude
CIRCLE_RADII_KM = list(range(50, 601, 50))  # 50 km to 600 km

# ====== DATA PREP ======
df = pd.read_csv('plants_with_coords.csv')
states = ['andhra pradesh', 'telangana', 'karnataka', 'tamil nadu']
df = df[df['State'].str.lower().isin(states)]

df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df['RegionLat'] = df['Latitude'].round(1)
df['RegionLon'] = df['Longitude'].round(1)

cement_df = df[df['Type'].str.lower().str.contains('cement')]
power_df = df[df['Type'].str.lower().str.contains('power')]

region_demand = cement_df.groupby(['RegionLat', 'RegionLon'])['Demand'].sum().reset_index()
region_supply = power_df.groupby(['RegionLat', 'RegionLon'])['Supply'].sum().reset_index()

region_df = pd.merge(region_demand, region_supply, how='outer', on=['RegionLat', 'RegionLon']).fillna(0)
region_df['NetDemand'] = region_df['Demand'] - region_df['Supply']

positive_net = region_df[region_df['NetDemand'] > 0].dropna(subset=['RegionLat', 'RegionLon'])
negative_net = region_df[region_df['NetDemand'] < 0].dropna(subset=['RegionLat', 'RegionLon'])

heat_data_positive = [
    [float(row['RegionLat']), float(row['RegionLon']), float(row['NetDemand'])]
    for _, row in positive_net.iterrows()
]

heat_data_negative = [
    [float(row['RegionLat']), float(row['RegionLon']), abs(float(row['NetDemand']))]
    for _, row in negative_net.iterrows()
]

# ====== MAP INITIALIZATION ======
m = folium.Map(location=[CENTER_LAT, CENTER_LON], zoom_start=6)

# ====== HEATMAP LAYERS ======
HeatMap(
    heat_data_positive,
    radius=50,
    blur=30,
    min_opacity=0.3,
    max_zoom=7 ,
    gradient={'0.4': 'lime', '0.7': 'yellow', '1': 'orange'},
    name='Demand > Supply'
).add_to(m)

HeatMap(
    heat_data_negative,
    radius=50,
    blur=30,
    min_opacity=0.3,
    max_zoom=7 ,
    gradient={'0.4': 'red', '0.7': 'orangered', '1': 'deeppink'},
    name='Supply > Demand'
).add_to(m)

# ====== CIRCLES AROUND CENTRAL PLANT (lighter and thinner) ======
for radius_km in CIRCLE_RADII_KM:
    folium.Circle(
        location=(CENTER_LAT, CENTER_LON),
        radius=radius_km * 1000,  # convert to meters
        color='black',
        fill=False,
        weight=1,               # thinner line
        opacity=0.5,            # more transparent
        dash_array="4,8",       # dotted style
        popup=f'{radius_km} km'
    ).add_to(m)


# ====== FINALIZATION ======
folium.LayerControl().add_to(m)
m.save("net_demand_supply_heatmap_with_circles.html")
