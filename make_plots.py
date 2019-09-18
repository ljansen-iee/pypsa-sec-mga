import plotly.offline as py
import plotly.graph_objs as go

import cufflinks as cf
cf.set_config_file(offline=True, theme='white')
import plotly.io as pio
import plotly.express as px
pio.templates.default = "plotly_white"

rename_map = {
    'PV-ground.el':"PV-ground",'PV-roof.el':"PV-roof", 'Onwind.el':"Wind-On", 'Offwind.el':"Wind-Off", 'Onwind':"Wind-On", 'Offwind':"Wind-Off", 
    'OCGT.el':"OCGT", 'Bat.el':"Bat", 'Hydro.el':"Hydro",
    'PHS.el':"PHS", 'HP.th':"HP", 'RH.th':"RH", 'HE.el':"HE", 'FC.el':"FC", 'MT.ch4':"MT", 'CHP.el.th':"CHP", "CHP.el" : "CHP",
    'Boiler.th':"Boiler", 'Solar.th':"Solar", 'THS.th':"THS", "COST %": "Cost"}

#clscale = [[0, 'rgb(0, 155, 103)'], [0.5, 'rgb(0, 79, 128)'], [1, 'rgb(143, 53, 71)']] # UniKassel Farben: https://www.uni-kassel.de/intranet/themen/weitere-themen/corporate-design/startseite/gestaltungselemente/farben.html
clscale = [[0, 'rgb(80, 149, 200)'], [0.5, 'rgb(196, 210, 15)'], [1, 'rgb(154, 12, 70)']] 

def parcoords(df, title, colorDimension, save=True):
    
    dimensions = []
    for label, values in df.iteritems():
        if label == "Wind-On":
            dimensions.append(
                    dict(
                        label=str(label), 
                        values=values,
                        constraintrange = [df["Wind-On"].min(),120]
                    )
            )
        else:
            dimensions.append(
                    dict(
                        label=str(label), 
                        values=values
                    )       
            )

    data = [
        go.Parcoords(
            line = dict(
                color = df[colorDimension],
                colorscale = clscale,
                cauto=True,
                showscale = False,
                cmin = df.loc[:,colorDimension].min(),
                cmax = df.loc[:,colorDimension].max(),
            ),
            labelfont=dict(size=20),
            rangefont=dict(size=20, color="white"),
            tickfont=dict(size=20),            
            dimensions = dimensions
        )
    ]
    layout = go.Layout(
        title=title,
        height=500,
        width= 1600,
        margin={"l": 50, "t":100, "b": 10, "r": 50},
        font=dict(family="Times New Roman")

    )
    # Categorical Labels
    labels = [
            dict(xref='paper', yref='paper', 
                 x=0.2, y=1.2,
                 xanchor='center', yanchor='top',
                 text=r"$\text{GW}_{\text{el}}$",
                 font=dict(
                     size=20,
                 ),
                 showarrow=False
                ),
            dict(xref='paper', yref='paper', 
                 x=0.495, y=1.2,
                 xanchor='center', yanchor='top',
                 text=r"$\text{GW}_{\text{CH4}}$",
                 font=dict(
                     size=20,
                 ),
                 showarrow=False
                ),
            dict(xref='paper', yref='paper', 
                 x=0.75, y=1.2,
                 xanchor='center', yanchor='top',
                 text=r"$\text{GW}_{\text{th}}$",
                 font=dict(
                     size=20,
                 ),
                 showarrow=False
                ),
            dict(xref='paper', yref='paper', 
                 x=-0.03, y=1.18,
                 xanchor='left', yanchor='top',
                 text="___________________________________________________________________________________________________________________________________________________________________________________________________",
                 font=dict(
                     size=16,
                 ),
                 showarrow=False
                ),
            dict(xref='paper', yref='paper', 
                 x=0.453, y=1.19,
                 xanchor='left', yanchor='top',
                 text="_____",
                 textangle=-90,
                 font=dict(
                     size=16,
                 ),
                 showarrow=False
                ), 
        dict(xref='paper', yref='paper', 
                 x=0.523, y=1.19,
                 xanchor='left', yanchor='top',
                 text="_____",
                 textangle=-90,
                 font=dict(
                     size=16,
                 ),
                 showarrow=False
                ), 


            ]
    layout['annotations'] = labels

    
    fig = go.Figure(data=data, layout=layout)
    
    py.iplot(fig, filename = 'mga_parcoords.html',
                config = {'displayModeBar': True, "showLink":False}
           )
    if save == True:
        fig.write_image("decision_space.png", scale=2)

def barplot(df, title, filename, width=600):
    fig = df.iplot(kind='bar', barmode='stack', bargap=.1, asFigure=True, colors=colors, orientation="v", 
                      margin={"l": 0, "t":40, "b": 0, "r": 0})
    fig.layout.width = width
    fig.layout.height = 450
    fig.layout.title = title
    #fig.layout.xaxis.title = ""
    fig.layout.xaxis.tickvals = df.index
    fig.layout.font.size = 16
    fig.layout.font.family= "Times New Roman"   
    fig.iplot()
    fig.write_image(filename, scale=3)

colors = {
        "PV.el":            "rgba(254, 220, 0, 0.95)",
        "PV":               "rgba(254, 220, 0, 0.95)",
        "PV-ground.el":            "rgba(254, 220, 0, 0.95)",
        "PV-ground":               "rgba(254, 220, 0, 0.95)",
        "PV-roof.el":            "rgba(255,253,4, 0.95)",
        "PV-roof":               "rgba(255,253,4, 0.95)",
        "Onwind":        "rgba(0, 91, 148, 0.95)",
        "Offwind":       "rgba(30,130,192, 0.95)",
        "Wind-On":        "rgba(0, 91, 148, 0.95)",
        "Wind-Off":       "rgba(30,130,192, 0.95)",
        "Onwind.el":        "rgba(0, 91, 148, 0.95)",
        "Offwind.el":       "rgba(30,130,192, 0.95)",
        "Wind":             "rgba(30,130,192, 0.95)",
        "CHP.el.th":        "rgba(255, 188, 66, 0.95)",
        "CHP":        "rgba(255, 188, 66, 0.95)",
        "CCGT.el":          "rgba(255, 163, 20, 0.95)",
        "CCGT":          "rgba(255, 163, 20, 0.95)",        
        "OCGT.el":          "rgba(255, 163, 20, 0.95)",
        "OCGT":          "rgba(255, 163, 20, 0.95)",
        "H2.el":          "rgba(190, 118, 60, 0.95)",
        "H2":             "rgba(190, 118, 60, 0.95)",
        "HE":             "rgba(190, 118, 60, 0.95)",
        "FC.el":            "rgba(104, 46, 0, 0.95)",
        "FC":            "rgba(104, 46, 0, 0.95)",
        "Boiler.th":        "rgba(240,104,14, 0.95)",
        "Boiler":        "rgba(240,104,14, 0.95)",
        "":                 "rgba(163,143,25, 0.95)",
        "BatOut.el":        "rgba(0,1,251, 0.95)",
        "BatOut":        "rgba(0,1,251, 0.95)",
        "Bat.el":        "rgba(0,1,251, 0.95)",
        "Bat":        "rgba(0,1,251, 0.95)",
        "Hydro.el":         "rgba(49, 185, 198, 0.95)",
        "Hydro":         "rgba(49, 185, 198, 0.95)",
        "PHS":              "rgba(49, 185, 198, 0.95)",
        "PHS.el":              "rgba(49, 185, 198, 0.95)",
        "gas_import":       "rgba(80, 95, 107, 0.95)",
        "gas_storage":      "rgba(169,173,172, 0.95)",
        "load":             "rgba(142, 35, 39, 0.95)",
        "load-shed":        "rgba(108, 192, 169, 0.95)",
        "driving_load-shed":"rgba(108, 192, 169, 0.95)",
        "bev_charger":      "rgba(54,55,145, 0.95)",
        "RH.th":            "rgba(248,4,0, 0.95)",
        "RH":            "rgba(248,4,0, 0.95)",
        "driving_load":     "rgba(143,132,192, 0.95)",
        "Solar.th":         "rgba(255,253,4, 0.95)",
        "Solar":         "rgba(255,253,4, 0.95)",
        "THS":           "rgba(222,226,0, 0.95)",
        "THS.th":           "rgba(222,226,0, 0.95)",
        "HP.th":            "rgba(252,235,201, 0.95)",
        "HP":            "rgba(252,235,201, 0.95)",
        "":                 "rgba(80,95,107, 0.95)",
        "import":           "rgba(80,95,107, 0.95)",
        "biomass":          "rgba(143,163,4, 0.95)",
        "CH4.h2":         "rgba(240,104,4, 0.95)",
        "MT.h2":         "rgba(240,104,4, 0.95)",
        "MT":         "rgba(240,104,4, 0.95)"
        }