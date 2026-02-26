import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx

class CCAAMap:
    """
    
    """
    def __init__(self, shapefile_path):
        """
        Initializes the object with the required parameters.
        :param shapefile_path: Path direction to the file supported in GeoPandas
        """
        self.gdf = gpd.read_file(shapefile_path)
        self.gdf = self.gdf.set_index('CCAA')
        # build a graph of neighborss
        self.graph = self._build_graph()

    def _build_graph(self):
        """

        """
        G = nx.Graph()
        for ccaa, geom in self.gdf.geometry.items():
            G.add_node(ccaa)
            for other_ccaa, other_geom in self.gdf.geometry.items():
                if ccaa == other_ccaa:
                    continue
                # consider neighbors if the polygons touch or intersect.
                if geom.touches(other_geom) or geom.intersects(other_geom):
                    G.add_edge(ccaa, other_ccaa)
        return G

    def plot(self, ccaa_list='all', figsize=(12,10)):
        """
        """
        gdf = self.gdf.copy()
        
        if ccaa_list == 'all' or not ccaa_list:
            penins_baleares = gdf[~gdf.index.isin(['Canarias'])]
            fig, ax = plt.subplots(figsize=figsize)
            penins_baleares.plot(ax=ax, color='white', edgecolor='black')
            plt.show()
            return

        if isinstance(ccaa_list, str):
            ccaa_list = [ccaa_list]

        selected_set = set(ccaa_list)
        # extract connected subgraphs
        subgraphs = list(nx.connected_components(self.graph.subgraph(selected_set)))
        
        if len(subgraphs) == 1:
            # they are all transitively connected
            selected = gdf.loc[list(selected_set)]
        else:
            # not all connected: paint everything
            selected = gdf[~gdf.index.isin(['Canarias'])]

        fig, ax = plt.subplots(figsize=figsize)
        ax.set_axis_off()
        selected.plot(ax=ax, color='white', edgecolor='black')
        plt.show()


# test
if __name__ == '__main__':
    # rute of the shapefile
    shapefile_path = r"C:\Users\acer\Desktop\facility-location-problem-code\flpsolve\maps\SHP_ETRS89\Autonomics\Autonomics.shp"
    
    spain_map = CCAAMap(shapefile_path)
    
    # paint only one CCAA
    spain_map.plot('Galicia')
    
    # paint only CCAA bordering lines
    spain_map.plot(['Galicia', 'Castilla y León', 'Principado de Asturias'])
    
    # if the CCAA are not bordering lines, paint all the CCAA 
    spain_map.plot(['Galicia', 'Andalucía'])
    
    # paint all CCAA Spain map
    spain_map.plot('all')