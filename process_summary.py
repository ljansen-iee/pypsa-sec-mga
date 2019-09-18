import pandas as pd
import numpy as np
import logging
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

def get_installed_capacities(raw_results, esom, cost=True):
    df = raw_results
    cap_df = pd.DataFrame()

    cap_df["PV-ground.el"] = df["DE solar"] * 0.5
    
    cap_df["PV-roof.el"] = df["DE solar"] * 0.5 + df["DE solar-rooftop"]   
    
    cap_df["Onwind.el"] = df["DE0 onwind"].values + df["DE1 onwind"].values + df["DE2 onwind"].values
    
    cap_df["Offwind.el"] = df["DE offwind"]
    
    cap_df["OCGT.el"] = df["DE OCGT"] * esom.links.efficiency["DE central CHP electric"]
    
    cap_df["Bat.el"] = df["DE battery discharger"] * esom.links.efficiency["DE battery discharger"]
    
    cap_df["Hydro.el"] = df["DE ror"].values + df["DE hydro"]
    
    cap_df["PHS.el"] = df["DE PHS"] * esom.storage_units.efficiency_dispatch["DE PHS"]
    
    cap_df["FC.el"] = df["DE H2 Fuel Cell"] * esom.links.efficiency["DE H2 Fuel Cell"]
    
    cap_df["HE.el"] = df["DE H2 Electrolysis"] #NB: the only value that represents input power capacity and not output power capacity. 
    
    cap_df["MT.ch4"] = df["DE Sabatier"] * esom.links.efficiency["DE Sabatier"]
    
    cap_df["CHP.el.th"] = df["DE central CHP electric"] * esom.links.efficiency["DE central CHP electric"] # NB: ratio between heat and electricity output is one.
    
    cap_df["Boiler.th"] = df["DE gas boiler"] * esom.links.efficiency["DE gas boiler"] + df["DE central gas boiler"] * esom.links.efficiency["DE central gas boiler"]
    
    cap_df["HP.th"] = df["DE central heat pump"].values * esom.links_t.efficiency["DE central heat pump"].max() + df["DE ground heat pump"].values * esom.links_t.efficiency["DE central heat pump"].max()
    
    cap_df["RH.th"] = df["DE resistive heater"].values * esom.links.efficiency["DE resistive heater"] + df["DE central resistive heater"].values * esom.links.efficiency["DE central resistive heater"]
    
    cap_df["Solar.th"] = df["DE central solar thermal collector"].values + df["DE solar thermal collector"].values
    
    cap_df["THS.th"] = df["DE water tanks discharger"].values * esom.links.efficiency["DE water tanks discharger"] + df["DE central water tanks discharger"].values * esom.links.efficiency["DE central water tanks discharger"]
    
    if cost:
        cap_df["COST %"] = df["Cost [%]"] * 1e5
        
    return (cap_df / 1e3).round(0)


def get_cap_df_el_th(cap_df, ending):
    cap_df_el = pd.DataFrame()
    
    for column in cap_df.columns:
        if ending in column:
            cap_df_el[column[:-3]] = cap_df[column]
    return cap_df_el

def build_small_subset(df, techs, number=7):
    """ returns an index list for a subset of solutions """

    
    def euclidean(s1_vector, s2_vector): 
        """ returns one euclidean distance """
        dist_vector = s2_vector - s1_vector
        euclidean_distance = (dist_vector*dist_vector).sum()**0.5
        if euclidean_distance == 0.:
            return euclidean_distance + 1e-6
        return euclidean_distance
    
    solution_selected = [df.index[df['COST %'] == df["COST %"].min()][0]]
    
    df_wo_cost = (df.loc[:, techs] / df.loc[:, techs].mean()) # normalize
    
    # calculates series of euclidean distances
    dist=df_wo_cost.apply(lambda row: euclidean(df_wo_cost.loc[solution_selected[0],:].values, row.values), axis=1)

    
    logger.info(" Add first solution")
    # add first solution
    solution_selected.append(dist.idxmax())
            
    def harmonic_mean(j_row_values, solution_selected, df_wo_cost):
        """ returns the distance between one solution j 
        and all already selected solutions k """
        return sum(1/euclidean(df_wo_cost.loc[k,:].values, j_row_values) 
                   for k in  solution_selected)**-1

    for _ in range(number-1):
        dist=df_wo_cost.apply(
            lambda row: harmonic_mean(j_row_values=row.values,
                                      solution_selected=solution_selected,
                                      df_wo_cost=df_wo_cost),
            axis=1)
        logger.info(f" Add solution number {_+2}")
        # add number of solutions consecutively
        solution_selected.append(dist.idxmax())
        
    return solution_selected