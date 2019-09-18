import pandas as pd
import itertools
import pyomo.environ as pe
import pypsa
idx = pd.IndexSlice
import logging
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

def make_options():
    """ Returns a dict with options for the model and the solver """

    options = {
        "solver": {
            "name": "gurobi_persistent",
            "options": {None}
        },
        "step": 3,
        "co2_limit": 0.,
    }

    if options['solver']['name'] == "gurobi" or options['solver']['name'] == "gurobi_persistent":
        options['solver']['options'] = {"threads" : 4,"method" : 2,"crossover" : 0,"BarConvTol": 1.e-3,"FeasibilityTol": 1.e-3 }
    if options['solver']['name'] == "cplex":
        options['solver']['options'] = {"lpmethod":4,"threads":4,"simplex tolerances optimality":1e-3,"solutiontype":2}
        
    return options


def annuity(lifetime,discount_rate):
    """ Returns the annuity factor """

    if discount_rate == 0.:
        return 1/lifetime
    else:
        return discount_rate/(1. - 1. / (1. + discount_rate)**lifetime)
    

def prepare_costs(file_name = "pypsa-eur-sec-30/data/costs/costs.csv", number_years=1, usd_to_eur=1/1.2, costs_year=2030):
    """ Returns a pd.DataFrame with model-ready asset costs and other parameters """

    costs = pd.read_csv(file_name, index_col=[0,1,2]).sort_index()

    #correct units to MW and EUR
    costs.loc[costs.unit.str.contains("/kW"),"value"]*=1e3
    costs.loc[costs.unit.str.contains("USD"),"value"]*=usd_to_eur

    costs = costs.loc[idx[:,costs_year,:],"value"].unstack(level=2)

    #fill defaults
    costs = costs.fillna({"CO2 intensity" : 0,
                          "FOM" : 0,
                          "VOM" : 0,
                          "discount rate" : 0.07,
                          "efficiency" : 1,
                          "fuel" : 0,
                          "investment" : 0,
                          "lifetime" : 25
    })

    #annualise investment costs and add FOM
    costs["fixed"] = [(
        annuity(v["lifetime"],v["discount rate"]) \
            +v["FOM"]/100.)*v["investment"]*number_years 
            for i,v in costs.iterrows()
            ]

    return costs

def extra_functionality(esom,snapshots):
    '''
    Adds extra technical constraints to the standard pypsa formulation. 

    Modified version of pypsa-eur-sec-30/scripts/solve_network.py -> extra_functionality
    '''
    
    def battery_charge_discharge(model):
        return model.link_p_nom["DE battery charger"] == \
                model.link_p_nom["DE battery discharger"]*esom.links.at["DE battery charger","efficiency"]
    esom.model.battery_charge_discharge = pe.Constraint(rule=battery_charge_discharge)
    
    #ratio between max heat output and max electric output
    nom_r = 1.
            
    #backpressure limit
    c_m = 0.75
            
    #marginal loss for each additional generation of heat
    # c_v = 0.15  # is already applied, see prepare_network: options['chp_parameters']['eta_elec']/options['chp_parameters']['c_v']
    
    #Guarantees heat output and electric output nominal powers are proportional
    def chp_nom_propotion(model):
        return nom_r*esom.links.at["DE central CHP electric","efficiency"]*model.link_p_nom["DE central CHP electric"] == \
                esom.links.at["DE central CHP heat","efficiency"]*model.link_p_nom["DE central CHP heat"]
    esom.model.chp_nom_propotion = pe.Constraint(rule=chp_nom_propotion)

    #Guarantees c_m p_b1  leq  p_g1
    def chp_backpressure(model,snapshot):
        return c_m*esom.links.at["DE central CHP heat","efficiency"]*model.link_p["DE central CHP heat",snapshot] <= \
                esom.links.at["DE central CHP electric","efficiency"]*model.link_p["DE central CHP electric",snapshot] 
    
    esom.model.chp_backpressure = pe.Constraint(list(snapshots),rule=chp_backpressure)
    
    #Guarantees p_g1 +c_v p_b1  leq  p_g1_nom
    def chp_top_iso_fuel_line(model,snapshot):
        return model.link_p["DE central CHP heat",snapshot] + model.link_p["DE central CHP electric",snapshot] <= \
                model.link_p_nom["DE central CHP electric"]
    
    esom.model.chp_top_iso_fuel_line = pe.Constraint(list(snapshots),rule=chp_top_iso_fuel_line)


def make_slacks_mga_weights(mga_n, slacks=[1.01, 1.02, 1.05, 1.1]):
    """ Returns a tidy pd.DataFrame that contains slack and mga parameter values. 
    
    Parameters
    -----------
    mga_n: int
        Number of mga variables

    """
    mga_weights = list(itertools.product([1,-1,], repeat=mga_n))  
    
    slacks_mga_weights = [(slack,)+ m for slack in slacks \
                                 for m in mga_weights]

    slacks_mga_weights_columns = ["slack"]
    slacks_mga_weights_columns.extend(["m"+str(_) for _ in range(mga_n)])

    slacks_mga_weights_df = pd.DataFrame(data=slacks_mga_weights, 
                                         columns=slacks_mga_weights_columns)  
    
    return slacks_mga_weights_df

def apply_mga_structure(es, mga_n, slacks_mga_weights_df):
    """ 
    TODO: make this method generic?
    Changes the model structure: 
        Express the adjusted cost function value as an upper bound constraint
        Define an alternative objective function
    """
    logger.info("Changing the model structure (In a non-generic way)")

    es.model.cost_minimum = pe.Param(initialize=es.model.objective.expr())

    es.model.cost_function_expr = es.model.objective.expr

    es.model.slack = pe.Param(initialize=1., mutable=True)

    es.model.cost_budget = pe.Constraint(
            expr=es.model.cost_function_expr <= es.model.cost_minimum * es.model.slack
            )

    mga_weights_0 = slacks_mga_weights_df.loc[0, ["m"+str(_) for _ in range(mga_n)]].tolist()

    es.model.mga_weight = pe.Param(
            range(mga_n), 
            initialize = {j: w for j, w in enumerate(mga_weights_0)},
            mutable=True)

    # TODO: Apparently the following is very specific and not generic
    es.model.mga_function_expr = (
            es.model.mga_weight[0] * (
                es.model.generator_p_nom["DE solar"]
                + es.model.generator_p_nom["DE solar-rooftop"]
            )
            + es.model.mga_weight[1] * (
                    es.model.generator_p_nom["DE0 onwind"]
                    + es.model.generator_p_nom["DE1 onwind"]
                    + es.model.generator_p_nom["DE2 onwind"]
                    )
            + es.model.mga_weight[2] * es.model.link_p_nom["DE battery charger"]
            + es.model.mga_weight[3] * es.model.generator_p_nom["DE offwind"]
            + es.model.mga_weight[4] * (
                    es.model.link_p_nom["DE central heat pump"]
                    + es.model.link_p_nom["DE ground heat pump"]
                    )        
            + es.model.mga_weight[5] * (    
                    + es.model.link_p_nom["DE resistive heater"]
                    + es.model.link_p_nom["DE central resistive heater"]
                    )
            + es.model.mga_weight[6] * (
                    es.model.link_p_nom["DE gas boiler"]
                    + es.model.link_p_nom["DE central gas boiler"]
                    + es.model.link_p_nom["DE central CHP electric"]
                    + es.model.link_p_nom["DE OCGT"]
                    )
            + es.model.mga_weight[7] * es.model.link_p_nom["DE H2 Fuel Cell"]
            )

    es.model.del_component(es.model.objective)
    es.model.objective = pe.Objective(expr= es.model.mga_function_expr)


pypsa.Network.apply_mga_structure = apply_mga_structure