import pypsa
import pandas as pd
import logging
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

from utils import make_options

options = make_options()

esom = pypsa.Network()

esom.import_from_hdf5("pypsa-eur-sec-30/results/version-16/postnetworks/postnetwork-all_flex-central_.h5")

bus_cutout = [
        "DE",
        "DE gas", 
        "DE H2", 
        "DE heat", 
        "DE urban heat", 
        "DE water tanks",
        "DE central water tanks",
        "DE EV battery",
        'DE battery'
        ]

links_cutout = esom.links.index.drop("DE V2G")

esom.buses = esom.buses[esom.buses.index.isin(bus_cutout)]

esom.generators = esom.generators[esom.generators["bus"].isin(bus_cutout)]

esom.loads = esom.loads[esom.loads["bus"].isin(bus_cutout)]

esom.storage_units = esom.storage_units[esom.storage_units["bus"].isin(bus_cutout)]

esom.stores = esom.stores[esom.stores["bus"].isin(bus_cutout)]

esom.links = esom.links[
        esom.links["bus0"].isin(bus_cutout) & esom.links["bus1"].isin(bus_cutout) 
        & esom.links.index.isin(links_cutout)
        ]

for key in esom.generators_t.keys():
    cutout = esom.generators.index & esom.generators_t[key].columns # Note: in the time-varying data is no bus attribute
    esom.generators_t[key] = esom.generators_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]

for key in esom.loads_t.keys():
    cutout = esom.loads.index & esom.loads_t[key].columns
    esom.loads_t[key] = esom.loads_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]

for key in esom.storage_units_t.keys():
    cutout = esom.storage_units.index & esom.storage_units_t[key].columns
    esom.storage_units_t[key] = esom.storage_units_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]
    
for key in esom.stores_t.keys():
    cutout = esom.stores.index & esom.stores_t[key].columns
    esom.stores_t[key] = esom.stores_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]

for key in esom.links_t.keys():
    cutout = esom.links.index & esom.links_t[key].columns
    esom.links_t[key] = esom.links_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]

for key in esom.buses_t.keys():
    cutout = esom.buses.index & esom.buses_t[key].columns
    esom.buses_t[key] = esom.buses_t[key][cutout].rolling(options["step"], min_periods=1, center=True).mean()[::options["step"]]

esom.set_snapshots(esom.snapshots[::options["step"]])
esom.set_snapshots(esom.generators_t.p_max_pu.index)
esom.snapshot_weightings = pd.Series(float(options["step"]),index=esom.snapshots)

esom.export_to_hdf5("all_flex-central_0_DE.h5")

logger.info("cutout is build")
