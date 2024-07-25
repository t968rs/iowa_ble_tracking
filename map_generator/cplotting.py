import os
import folium
import geopandas as gpd
from pathlib import Path
from folium.features import DivIcon

blue_lines_override = """
<style>
    .leaflet-interactive { stroke: rgb(247,247,247); stroke-width: 1; fill-opacity: 0;}
</style>
"""


def lighten_color(hex_color, factor=0.1):
    """
    Lightens the given hex color by a specified factor.

    :param hex_color: Hex color string
    :param factor: Factor by which to lighten the color (0 to 1)
    :return: Lightened hex color string
    """
    # Ensure factor is between 0 and 1
    factor = max(min(factor, 1), 0)

    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    # Lighten RGB values
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)

    # Convert RGB back to hex
    return f'#{r:02x}{g:02x}{b:02x}'


stat_highlight_function = lambda x: {
    'fillColor': "rgb(247,247,247)",
    'color': "rgb(247,247,247)",  # Outline color
    'weight': 2,
    'fillOpacity': 0.5,
}

stat_color_swatches = {
    "Draft DFIRM Submitted": "#A3FF73",  # Gold
    "Mapping In-Progress": "#CACA00",  # DodgerBlue
    "Model Available": "#008FA4",  # LimeGreen
    "Model Unavailable": "#F597B6",  # OrangeRed
    "Phase 1 Delivered": "#00A884",  # SlateBlue
    "Partial": "#FF69B4",  # HotPink
}

stat_style_function = lambda x: {
    'fillColor': stat_color_swatches[x['properties']['Production']]
    if x['properties']['Production'] is not None else "blue",
    'color': "rgb(247,247,247)",
    'weight': 1,
    'fillOpacity': 0.6
}

stat_style = {'fillColor': None, 'color': "rgb(247,247,247)", 'weight': 1, 'fillOpacity': 0.6}
# Define default style for the layer
light_outline_style = {'color': "rgb(247,247,247)", 'weight': 1}
dashed_style = {'color': '#6C9600', 'weight': 2, 'dashArray': '5, 5', 'fillOpacity': 0, }
invisible_style = {'fillColor': 'rgba(0,0,0,0)', 'color': 'rgba(0,0,0,0)', 'weight': 0, 'fillOpacity': 0}


class Plotting:
    def __init__(self):
        self.target_lyr = "production_status"
        self.folder = "../data/in_data/"
        self.lyr_folder = os.path.join("../data/", "lyrs_geojson")
        os.makedirs(self.folder, exist_ok=True), os.makedirs(self.lyr_folder, exist_ok=True)
        self.map_path = "../production_status.html"
        self.data_dict = {}  # name: {gdf, fields}

        self.map = None  # Will be initialized in load_map_based_on_config

    @property
    def layer_options(self):
        return {"production_status":
                    {"type": "GeoJson", "data_source": 1,
                     "name": "Production Status",
                     "style": stat_style_function,
                     "status_field": "Production",
                     "order": 1, "control": True, "show": True, "interactive": False},
                "highlights":
                    {"name": "Highlights", "type": "GeoJson", "data_source": 1,
                     "style": invisible_style, "highlight_function": stat_highlight_function,
                     "tooltips": ["Production", "Mapping", "Fnl_Model"],
                     "popups": 1, "interactive": True, "order": 0, "show": True},
                "state_boundary": {"type": "GeoJson", "data_source": 1,
                                   "name": "State Boundary",
                                   "style": dashed_style,
                                   "interactive": False, "order": 2, "control": True, "show": True}
                }

    def _init_input_data(self):
        infile_dict = {}
        for root, dirs, files in os.walk(self.folder):
            for file in files:
                if file.endswith(".shp"):
                    path = Path(root, file).as_posix()
                    infile_dict[path] = {}
        for path, info in infile_dict.items():
            if isinstance(path, str):
                name = os.path.split(path)[1].split(".")[0]
                gdf = gpd.read_file(path).to_crs(epsg=4326)
                self.data_dict[name] = {"gdf": gdf, "fields": [], "geojson": None, "style": None}
            elif isinstance(path, gpd.GeoDataFrame):
                self.data_dict[path] = {"gdf": path.to_crs(epsg=4326), "fields": [], "geojson": None, "style": None}
            else:
                raise ValueError("Input data must be a path to a GeoDataFrame or a GeoDataFrame itself")

    def _limit_all_bounds(self):
        target_lyr = self.data_dict[self.target_lyr]["gdf"]
        self.bounds_limiter = [float(c) for c in target_lyr.geometry.total_bounds]
        self.bounds_fit, self.centroid = self.get_bounds_fit_from_bounds(self.bounds_limiter)
        print(f" Bounds Limiter: {self.bounds_limiter}")

        # Limit extents of the input data to the target layer bounds
        minx, miny, maxx, maxy = self.bounds_limiter
        for name, data in self.data_dict.items():
            if name == self.target_lyr:
                continue
            else:
                gdf = data["gdf"]
                gdf = gdf.cx[minx:maxx, miny:maxy]
                self.data_dict[name]["gdf"] = gdf

    def _export_geojson(self):
        for name, data in self.data_dict.items():
            geojson_path, fields = self._exp_geojson(data["gdf"], self.lyr_folder, name)
            self.data_dict[name]["geojson"] = geojson_path
            self.data_dict[name]["fields"] = fields

    @staticmethod
    def get_bounds_fit_from_bounds(bounds):

        southwest = [bounds[1], bounds[0]]
        northeast = [bounds[3], bounds[2]]
        centroid = [(southwest[0] + northeast[0]) / 2, (southwest[1] + northeast[1]) / 2]
        return [southwest, northeast], centroid

    @staticmethod
    def get_bounds_from_bounds_fit(bounds_fit):
        return [bounds_fit[0][1], bounds_fit[0][0], bounds_fit[1][1], bounds_fit[1][0]]

    @staticmethod
    def _exp_geojson(gdf, folder, lyr_name):
        geojson_path = os.path.normpath(os.path.join(folder, f"{lyr_name}.geojson"))
        print(f"Exporting {lyr_name} to {geojson_path}")
        gdf.to_file(geojson_path, driver='GeoJSON')
        fields = [c for c in gdf.columns if c not in
                  ["geometry", "FID", "Shape", "Shape_Length", "Shape_Area"]]
        return geojson_path, fields

    @staticmethod
    def get_tooltip(fields):

        return folium.GeoJsonTooltip(
            fields=fields,
            localize=True,
            sticky=False,
            labels=True,
            style="""
                background-color: #F0EFEF;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
            """,
            max_width=800,
        )

    def process_data(self):
        # Process Data
        self._init_input_data()
        for k, v in self.data_dict.items():
            print(f'{k}')
            for k2, v2 in v.items():
                if k2 != "gdf":
                    if v2:
                        print(f' has {k2}')
        self._limit_all_bounds()
        self._export_geojson()

    def get_layers(self):
        with os.walk(self.lyr_folder) as walk:
            for root, dirs, files in walk:
                for file in files:
                    if file.endswith(".geojson"):
                        path = Path(root, file).as_posix()
                        yield path

    @staticmethod
    def convert_gdf_to_pt_dict(gdf, field):
        huc8_centroids = {}
        for idx, row in gdf.iterrows():
            centroid = [float(row.geometry.centroid.y), float(row.geometry.centroid.x)]
            # print(f' Centroid: {centroid}')
            huc8_centroids[idx] = {"centroid": centroid,
                                   "Name": row[field]}
        return huc8_centroids

    def load_map(self):
        self.map = folium.Map(location=self.centroid, zoom_start=4, tiles='Esri.WorldShadedRelief')
        self.map.fit_bounds(self.bounds_fit)

        # state bounds
        folium.GeoJson(
            self.data_dict["state_boundary"]["geojson"],
            style=dashed_style,  # Use the style function here
            control=True,
            interactive=False,
            name="State Boundaries"
        ).add_to(self.map)

        # Labels for the centroids
        centroid_dict = self.convert_gdf_to_pt_dict(self.data_dict[self.target_lyr]["gdf"], "name")
        for cid, info in centroid_dict.items():
            folium.Marker(
                location=info['centroid'],
                icon=DivIcon(
                    icon_size=(150, 150),
                    icon_anchor=(45, 10),  # Adjusted to center the text
                    html=f'''
                        <div style="font-size: 12pt; color: gray; text-shadow: 0 0 4px rgba(247, 247, 247, 0.8);">
                            {info["Name"]}
                        </div>
                    '''
                ),
                interactive=False,
                control=True,
                name="HUC8 Labels"
            ).add_to(self.map)

        def apply_style(feature):
            production_status = feature['properties'].get('Production', None)
            if production_status:
                # Normalize the production status to match the dictionary keys
                production_status = production_status.strip()
                color = stat_color_swatches.get(production_status, "grey")  # Fallback color if no match found
            else:
                color = "grey"  # Default fallback color if production status is missing

            return {
                'fillColor': color,
                'color': "rgb(247,247,247)",  # Outline color
                'weight': 1,
                'fillOpacity': 0.6
            }

        # Add main production status layer with dynamic styling
        folium.GeoJson(
            self.data_dict[self.target_lyr]["gdf"],
            style_function=apply_style,  # Use the style function here
            control=True,
            name="Production Status"
        ).add_to(self.map)

        # Add invisible with tooltips and popups
        tfields = ["Production", "Mapping", "Fnl_Model"]
        tooltip = self.get_tooltip(tfields)
        popup = folium.GeoJsonPopup(fields=self.data_dict[self.target_lyr]["fields"], localize=True)
        folium.GeoJson(
            self.data_dict[self.target_lyr]["geojson"],
            style=invisible_style,
            highlight_function=stat_highlight_function,
            tooltip=tooltip,
            popup=popup,
            control=True,
            name="Popups"
        ).add_to(self.map)

        folium.LayerControl().add_to(self.map)
        # self._save_map_config()

        # self.map.get_root().html.add_child(folium.Element(blue_lines_override))
        self.map.save(self.map_path)


if __name__ == "__main__":
    plotter = Plotting()
    plotter.process_data()
    plotter.load_map()
