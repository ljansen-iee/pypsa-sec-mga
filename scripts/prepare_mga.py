import pandas as pd
idx = pd.IndexSlice
import numpy as np
import pyomo.environ as pe
import pypsa
import logging
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

def techs_n_groups_n(mga_groups):
    
    techs = [gen for group in mga_groups["generators"] for gen in group] \
                +[link for group in mga_groups["links"] for link in group]\
                +[store for group in mga_groups["stores"] for store in group]

    n_techs = len(techs)

    groups = [group for group in mga_groups["generators"]] \
            +[group for group in mga_groups["links"]] \
            +[group for group in mga_groups["stores"]]

    n_groups = len(groups)

    return techs, n_techs, groups, n_groups

def make_mga_weights(mga_groups): 
    """
    mga_groups: dict
       e.g. mga_groups = {
            "generators": [["DE0 onwind", "DE1 onwind", "DE2 onwind"],
                     ["DE offwind"], 
                     ["DE solar", "DE solar-rooftop"],
                     ["DE solar thermal collector", "DE central solar thermal collector"],
                    ],
            "links": [["DE OCGT"], 
                      ["DE H2 Electrolysis"],
                      ["DE H2 Fuel Cell"],
                      ["DE Sabatier"],
                      ["DE battery charger"], 
                      ["DE central heat pump"],
                      ["DE ground heat pump"],
                      ["DE resistive heater"],
                      ["DE central resistive heater", "DE industrial resistive heater"],
                      ["DE gas boiler"],
                      ["DE central gas boiler", "DE industrial gas boiler"],
                      ["DE central CHP electric", "DE industrial CHP electric"]
                     ],
            "stores": [["DE gas Store"]]
        }
    """
    
    techs, n_techs, groups, n_groups = techs_n_groups_n(mga_groups)

    m=n_groups*2 #rows

    mga_weights = pd.DataFrame(np.zeros((m,n_techs)), 
                               columns=techs, 
                               index=range(m))

    for i,m in enumerate(range(0,m,2)):
        for tech in groups[i]:
            mga_weights.at[m,tech] = 1
            mga_weights.at[m+1,tech] = -1
        
    print(f"length of mga_weight dataframe: {len(mga_weights)}")     
    return mga_weights

def apply_mga_structure(es, mga_groups, mga_weights):
    """ 
    Changes the model structure: 
        Express the adjusted cost function value as an upper bound constraint
        Define an alternative objective function
    """
    
    techs, n_techs, groups, n_groups = techs_n_groups_n(mga_groups)
    
    logger.info("Changing the model structure") #logger.info

    mod = es.model

    mod.cost_minimum = pe.Param(initialize=mod.objective.expr())

    mod.cost_function_expr = mod.objective.expr

    mod.slack = pe.Param(initialize=1., mutable=True)

    mod.cost_budget = pe.Constraint(
            expr=mod.cost_function_expr <= mod.cost_minimum * mod.slack
            )

    mod.mga_techs = pe.Set(initialize=mga_weights.columns)

    mod.mga_weight = pe.Param(
                mod.mga_techs, 
                initialize = mga_weights.loc[0,:].to_dict(),
                mutable=True)


    mod.mga_function_expr = 0
    
    for gen_group in mga_groups["generators"]:
        for gen in gen_group:
            mod.mga_function_expr += mod.mga_weight[gen] * mod.generator_p_nom[gen]
    
    for link_group in mga_groups["links"]:
        for link in link_group:
            mod.mga_function_expr += mod.mga_weight[link] * mod.link_p_nom[link]    

    snapshots = es.snapshots
    for store_group in mga_groups["stores"]:
        for store in store_group:
            mod.mga_function_expr += (mod.mga_weight[store] 
                                        * sum(mod.store_p[store, sn] for sn in snapshots))

    mod.del_component(mod.objective)
    mod.objective = pe.Objective(expr= mod.mga_function_expr)


pypsa.Network.apply_mga_structure = apply_mga_structure