import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import networkx as nx

class ImprovedMap:
    """
    """
    # order of geographic levels 
    level_order = ["autonomics", "provinces", "regions", "municipalities"]

    def __init__(self, shp_dir=None, epsg=None, gdf_aut=None, gdf_prov=None, gdf_reg=None, gdf_muni=None):
        """
        """
        self.shp_dir = shp_dir
        self.epsg = epsg

        # load shapefiles or use provided GeoDataFrames
        self.gdf_aut = gdf_aut if gdf_aut is not None else self._maybe_read("Autonomics")
        self.gdf_prov = gdf_prov if gdf_prov is not None else self._maybe_read("Provinces")
        self.gdf_reg = gdf_reg if gdf_reg is not None else self._maybe_read("Regions")
        self.gdf_muni = gdf_muni if gdf_muni is not None else self._maybe_read("Municipalities")

        # reproject to desired EPSG
        if self.epsg is not None:
            for attr in ("gdf_aut","gdf_prov","gdf_reg","gdf_muni"):
                g = getattr(self, attr)
                if g is not None and not g.empty:
                    try:
                        g = g.to_crs(epsg=self.epsg)
                        setattr(self, attr, g)
                    except Exception:
                        pass

        # store last selection
        self.selected = None
        self.filtered_muni = None

        # list of valid names for each level
        self.valid = {
            "autonomics": sorted(self.gdf_aut["CCAA"].dropna().unique().tolist()) if self.gdf_aut is not None else [],
            "provinces": sorted(self.gdf_prov["PROVINCE"].dropna().unique().tolist()) if self.gdf_prov is not None else [],
            "regions": sorted(self.gdf_reg["REGION"].dropna().unique().tolist()) if self.gdf_reg is not None else [],
            "municipalities": sorted(self.gdf_muni["MUNI"].dropna().unique().tolist()) if self.gdf_muni is not None else []
        }

    def _maybe_read(self, base_name):
        """
        """
        if not self.shp_dir:
            return None
        candidate = os.path.join(self.shp_dir, base_name)
        if os.path.exists(candidate + ".shp"):
            candidate += ".shp"
        if os.path.exists(candidate):
            try:
                return gpd.read_file(candidate)
            except Exception:
                return None
        return None

    @staticmethod
    def _ensure_list(x):
        """
        """
        if x is None:
            return []
        return x if isinstance(x, (list, tuple)) else [x]

    @staticmethod
    def dict_to_gdf(data_dict, epsg=None):
        """
        """
        if data_dict is None:
            return None
        df = pd.DataFrame.from_dict(data_dict, orient="index").reset_index(drop=True) if isinstance(data_dict, dict) else pd.DataFrame(data_dict)
        if "lon" not in df.columns or "lat" not in df.columns:
            if {"x","y"}.issubset(df.columns):
                df = df.rename(columns={"x":"lon","y":"lat"})
            else:
                cand = [c for c in df.columns if c.lower() in ("lon","longitude","x")]
                cand2 = [c for c in df.columns if c.lower() in ("lat","latitude","y")]
                if cand and cand2:
                    df = df.rename(columns={cand[0]:"lon", cand2[0]:"lat"})
                else:
                    raise ValueError("No lon/lat columns found in the points")
        geo = gpd.GeoDataFrame(df, geometry=[Point(x,y) for x,y in zip(df.lon, df.lat)], crs="EPSG:4326")
        return geo.to_crs(epsg=epsg) if epsg else geo

    def _get_gdf(self, level, names):
        """
        """
        names = self._ensure_list(names)
        if not names:
            return gpd.GeoDataFrame(columns=["geometry"])
        mapping = {
            "autonomics": ("CCAA", self.gdf_aut),
            "provinces": ("PROVINCE", self.gdf_prov),
            "regions": ("REGION", self.gdf_reg),
            "municipalities": ("MUNI", self.gdf_muni)
        }
        col, gdf = mapping.get(level, (None, None))
        return gdf[gdf[col].isin(names)].reset_index(drop=True) if gdf is not None else gpd.GeoDataFrame(columns=["geometry"])

    def _is_contiguous(self, gdf):
        """
        """
        if gdf is None or len(gdf) == 0:
            return False
        try:
            u = gdf.geometry.union_all()
            return getattr(u, "geom_type", "") not in ("MultiPolygon", "GeometryCollection")
        except Exception:
            return False

    def _adjacency_graph(self, gdf, tolerance=0.0):
        """
        """
        G = nx.Graph()
        for i in range(len(gdf)):
            G.add_node(i)
        for i in range(len(gdf)):
            for j in range(i+1, len(gdf)):
                ga = gdf.geometry.iloc[i]
                gb = gdf.geometry.iloc[j]
                try:
                    if ga.touches(gb) or ga.intersects(gb) or ga.distance(gb) <= tolerance:
                        G.add_edge(i, j)
                except Exception:
                    pass
        return G

    def _map_decide_scope(self, selected_gdf, level_used):
        """
        """
        if selected_gdf is None or len(selected_gdf) == 0:
            return None, None, "empty_selection"
        
        if level_used in ("provinces", "regions", "municipalities"):
            return selected_gdf, level_used, f"selected_{level_used}"
        
        if self._is_contiguous(selected_gdf):
            return selected_gdf, level_used, "selected_contiguous"
        
        if self.gdf_aut is None:
            return selected_gdf, level_used, "no_autonomy_layer_present"
        
        if "CCAA" in selected_gdf.columns:
            aut_set = set(selected_gdf["CCAA"].dropna().unique())
        else:
            try:
                join = gpd.sjoin(selected_gdf, self.gdf_aut[["CCAA","geometry"]], how="left", predicate="within")
                aut_set = set(join["CCAA"].dropna().unique())
            except Exception:
                aut_set = set()

        if len(aut_set) == 1:
            aut_name = next(iter(aut_set))
            return self.gdf_aut[self.gdf_aut["CCAA"] == aut_name].reset_index(drop=True), "autonomics", "single_autonomy"
        
        aut_gdf = self.gdf_aut[self.gdf_aut["CCAA"].isin(aut_set)].reset_index(drop=True)
        if len(aut_gdf) == 0:
            return self.gdf_aut, "autonomics", "fallback_full_country"
        
        G = self._adjacency_graph(aut_gdf, tolerance=0.0)
        return (aut_gdf, "autonomics", "autonomies_connected_or_single") if len(aut_gdf)==1 or nx.is_connected(G) else (self.gdf_aut, "autonomics", "autonomies_not_connected_full_country")

    def determine_scope(self, autonomics=None, provinces=None, regions=None, municipalities=None, target_level="municipalities"):
        """
        """
        autonomics, provinces, regions, municipalities = map(self._ensure_list, [autonomics, provinces, regions, municipalities])
        selected_gdf, level_used = None, None
        if target_level == "municipalities" and municipalities:
            selected_gdf, level_used = self._get_gdf("municipalities", municipalities), "municipalities"
        elif target_level == "regions" and regions:
            selected_gdf, level_used = self._get_gdf("regions", regions), "regions"
        elif target_level == "provinces" and provinces:
            selected_gdf, level_used = self._get_gdf("provinces", provinces), "provinces"
        elif target_level == "autonomics" and autonomics:
            selected_gdf, level_used = self._get_gdf("autonomics", autonomics), "autonomics"
        else:
            for lvl, vals in zip(["autonomics","provinces","regions","municipalities"], [autonomics, provinces, regions, municipalities]):
                if vals: 
                    selected_gdf, level_used = self._get_gdf(lvl, vals), lvl
                    break
        self.selected = selected_gdf
        gdf_to_plot, level_for_layers, reason = self._map_decide_scope(selected_gdf, level_used)
        self.filtered_muni = gdf_to_plot if level_for_layers=="municipalities" else None
        return {"level_used": level_for_layers, "gdf": gdf_to_plot, "reason": reason}

    def plot_map(self, suppliers=None, plants=None, customers=None, autonomics=None, provinces=None, regions=None, municipalities=None,
                 target_level="municipalities", plot_layers=None, figsize=(10,10), annotate_municipalities=False, show=True, savepath=None):
        """
        """
        scope = self.determine_scope(autonomics, provinces, regions, municipalities, target_level)
        gdf_used = scope["gdf"]
        if gdf_used is None or len(gdf_used) == 0:
            print("No data to plot for the selection provided.")
            return scope

        # create figure
        fig, ax = plt.subplots(figsize=figsize)

        # plot the base selection with no fill
        base_gdf = gdf_used.copy()
        base_gdf.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1.2)

        # plot optional layers intersecting the base
        if plot_layers is None:
            plot_layers = {}

        layer_info = [
            ("autonomics", self.gdf_aut, 1.0, "black"),
            ("provinces", self.gdf_prov, 0.8, "grey"),
            ("regions", self.gdf_reg, 0.6, "grey"),
            ("municipalities", self.gdf_muni, 0.4, "grey")
        ]

        for layer_name, gdf_layer, width, color in layer_info:
            if plot_layers.get(layer_name, False) and gdf_layer is not None:
                # only plot intersection with selected area
                sub = gpd.overlay(gdf_layer, base_gdf, how='intersection')
                if not sub.empty:
                    sub.boundary.plot(ax=ax, linewidth=width, color=color)

        # add points (suppliers, plants, customers)
        for pts in (suppliers, plants, customers):
            if pts:
                try:
                    gpts = self.dict_to_gdf(pts, epsg=self.epsg)
                    gpts.plot(ax=ax, markersize=50)
                except Exception:
                    pass

        # annotate municipalities if desired
        if annotate_municipalities and self.filtered_muni is not None and len(self.filtered_muni) > 0:
            name_col = "NAMEUNIT" if "NAMEUNIT" in self.filtered_muni.columns else (
                        "MUNICIPIO" if "MUNICIPIO" in self.filtered_muni.columns else None
            )
            if name_col:
                for _, row in self.filtered_muni.iterrows():
                    try:
                        centroid = row.geometry.centroid
                        ax.annotate(row.get(name_col, ""), xy=(centroid.x, centroid.y),
                                    fontsize=6, color="dimgray", ha="center")
                    except Exception:
                        pass

        # remove axes
        ax.set_xticks([]); ax.set_yticks([])

        # save or show
        if savepath:
            plt.savefig(savepath, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)

        return scope



















# comunidades limitrofes: pintar solo esas dos con posibilidad de activar diferentes capas
#map.plot_map(autonomics=["Galicia", "Asturias"], target_level="autonomics") # solo autonomica
#map.plot_map(autonomics=["Galicia", "Asturias"], plot_layers={'provinces':True, 'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Asturias"],  plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Asturias"],  plot_layers={'provinces':True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Asturias"],  plot_layers={'regions': True}) #solo con capas 
#map.plot_map(autonomics=["Galicia", "Asturias"],  plot_layers={'municipalities': True}) #solo con capas 

# provincias limitrofes: pintar solo esas con posibilidad de activar diferentes capas
#map.plot_map(province=["A Coruña", "Lugo"], target_level="provinces") # solo provincia
#map.plot_map(province=["A Coruña", "Lugo"], plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Lugo"],  plot_layers={'regions': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Lugo"],  plot_layers={'municipalities': True}) #solo con capas

# comarcas limítrofes: pintar solo esas con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "Ortegal"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "Ortegal"], plot_layers={'municipalities': True}) #solo con capas

# municipios limitrofes: pintar solo eses
#map.plot_map(regions=["Pontedeume", "Miño"], target_level="municipalities") # solo comarca



# comunidades no limitrofes: pintar el mapa de españa completo (todas los datos para cada nivel) con posibilidad de activar diferentes capas
#map.plot_map(autonomics=["Galicia", "Andalucía"], target_level="autonomics") # solo autonomica
#map.plot_map(autonomics=["Galicia", "Andalucía"], plot_layers={'provinces':True, 'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Andalucía"],  plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Andalucía"],  plot_layers={'provinces':True}) #solo con capas
#map.plot_map(autonomics=["Galicia", "Andalucía"],  plot_layers={'regions': True}) #solo con capas 
#map.plot_map(autonomics=["Galicia", "Andalucía"],  plot_layers={'municipalities': True}) #solo con capas 

# provincias no limitrofes de la misma comunidad: pintar solo esa comunidad con posibilidad de activar diferentes capas
#map.plot_map(province=["A Coruña", "Ourense"], target_level="provinces") # solo provincia
#map.plot_map(province=["A Coruña", "Ourense"], plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Ourense"],  plot_layers={'regions': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Ourense"],  plot_layers={'municipalities': True}) #solo con capas

# provincias no limitrofes de diferentes comunidades, pero comunidades limitrofes: pintar solo esas comunidades con posibilidad de activar diferentes capas
#map.plot_map(province=["A Coruña", "Asturias"], target_level="provinces") # solo provincia
#map.plot_map(province=["A Coruña", "Asturias"], plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Asturias"],  plot_layers={'regions': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Asturias"],  plot_layers={'municipalities': True}) #solo con capas

# provincias no limitrofes de diferentes comunidades y comunidades no limítrofes: pintar el mapa de españa completo (todas los datos para cada nivel) con posibilidad de activar diferentes capas
#map.plot_map(province=["A Coruña", "Cantabria"], target_level="provinces") # solo provincia
#map.plot_map(province=["A Coruña", "Cantabria"], plot_layers={'regions': True, 'municipalities': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Cantabria"],  plot_layers={'regions': True}) #solo con capas
#map.plot_map(province=["A Coruña", "Cantabria"],  plot_layers={'municipalities': True}) #solo con capas



# comarcas no limítrofes de la misma provincia: pintar solo esa provincia con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "A Coruña"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "A Coruña"], plot_layers={'municipalities': True}) #solo con capas

# comarcas no limítrofes de distintas provincias, pero estas son limitrofes: pintar solo esas provincias con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "Lugo"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "Luego"], plot_layers={'municipalities': True}) #solo con capas

# comarcas no limítrofes de provincias no limitrofes, pero misma comunidad: pintar solo esa comunidad con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "Ourense"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "Ourense"], plot_layers={'municipalities': True}) #solo con capas

# comarcas no limítrofes de distintas comunidades, pero comunidades limitrofes: pintar solo esas comunidades con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "Oviedo"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "Oviedo"], plot_layers={'municipalities': True}) #solo con capas

# comarcas no limítrofes de distintas comunidades, pero comunidades no limitrofes: pintar el mapa de españa completo (todas los datos para cada nivel) con posibilidad de activar diferentes capas
#map.plot_map(regions=["Ferrol", "Terra Alta"], target_level="regions") # solo comarca
#map.plot_map(regions=["Ferrol", "Terra Alta"], plot_layers={'municipalities': True}) #solo con capas



# municipios no limitrofes de la misma provincia: pintar solo esa provincia
#map.plot_map(regions=["Pontedeume", "Cerceda"], target_level="municipalities") # solo comarca

# municipios no limítrofes de distintas provincias, pero estas son limitrofes: pintar solo esas provincias 
#map.plot_map(regions=["Pontedeume", "Lugo"], target_level="municipalities") # solo comarca

# municipios no limítrofes de provincias no limitrofes, pero misma comunidad: pintar solo esa comunidad 
#map.plot_map(regions=["Pontedeume", "Allariz"], target_level="municipalities") # solo comarca

# municipios no limitrofes de distintas comunidades, pero comunidades limitrofes: pintar solo esas comunidades 
#map.plot_map(regions=["Pontedeume", "Llaneras"], target_level="municipalities") # solo comarca

# municipios no limitrofes de distintas comunidades, pero comunidades no limitrofes: pintar el mapa de españa completo (todas los datos para cada nivel) con posibilidad de activar diferentes capas
#map.plot_map(regions=["Pontedeume", "Terrasa"], target_level="municipalities") # solo comarca