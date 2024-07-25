from rasterio import open as ro
from rasterio.crs import CRS
import geopandas as gpd


class CheckCRSmatch:
    def __init__(self):
        self.file_list = []
        self.file_dict = {}
        self.crs = None
        self.crs_dict = {}

    def _init_file_dict(self):
        from iowa_ble_tracking.src.d00_utils import get_extension
        ext_dict = {}
        for path in self.file_list:
            p_extension = get_extension(path)
            # print(f'Path {path}, \n  Ext: {p_extension}')
            ext_dict[path] = p_extension
        # print(f"Extensions: \n{ext_dict}")
        self.file_dict = ext_dict

    def _record_all_crs(self):

        if self.file_dict is not None:
            # print(f"File Dict: {self.file_dict}")
            for path, ext in self.file_dict.items():
                # print(f" Ext: {ext}")
                if ext == ".shp":
                    gdf = gpd.read_file(path)
                    crs = CRS(gdf.crs)
                    self.crs_dict[path] = crs
                elif ext in [".tif", ".img"]:
                    # print(f"Path: {path}")
                    with ro(path, "r") as raster:
                        crs = raster.crs
                        print(f'    Found CRS: {crs}')
                        self.crs_dict[path] = crs
                else:
                    self.crs_dict[path] = None

    def check_all_match(self, pathlist):
        self.file_list = pathlist
        # print(f' File List: {self.file_list}')
        self._init_file_dict()
        self._record_all_crs()

        # Compare all CRS
        crs_comparison = None
        match = None
        for path, crs_obj in self.crs_dict.items():
            if crs_comparison is None:
                crs_comparison = crs_obj
                match = False
            elif crs_comparison == crs_obj:
                match = True
            else:
                match = False
                break

        # return matching or not
        if match:
            return True
        else:
            # print(f'Some CRS do not match')
            # for k, v in self.crs_dict.items():
            # print(f"{k}, \n  {v}")
            return False


def check_crs_match_from_list(pathlist):
    return CheckCRSmatch().check_all_match(pathlist)
