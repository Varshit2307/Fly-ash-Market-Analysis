import pandas as pd
import folium
from geopy.distance import geodesic
from folium import FeatureGroup, LayerControl
from folium.plugins import HeatMap
import json

# Load and clean data
df = pd.read_csv("plants_with_coords.csv")
df = df.dropna(subset=["Latitude", "Longitude"])
df['Type'] = df['Type'].str.lower().str.strip()
df['State'] = df['State'].str.lower().str.strip()

# Define your central (main) plant
central_plant_name = "MEENAKSHI ENERGY - VEDANTA POWER,300 MW"
central_lat = 14.21622939
central_lon = 80.08945027

# Filter for South Indian states
selected_states = ['andhra pradesh', 'telangana', 'karnataka', 'tamil nadu']
df = df[df['State'].isin(selected_states)]

# Split into cement and power plants
cement_plants = df[df['Type'] == 'cement'].reset_index(drop=True)
power_plants = df[df['Type'] == 'power'].reset_index(drop=True)
brick_plants = df[df['Type'] == 'brick manufacturer'].reset_index(drop=True)
rmc_plants = df[df['Type'] == 'rmc'].reset_index(drop=True)
road_dev_plants = df[df['Type'].str.contains("road dev", case=False)].reset_index(drop=True)



# Compute suppliers for each cement plant
supplier_map = {}
for _, cement in cement_plants.iterrows():
    cement_coords = (cement['Latitude'], cement['Longitude'])
    suppliers = []
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(cement_coords, power_coords).km)*1.35
        if dist <= 300:
            suppliers.append((power['Name'], dist))
    supplier_map[cement['Name']] = suppliers

# Add Distance from central plant
cement_plants['Distance from Our Plant (km)'] = cement_plants.apply(
    lambda row: geodesic((central_lat, central_lon), (row['Latitude'], row['Longitude'])).km, axis=1
)

# Compute suppliers for Brick Plants
brick_supplier_map = {}
for _, brick in brick_plants.iterrows():
    brick_coords = (brick['Latitude'], brick['Longitude'])
    suppliers = []
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(brick_coords, power_coords).km) * 1.35
        if dist <= 300:
            suppliers.append((power['Name'], dist))
    brick_supplier_map[brick['Name']] = suppliers

# Add Distance from central plant
brick_plants['Distance from Our Plant (km)'] = brick_plants.apply(
    lambda row: geodesic((central_lat, central_lon), (row['Latitude'], row['Longitude'])).km, axis=1
)

# Compute suppliers for RMC Plants
rmc_supplier_map = {}
for _, rmc in rmc_plants.iterrows():
    rmc_coords = (rmc['Latitude'], rmc['Longitude'])
    suppliers = []
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(rmc_coords, power_coords).km) * 1.35
        if dist <= 300:
            suppliers.append((power['Name'], dist))
    rmc_supplier_map[rmc['Name']] = suppliers

# Add Distance from central plant
rmc_plants['Distance from Our Plant (km)'] = rmc_plants.apply(
    lambda row: geodesic((central_lat, central_lon), (row['Latitude'], row['Longitude'])).km, axis=1
)

# Compute suppliers for Road Development Plants
road_supplier_map = {}
for _, road in road_dev_plants.iterrows():
    road_coords = (road['Latitude'], road['Longitude'])
    suppliers = []
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(road_coords, power_coords).km) * 1.35
        if dist <= 300:
            suppliers.append((power['Name'], dist))
    road_supplier_map[road['Name']] = suppliers

# Add Distance from central plant
road_dev_plants['Distance from Our Plant (km)'] = road_dev_plants.apply(
    lambda row: geodesic((central_lat, central_lon), (row['Latitude'], row['Longitude'])).km, axis=1
)


power_plants['Distance from Our Plant (km)'] = power_plants.apply(
    lambda row: geodesic((central_lat, central_lon), (row['Latitude'], row['Longitude'])).km, axis=1
)

# Compute buyers for each power plant
buyer_map = {}
for _, power in power_plants.iterrows():
    power_coords = (power['Latitude'], power['Longitude'])
    buyers = []
    for _, cement in cement_plants.iterrows():
        cement_coords = (cement['Latitude'], cement['Longitude'])
        dist = (geodesic(power_coords, cement_coords).km)*1.35
        if dist <= 300:
            buyers.append((cement['Name'], dist))
    buyer_map[power['Name']] = buyers



# Create folium map
m = folium.Map(location=[central_lat, central_lon], zoom_start=7)

type_groups = {
    'Cement Plants': folium.FeatureGroup(name='Cement Plants', show=True),
    'Brick Plants': folium.FeatureGroup(name='Brick Plants', show=True),
    'RMC Plants': folium.FeatureGroup(name='RMC Plants', show=True),
    'Road Dev Plants': folium.FeatureGroup(name='Road Dev Plants', show=True),
}

# Add central plant marker
folium.Marker(
    location=[central_lat, central_lon],
    popup=folium.Popup(f"<b>Central Plant:</b><br>{central_plant_name}", max_width=300),
    icon=folium.Icon(color='red', icon='star', prefix='fa')
).add_to(m)

# Distance ranges and color palette
distance_ranges = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 250), (250, 300),
                   (300, 350), (350, 400), (400, 450), (450, 500), (500, 550), (550, 600), (600, 650)]
colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'pink', 'black', 'gray', 'beige', 'darkblue', 'darkpurple', 'lightgray']

# Create distance-based feature groups
range_groups = {}
for r_start, r_end in distance_ranges:
    label = f"{r_start}-{r_end} km"
    range_groups[label] = FeatureGroup(name=f"{label} from Central Plant")

# Utility to find range group label
def get_range_label(distance):
    for r_start, r_end in distance_ranges:
        if r_start <= distance < r_end:
            return f"{r_start}-{r_end} km"
    return None

# Add Cement Plant Markers to appropriate range group
for _, row in cement_plants.iterrows():
    name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    dist_main = row['Distance from plant']
    
    suppliers = supplier_map[name]

    # Compute nearest power plant from all (not just within 150 km)
    cement_coords = (row['Latitude'], row['Longitude'])
    nearest_supplier = None
    min_distance = float('inf')
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(cement_coords, power_coords).km)*1.35
        if dist < min_distance:
            min_distance = dist
            nearest_supplier = (power['Name'], dist)


    popup_html = (
        f"<b>Cement Plant:</b> {name}<br>"
        f"<b>Distance from Our Plant:</b> {dist_main:.1f} km<br>"
    )

    if nearest_supplier:
        popup_html += (
            f"<b>Nearest Supplier (any distance):</b><br>"
            f"- {nearest_supplier[0]} ({nearest_supplier[1]:.1f} km)<br>"
        )
    else:
        popup_html += "<b>Nearest Supplier (any distance):</b> None<br>"

    popup_html += "<b>Suppliers within 300 km:</b><br>"
    if suppliers:
        for sup_name, dist in suppliers:
            popup_html += f"- {sup_name} ({dist:.1f} km)<br>"
    else:
        popup_html += "None"



    label = get_range_label(dist_main)
    if label:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='blue', icon='industry', prefix='fa')
        ).add_to(range_groups[label])

# Add Brick Plant Markers
for _, row in brick_plants.iterrows():
    name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    dist_main = row['Distance from plant']

    suppliers = brick_supplier_map[name]

    # Nearest power plant
    brick_coords = (lat, lon)
    nearest_supplier = None
    min_distance = float('inf')
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(brick_coords, power_coords).km) * 1.35
        if dist < min_distance:
            min_distance = dist
            nearest_supplier = (power['Name'], dist)

    popup_html = (
        f"<b>Brick Plant:</b> {name}<br>"
        f"<b>Distance from Our Plant:</b> {dist_main:.1f} km<br>"
    )

    if nearest_supplier:
        popup_html += (
            f"<b>Nearest Supplier (any distance):</b><br>"
            f"- {nearest_supplier[0]} ({nearest_supplier[1]:.1f} km)<br>"
        )
    else:
        popup_html += "<b>Nearest Supplier (any distance):</b> None<br>"

    popup_html += "<b>Suppliers within 300 km:</b><br>"
    if suppliers:
        for sup_name, dist in suppliers:
            popup_html += f"- {sup_name} ({dist:.1f} km)<br>"
    else:
        popup_html += "None"

    label = get_range_label(dist_main)
    if label:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='red', icon='cubes', prefix='fa')  # Brick icon
        ).add_to(range_groups[label])

# Add RMC Plant Markers
for _, row in rmc_plants.iterrows():
    name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    dist_main = row['Distance from plant']

    suppliers = rmc_supplier_map[name]

    rmc_coords = (lat, lon)
    nearest_supplier = None
    min_distance = float('inf')
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(rmc_coords, power_coords).km) * 1.35
        if dist < min_distance:
            min_distance = dist
            nearest_supplier = (power['Name'], dist)

    popup_html = (
        f"<b>RMC Plant:</b> {name}<br>"
        f"<b>Distance from Our Plant:</b> {dist_main:.1f} km<br>"
    )

    if nearest_supplier:
        popup_html += (
            f"<b>Nearest Supplier (any distance):</b><br>"
            f"- {nearest_supplier[0]} ({nearest_supplier[1]:.1f} km)<br>"
        )
    else:
        popup_html += "<b>Nearest Supplier (any distance):</b> None<br>"

    popup_html += "<b>Suppliers within 300 km:</b><br>"
    if suppliers:
        for sup_name, dist in suppliers:
            popup_html += f"- {sup_name} ({dist:.1f} km)<br>"
    else:
        popup_html += "None"

    label = get_range_label(dist_main)
    if label:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='orange', icon='truck', prefix='fa')  # RMC icon
        ).add_to(range_groups[label])

# Add Road Development Plant Markers
for _, row in road_dev_plants.iterrows():
    name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    dist_main = row['Distance from plant']

    suppliers = road_supplier_map[name]

    road_coords = (lat, lon)
    nearest_supplier = None
    min_distance = float('inf')
    for _, power in power_plants.iterrows():
        power_coords = (power['Latitude'], power['Longitude'])
        dist = (geodesic(road_coords, power_coords).km) * 1.35
        if dist < min_distance:
            min_distance = dist
            nearest_supplier = (power['Name'], dist)

    popup_html = (
        f"<b>Road Dev:</b> {name}<br>"
        f"<b>Distance from Our Plant:</b> {dist_main:.1f} km<br>"
    )

    if nearest_supplier:
        popup_html += (
            f"<b>Nearest Supplier (any distance):</b><br>"
            f"- {nearest_supplier[0]} ({nearest_supplier[1]:.1f} km)<br>"
        )
    else:
        popup_html += "<b>Nearest Supplier (any distance):</b> None<br>"

    popup_html += "<b>Suppliers within 300 km:</b><br>"
    if suppliers:
        for sup_name, dist in suppliers:
            popup_html += f"- {sup_name} ({dist:.1f} km)<br>"
    else:
        popup_html += "None"

    label = get_range_label(dist_main)
    if label:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='purple', icon='road', prefix='fa')  # Road icon
        ).add_to(range_groups[label])


# Add Power Plant Markers to appropriate range group
for _, row in power_plants.iterrows():
    name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    dist_main = row['Distance from plant']
    buyers = buyer_map[name]

    popup_html = (
        f"<b>Power Plant:</b> {name}<br>"
        f"<b>Distance from Our Plant:</b> {dist_main:.1f} km<br>"
        f"<b>Cement Plants within 300 km:</b><br>"
    )
    if buyers:
        for buyer_name, dist in buyers:
            popup_html += f"- {buyer_name} ({dist:.1f} km)<br>"
    else:
        popup_html += "None"

    label = get_range_label(dist_main)
    if label:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='green', icon='bolt', prefix='fa')
        ).add_to(range_groups[label])

# Add all range groups to map
for group in range_groups.values():
    group.add_to(m)

# Add concentric circles around central plant
for idx, (r_start, r_end) in enumerate(distance_ranges):
    folium.Circle(
        radius=r_end * 1000,
        location=(central_lat, central_lon),
        color=colors[idx % len(colors)],
        fill=False,
        weight=1.5,
        dash_array="5, 10",
        tooltip=f"{r_end} km range"
    ).add_to(m)

from folium.plugins import Search
from folium.map import FeatureGroup

# Combine all markers into one FeatureGroup for search
all_markers = FeatureGroup(name="All Plants for Search")

# Add markers with a special tag for search
for _, row in pd.concat([cement_plants, power_plants,brick_plants,rmc_plants,road_dev_plants]).iterrows():
    plant_name = row['Name']
    lat = row['Latitude']
    lon = row['Longitude']
    marker = folium.Marker(
        location=[lat, lon],
        title=plant_name,
        tooltip=plant_name,
        icon=folium.Icon(color='darkblue', icon='search', prefix='fa')
    )
    marker.add_to(all_markers)

all_markers.add_to(m)

# Add Search control
Search(
    layer=all_markers,
    search_label='title',
    placeholder="Search plant name...",
    collapsed=False,
    zoom=20,
    position='topright'
).add_to(m)

# Prepare long-form CSV: one row per cement plant - supplier pair
rows = []

for _, cement in cement_plants.iterrows():
    cement_name = cement['Name']
    cement_lat = cement['Latitude']
    cement_lon = cement['Longitude']

    for _, power in power_plants.iterrows():
        power_name = power['Name']
        power_lat = power['Latitude']
        power_lon = power['Longitude']

        distance_km = geodesic((cement_lat, cement_lon), (power_lat, power_lon)).km * 1.35

        if distance_km <= 300:
            rows.append({
                "Cement Plant": cement_name,
                "Supplier Power Plant": power_name,
                "Distance (Road, km)": round(distance_km, 1)
            })

# Export to CSV
df_supplier_distances = pd.DataFrame(rows)
df_supplier_distances.to_csv("cement_supplier_distances_longform.csv", index=False)
print("✅ Saved as 'cement_supplier_distances_longform.csv'")


# Add Layer Control
LayerControl(collapsed=False).add_to(m)

# Save map
m.save("cement_power_distance_range_full.html")
print("✅ Map saved as 'cement_power_distance_range_map.html'")
