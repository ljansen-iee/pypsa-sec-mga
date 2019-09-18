import pandas as pd
import pyomo.environ as pe

def add_summary_row(df, row_index, es):

    df.at[row_index,"Cost [%]"] = pe.value(es.model.cost_function_expr) / pe.value(es.model.cost_minimum)
    df.at[row_index,"Cost [€/a]"] = pe.value(es.model.cost_function_expr)

    # Installed capacity
    df.loc[row_index, es.generators.p_nom_opt.index] = es.generators.p_nom_opt.values
    df.loc[row_index, es.links.p_nom_opt.index] = es.links.p_nom_opt.values
    df.loc[row_index, es.storage_units.p_nom_opt.index] = es.storage_units.p_nom_opt.values
    df.loc[row_index, es.stores.e_nom_opt.index] = es.stores.e_nom_opt.values

    # Produced and consumed energy
    df.loc[row_index, "p " + es.generators_t.p.columns] = es.generators_t.p.sum().values
    df.loc[row_index, "p0 " + es.links_t.p0.columns] = es.links_t.p0.sum().values
    df.loc[row_index, "p1 " + es.links_t.p1.columns] = es.links_t.p1.sum().values
    df.loc[row_index, "p0 " + es.storage_units_t.p.columns] = es.storage_units_t.p[es.storage_units_t.p<0].sum().values
    df.loc[row_index, "p0 " + es.stores_t.p.columns] = es.stores_t.p[es.stores_t.p<0].sum().values   
    df.loc[row_index, "p1 " + es.storage_units_t.p.columns] = es.storage_units_t.p[es.storage_units_t.p>0].sum().values
    df.loc[row_index, "p1 " + es.stores_t.p.columns] = es.stores_t.p[es.stores_t.p>0].sum().values
    
    return df