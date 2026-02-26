import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
from typing import Union, List, Iterable

class RegionMap:
    def __init__(self, shapefile_path: str, region_col: str = "REGION", province_col: str = "PROVINCE", 
                 ccaa_col: str = "CCAA", codnut2_col: str = "CODNUT2", codnut3_col: str = "CODNUT3"):
        """
        """
        self.shapefile_path = shapefile_path
        self.region_col = region_col
        self.province_col = province_col
        self.ccaa_col = ccaa_col
        self.codnut2_col = codnut2_col
        self.codnut3_col = codnut3_col

        self.gdf = gpd.read_file(self.shapefile_path)
        # secure columns in string types
        for col in (self.region_col, self.province_col, self.ccaa_col, self.codnut2_col, self.codnut3_col):
            if col in self.gdf.columns:
                self.gdf[col] = self.gdf[col].astype(str)
            else:
                raise KeyError(f"The shapefile does not have the expected column: '{col}'")

        # normalize indices by regions (without removing duplicates)
        self.gdf = self.gdf.reset_index(drop=True)
        self._build_mappings()
        self.graph_reg = self._build_region_graph()
        self.graph_prov = self._build_province_graph()
        self.graph_ccaa = self._build_ccaa_graph()

    def _build_mappings(self):
        """
        """
        # ccaa -> CODNUT2 (if there are several provinces with the same CCAA, we take the first CODNUT2 found)
        self.ccaa_to_codnut2 = {}
        self.province_to_codnut3 = {}

        for _, row in self.gdf.iterrows():
            ccaa = row[self.ccaa_col]
            prov = row[self.province_col]
            cod2 = row[self.codnut2_col]
            cod3 = row[self.codnut3_col]

            if ccaa not in self.ccaa_to_codnut2 and cod2:
                self.ccaa_to_codnut2[ccaa] = cod2
            if prov not in self.province_to_codnut3 and cod3:
                self.province_to_codnut3[prov] = cod3
        
    def _build_region_graph(self):
        """
        """
        G = nx.Graph()
        gdf = self.gdf[[self.region_col, "geometry"]].copy()
        gdf = gdf.reset_index(drop=True)

        # add nodes
        for reg in gdf[self.region_col].tolist():
            G.add_node(reg)
        
        # check pairs
        for i, row in gdf.iterrows():
            reg_i = row[self.region_col]
            geom_i = row.geometry
            for j, row2 in gdf.iloc[i+1:].iterrows():
                reg_j = row2[self.region_col]
                geom_j = row2.geometry
                # use of touches or intersections to consider shared boundaries or overlaps
                try:
                    if geom_i.touches(geom_j) or geom_i.intersects(geom_j):
                        G.add_edge(reg_i, reg_j)
                except Exception:
                    # robustness against invalid geometries
                    if geom_i.buffer(0).touches(geom_j.buffer(0)) or geom_i.buffer(0).intersects(geom_j.buffer(0)):
                        G.add_edge(reg_i, reg_j)
        return G

    def _build_province_graph(self):
        """
        """
        G = nx.Graph()
        gdf = self.gdf[[self.province_col, "geometry"]].copy()
        gdf = gdf.reset_index(drop=True)

        # add nodes
        for prov in gdf[self.province_col].tolist():
            G.add_node(prov)

        # check pairs
        for i, row in gdf.iterrows():
            prov_i = row[self.province_col]
            geom_i = row.geometry
            for j, row2 in gdf.iloc[i+1:].iterrows():
                prov_j = row2[self.province_col]
                geom_j = row2.geometry
                # use of touches or intersections to consider shared boundaries or overlaps
                try:
                    if geom_i.touches(geom_j) or geom_i.intersects(geom_j):
                        G.add_edge(prov_i, prov_j)
                except Exception:
                    # robustness against invalid geometries
                    if geom_i.buffer(0).touches(geom_j.buffer(0)) or geom_i.buffer(0).intersects(geom_j.buffer(0)):
                        G.add_edge(prov_i, prov_j)
        return G

    def _build_ccaa_graph(self):
        """
        """
        G = nx.Graph()
        ccaa_groups = {ccaa: self.gdf[self.gdf[self.ccaa_col] == ccaa] for ccaa in self.gdf[self.ccaa_col].unique()}

        for ccaa in ccaa_groups:
            G.add_node(ccaa)

        ccaa_list = list(ccaa_groups.keys())
        for i, ccaa_i in enumerate(ccaa_list):
            geoms_i = ccaa_groups[ccaa_i].geometry.union_all()
            for ccaa_j in ccaa_list[i+1:]:
                geoms_j = ccaa_groups[ccaa_j].geometry.union_all()
                try:
                    if geoms_i.touches(geoms_j) or geoms_i.intersects(geoms_j):
                        G.add_edge(ccaa_i, ccaa_j)
                except Exception:
                    if geoms_i.buffer(0).touches(geoms_j.buffer(0)) or geoms_i.buffer(0).intersects(geoms_j.buffer(0)):
                        G.add_edge(ccaa_i, ccaa_j)
        return G
    
    def _reg_subgraph_connected(self, region_names: Iterable[str]) -> bool:
        """
        """
        selected = [r for r in region_names if r in self.graph_reg.nodes]
        if not selected:
            return False
        sub = self.graph_reg.subgraph(selected)
        return nx.is_connected(sub)

    def _provinces_subgraph_connected(self, province_names: Iterable[str]) -> bool:
        """
        """
        selected = [p for p in province_names if p in self.graph_prov.nodes]
        if not selected:
            return False
        sub = self.graph_prov.subgraph(selected)
        return nx.is_connected(sub)

    def _ccaa_subgraph_connected(self, ccaa_names: Iterable[str]) -> bool:
        """
        """
        selected = [c for c in ccaa_names if c in self.graph_ccaa.nodes]
        if not selected:
            return False
        sub = self.graph_ccaa.subgraph(selected)
        return nx.is_connected(sub)

    def select_regions(self, selection: Union[str, List[str], None]):
        """
        """
        gdf = self.gdf.copy()
        # for all regions
        if selection == 'all' or not selection:
            # exclude the Canary Islands for all regions
            penins_baleares = gdf[~gdf[self.ccaa_col].str.contains("Canarias", case=False)]
            return penins_baleares.copy()
        
        # normalize input
        if isinstance(selection, str):
            selection_list = [selection]
        elif isinstance(selection, (list, tuple, set)):
            selection_list = list(selection)
        else:
            raise ValueError("Selection must be 'all', None, a string (region) or a list of regions.")
        
        # check that all regions exist in the shapefile
        missing = [r for r in selection_list if r not in gdf[self.region_col].values]
        if missing:
            raise ValueError(f"The following provinces do not exist in the shapefile: {missing}")
        
        # for a single region: paint only that region
        if len(selection_list) == 1:
            reg = selection_list[0]
            return gdf[gdf[self.region_col] == reg].copy()
        
        # if the regions form a connected subgraph: only plot those regions
        if self._reg_subgraph_connected(selection_list):
            return gdf[gdf[self.region_col].isin(selection_list)].copy()
        
        # if all regions belong to the same province: paint all regions of that province
        provinces_set = set(gdf[gdf[self.region_col].isin(selection_list)][self.province_col].unique())
        if len(provinces_set) == 1:
            provinces = list(provinces_set)[0]
            return gdf[gdf[self.province_col] == provinces].copy()
        
        # if regions are in different provinces but the provinces form a connected subgraph: plot all the regions of those provinces
        if self._provinces_subgraph_connected(provinces_set):
            return gdf[gdf[self.province_col].isin(provinces_set)].copy()

        # if regions are in different provinces and the provinces do not form a connected subgraph, but provinces are in the same CCAA: plot all the regions of that CCAA
        ccaa_set = set(gdf[gdf[self.region_col].isin(selection_list)][self.ccaa_col].unique())
        if len(ccaa_set) == 1:
            ccaa = list(ccaa_set)[0]
            return gdf[gdf[self.ccaa_col] == ccaa].copy()

        # if regions are in different provinces and the provinces do not form a connected subgraph, but CCAA yes: plot all the regions of those CCAA
        if self._ccaa_subgraph_connected(ccaa_set):
            return gdf[gdf[self.ccaa_col].isin(ccaa_set)].copy()
        
        # default case: paint everything
        return gdf[~gdf[self.ccaa_col].str.contains("Canarias", case=False)].copy()

    def plot(self, selection: Union[str, List[str], None] = "all",
             figsize: tuple = (12, 10), show: bool = True, save_path: str = None):
        """
        """
        selected_gdf = self.select_regions(selection)
        fig, ax = plt.subplots(figsize=figsize)

        # if it is a single region: plot that one
        if isinstance(selection, str) and selection != 'all':
            # single region
            selected_gdf.plot(ax=ax, color="white", edgecolor="black")
        elif isinstance(selection, (list, tuple, set)) and len(selection) == 1:
            selected_gdf.plot(ax=ax, color="white", edgecolor="black")
        else:
            # default: white with black border
            selected_gdf.plot(ax=ax, color="white", edgecolor="black")

        ax.set_axis_off()
        if save_path:
            fig.savefig(save_path, bbox_inches='tigh', dpi=150)
        if show:
            plt.show()
        plt.close(fig)
        return selected_gdf

# test
if __name__ == "__main__":

    SHP_PATH = r"C:\Users\acer\Desktop\facility-location-problem-code\flpsolve\maps\SHP_ETRS89\Regions\Regions.shp"

    rm = RegionMap(SHP_PATH)

    # paint only one region
    rm.plot("Eume")

    # paint only regions bordering lines 
    rm.plot(["Eume", "Ferrol"])

    # if the regions are not bordering but they are from the same province, paint that province
    rm.plot(["Eume", "A Coruña"])

    # if the regions are not bordering, but from bordering provinces, paint only those provinces
    rm.plot(["Eume", "Lugo"])

    # if the regions and provinces are both not bordering but they are from the same CCAA, paint only that CCAA
    rm.plot(["Eume", "Ourense"])

    # if the regions and provinces are both not bordering, but from bordering CCAA, paint only those CCAA
    rm.plot(["Eume", "Caudal"])

    # if the regions, provinces and CCAA are not bordering, paint all the Spain map
    rm.plot(["Eume", "Santander"])

    # paint all regions Spain map
    rm.plot("all")