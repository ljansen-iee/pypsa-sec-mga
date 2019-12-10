import pypsa
import pandas as pd
import logging
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

from prepare_model_and_mga import make_options

options = make_options()
options["cutout_DE_export_path"] = "all_flex-central_0_DE_1h.h5"
options["postnetwork_import_path"] = "pypsa-eur-sec-30/results/version-16/postnetworks/postnetwork-all_flex-central_0.h5"

es = pypsa.Network()

es.import_from_hdf5(options["postnetwork_import_path"])

bus_cutout = es.buses[es.buses.index.str[:2] == "DE"].index

es.buses = es.buses[es.buses.index.isin(bus_cutout)]

es.generators = es.generators[es.generators["bus"].isin(bus_cutout)]

es.loads = es.loads[es.loads["bus"].isin(bus_cutout)]

es.storage_units = es.storage_units[es.storage_units["bus"].isin(bus_cutout)]

es.stores = es.stores[es.stores["bus"].isin(bus_cutout)]

es.links = es.links[
        es.links["bus0"].isin(bus_cutout) & es.links["bus1"].isin(bus_cutout) \
        & ~es.links.index.isin(["DE V2G"]) # ~ means without V2G
        ]

def reduce_time_steps(step, rolling_mean=False):
    """rolling mean leads to overestimated PV"""

    for key in es.generators_t.keys():
        cutout = es.generators.index & es.generators_t[key].columns # NB: in the time-varying data is no bus attribute
        if rolling_mean:
            es.generators_t[key] = es.generators_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.generators_t[key] = es.generators_t[key][cutout][::step]

    for key in es.loads_t.keys():
        cutout = es.loads.index & es.loads_t[key].columns
        if rolling_mean:
            es.loads_t[key] = es.loads_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.loads_t[key] = es.loads_t[key][cutout][::step]

    for key in es.storage_units_t.keys():
        cutout = es.storage_units.index & es.storage_units_t[key].columns
        if rolling_mean:
            es.storage_units_t[key] = es.storage_units_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.storage_units_t[key] = es.storage_units_t[key][cutout][::step]
        
    for key in es.stores_t.keys():
        cutout = es.stores.index & es.stores_t[key].columns
        if rolling_mean:
            es.stores_t[key] = es.stores_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.stores_t[key] = es.stores_t[key][cutout][::step]

    for key in es.links_t.keys():
        cutout = es.links.index & es.links_t[key].columns
        if rolling_mean:
            es.links_t[key] = es.links_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.links_t[key] = es.links_t[key][cutout][::step]

    for key in es.buses_t.keys():
        cutout = es.buses.index & es.buses_t[key].columns
        if rolling_mean:
            es.buses_t[key] = es.buses_t[key][cutout].rolling(step, min_periods=1, center=True).mean()
        es.buses_t[key] = es.buses_t[key][cutout][::step]


reduce_time_steps(step=options["step"])


es.set_snapshots(es.snapshots[::options["step"]])
es.set_snapshots(es.generators_t.p_max_pu.index)
es.snapshot_weightings = pd.Series(float(options["step"]),index=es.snapshots)

es.export_to_hdf5(options["cutout_DE_export_path"])

logger.info("energy system cutout for DE is build")
