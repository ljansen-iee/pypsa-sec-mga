import pandas as pd
import numpy as np
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
            "name": "cplex",
            "options": {None}
        },
        "step": 1,
        "co2_limit": 0.,
    }

    if options['solver']['name'] == "gurobi" or options['solver']['name'] == "gurobi_persistent":
        options['solver']['options'] = {"threads" : 4,"method" : 2,"crossover" : 0,"BarConvTol": 1.e-4,"FeasibilityTol": 1.e-4}
    if options['solver']['name'] == "cplex":
        options['solver']['options'] = {"lpmethod":4,"threads":4,"simplex tolerances optimality":1e-5,"solutiontype":2}
        
    return options


def annuity(lifetime,discount_rate):
    """ Returns the annuity factor """

    if discount_rate == 0.:
        return 1/lifetime
    else:
        return discount_rate/(1. - 1. / (1. + discount_rate)**lifetime)
    

def prepare_costs(file_name = "pypsa-eur-sec-30/data/costs/costs.csv", number_years=1, usd_to_eur=1/1.2, costs_year=2030):
    """ 
    Returns a pd.DataFrame with model-ready asset costs and other parameters 
    
    based on: arXiv:1801.05290. 
    """

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

    based on: arXiv:1801.05290.
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

    def chp_nom_propotion1(model):
        return nom_r*esom.links.at["DE industry CHP electric","efficiency"]*model.link_p_nom["DE industry CHP electric"] == \
                esom.links.at["DE industry CHP heat","efficiency"]*model.link_p_nom["DE industry CHP heat"]
    esom.model.chp_nom_propotion1 = pe.Constraint(rule=chp_nom_propotion1)

    #Guarantees c_m p_b1  leq  p_g1
    def chp_backpressure(model,snapshot):
        return c_m*esom.links.at["DE central CHP heat","efficiency"]*model.link_p["DE central CHP heat",snapshot] <= \
                esom.links.at["DE central CHP electric","efficiency"]*model.link_p["DE central CHP electric",snapshot] 
    esom.model.chp_backpressure = pe.Constraint(list(snapshots),rule=chp_backpressure)  

    def chp_backpressure1(model,snapshot):
        return c_m*esom.links.at["DE industry CHP heat","efficiency"]*model.link_p["DE industry CHP heat",snapshot] <= \
                esom.links.at["DE industry CHP electric","efficiency"]*model.link_p["DE industry CHP electric",snapshot] 
    esom.model.chp_backpressure1 = pe.Constraint(list(snapshots),rule=chp_backpressure1)  

    #Guarantees p_g1 +c_v p_b1  leq  p_g1_nom
    def chp_top_iso_fuel_line(model,snapshot):
        return model.link_p["DE central CHP heat",snapshot] + model.link_p["DE central CHP electric",snapshot] <= \
                model.link_p_nom["DE central CHP electric"]
    esom.model.chp_top_iso_fuel_line = pe.Constraint(list(snapshots),rule=chp_top_iso_fuel_line)
    
    def chp_top_iso_fuel_line1(model,snapshot):
        return model.link_p["DE industry CHP heat",snapshot] + model.link_p["DE industry CHP electric",snapshot] <= \
                model.link_p_nom["DE industry CHP electric"]
    esom.model.chp_top_iso_fuel_line1 = pe.Constraint(list(snapshots),rule=chp_top_iso_fuel_line1)


