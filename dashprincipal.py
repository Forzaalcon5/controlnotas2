import pandas as pd
import plotly.express as px
from dash import html, Input, Output, dcc, dash_table
import dash
from database import obtenerestudiantes
from flask import session


def creartablero(server):

    dataf = obtenerestudiantes()

    appnotas = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/dashprincipal/",
        suppress_callback_exceptions=True
    )

    # ── Opciones iniciales de carrera ──────────────────────────────────────
    carreras_opciones = (
        [{"label": ca, "value": ca} for ca in sorted(dataf["Carrera"].unique())]
        if len(dataf) > 0 else []
    )
    carrera_inicial = dataf["Carrera"].unique()[0] if len(dataf) > 0 else None

    appnotas.layout = html.Div([

        html.H1("TABLERO AVANZADO", style={
            "textAlign": "center",
            "backgroundColor": "#1E1BD2",
            "color": "white",
            "padding": "20px"
        }),

        # filtro
        html.Div([
            html.Label("Seleccionar carrera"),
            dcc.Dropdown(
                id="filtro_carrera",
                options=carreras_opciones,
                value=carrera_inicial
            ),
            html.Br(),
            html.Label("Rango de edad"),
            dcc.RangeSlider(
                id="slider_edad",
                min=dataf["Edad"].min() if len(dataf) > 0 else 0,
                max=dataf["Edad"].max() if len(dataf) > 0 else 100,
                step=1,
                value=[
                    dataf["Edad"].min() if len(dataf) > 0 else 0,
                    dataf["Edad"].max() if len(dataf) > 0 else 100
                ],
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Br(),
            html.Label("Rango promedio"),
            dcc.RangeSlider(
                id="slider_promedio",
                min=0, max=5, step=0.5,
                value=[0, 5],
                tooltip={"placement": "bottom", "always_visible": True}
            ),
        ], style={"width": "80%", "margin": "auto"}),

        html.Br(),

        # KPIs 
        html.Div(id="kpis", style={"display": "flex", "justifyContent": "space-around"}),
        html.Br(),

        #  Búsqueda y tabla 
        dcc.Input(id="busqueda", type="text", placeholder="Buscar estudiante....."),
        html.Br(), html.Br(),

        dcc.Loading(
            dash_table.DataTable(
                id="tabla",
                page_size=8,
                filter_action="native",
                sort_action="native",
                row_selectable="multi",
                selected_rows=[],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center"}
            ),
            type="circle"
        ),
        html.Br(),

        #  Intervalo para auto-refresh 
        dcc.Interval(id="intervalo", interval=10000, n_intervals=0),

        
        dcc.Loading(dcc.Graph(id="gra_detallado"), type="default"),
        html.Br(),

        
        dcc.Tabs([
            dcc.Tab(label="Histograma",           children=[dcc.Graph(id="histograma")]),
            dcc.Tab(label="Dispersión",           children=[dcc.Graph(id="dispersion")]),
            dcc.Tab(label="Desempeño",            children=[dcc.Graph(id="pie")]),
            dcc.Tab(label="Promedio por Carrera", children=[dcc.Graph(id="barras")]),
        ]),
        html.Br(),

       
        # Ranking top 10
       
        html.Div([
            html.H3(" Ranking Top 10 Estudiantes",
                    style={"textAlign": "center", "color": "#1E1BD2"}),
            dcc.Loading(
                dash_table.DataTable(
                    id="ranking",
                    columns=[
                        {"name": "#",        "id": "Posicion"},
                        {"name": "Nombre",   "id": "Nombre"},
                        {"name": "Carrera",  "id": "Carrera"},
                        {"name": "Promedio", "id": "Promedio"},
                    ],
                    style_cell={"textAlign": "center"},
                    style_header={
                        "backgroundColor": "#1E1BD2",
                        "color": "white",
                        "fontWeight": "bold"
                    },
                    style_data_conditional=[
                        {"if": {"row_index": 0},
                         "backgroundColor": "#FFD700", "fontWeight": "bold"},
                        {"if": {"row_index": 1},
                         "backgroundColor": "#C0C0C0", "fontWeight": "bold"},
                        {"if": {"row_index": 2},
                         "backgroundColor": "#CD7F32", "fontWeight": "bold"},
                    ]
                ),
                type="circle"
            ),
        ], style={"width": "80%", "margin": "auto"}),
        html.Br(),

       
        # Alerta estudiantes en riesgo 
        
        html.Div(id="alerta_riesgo",
                 style={"width": "80%", "margin": "auto"}),
        html.Br(),

    ])

    
    @appnotas.callback(
        Output("tabla",        "data"),
        Output("tabla",        "columns"),
        Output("kpis",         "children"),
        Output("histograma",   "figure"),
        Output("dispersion",   "figure"),
        Output("pie",          "figure"),
        Output("barras",       "figure"),
        Output("ranking",      "data"),           
        Output("alerta_riesgo","children"),        

        Input("filtro_carrera",  "value"),
        Input("slider_edad",     "value"),
        Input("slider_promedio", "value"),
        Input("busqueda",        "value"),
        Input("intervalo",       "n_intervals"),
    )
    def actualizar_comp(carrera, rangoedad, rangoprome, busqueda, n_intervals):

        # ── Cargar datos frescos ───────────────────────────────────────────
        dataf = obtenerestudiantes()

        if dataf.empty:
            empty_fig = px.scatter(title="Sin datos")
            return [], [], [], empty_fig, empty_fig, empty_fig, empty_fig, [], ""

       
        if carrera is None or carrera not in dataf["Carrera"].unique():
            carrera = dataf["Carrera"].unique()[0]

        filtro = dataf[
            (dataf["Carrera"] == carrera) &
            (dataf["Edad"]    >= rangoedad[0]) &
            (dataf["Edad"]    <= rangoedad[1]) &
            (dataf["Promedio"] >= rangoprome[0]) &
            (dataf["Promedio"] <= rangoprome[1])
        ]

        if busqueda:
            filtro = filtro[
                filtro.apply(lambda row: busqueda.lower() in str(row).lower(), axis=1)
            ]

        # filtro
        promedio = round(filtro["Promedio"].mean(), 2) if not filtro.empty else 0
        total    = len(filtro)
        maximo   = round(filtro["Promedio"].max(), 2) if not filtro.empty else 0

        estilo_kpi = {
            "backgroundColor": "#3498db",
            "color": "white",
            "padding": "15px",
            "borderRadius": "10px"
        }
        kpis = [
            html.Div([html.H4("Promedio"),           html.H2(promedio)], style=estilo_kpi),
            html.Div([html.H4("Total estudiantes"),  html.H2(total)],    style=estilo_kpi),
            html.Div([html.H4("Máximo"),             html.H2(maximo)],   style=estilo_kpi),
        ]

        #Gráficos 
        histo      = px.histogram(filtro, x="Promedio", nbins=10,
                                  title="Distribución de Promedios")
        dispersion = px.scatter(filtro, x="Edad", y="Promedio",
                                color="Desempeño", trendline="ols",
                                title="Edad vs Promedio")
        pie        = px.pie(filtro, names="Desempeño",
                            title="Distribución por Desempeño")
        promedios  = dataf.groupby("Carrera")["Promedio"].mean().reset_index()
        barras     = px.bar(promedios, x="Carrera", y="Promedio",
                            color="Carrera", title="Promedio General por Carrera")

        #  Ranking top 10 
        top10 = (
            dataf.nlargest(10, "Promedio")[["Nombre", "Carrera", "Promedio"]]
            .reset_index(drop=True)
        )
        top10.insert(0, "Posicion", range(1, len(top10) + 1))
        ranking_data = top10.to_dict("records")

        # Alerta estudiantes en riesgo 
        en_riesgo = dataf[dataf["Promedio"] < 3.0][["Nombre", "Carrera", "Promedio"]]

        if en_riesgo.empty:
            alerta = html.Div(
                " No hay estudiantes en riesgo actualmente.",
                style={
                    "backgroundColor": "#d4edda",
                    "color": "#155724",
                    "padding": "12px",
                    "borderRadius": "8px",
                    "textAlign": "center"
                }
            )
        else:
            alerta = html.Div([
                html.H3(
                    f" Estudiantes en Riesgo ({len(en_riesgo)})",
                    style={"color": "#721c24", "textAlign": "center"}
                ),
                dash_table.DataTable(
                    data=en_riesgo.to_dict("records"),
                    columns=[
                        {"name": "Nombre",   "id": "Nombre"},
                        {"name": "Carrera",  "id": "Carrera"},
                        {"name": "Promedio", "id": "Promedio"},
                    ],
                    style_cell={"textAlign": "center"},
                    style_header={
                        "backgroundColor": "#f5c6cb",
                        "color": "#721c24",
                        "fontWeight": "bold"
                    },
                    style_data={
                        "backgroundColor": "#fff3f4"
                    }
                )
            ], style={
                "border": "2px solid #f5c6cb",
                "borderRadius": "8px",
                "padding": "15px",
                "backgroundColor": "#fff3f4"
            })

        return (
            filtro.to_dict("records"),
            [{"name": i, "id": i} for i in filtro.columns],
            kpis,
            histo, dispersion, pie, barras,
            ranking_data,   
            alerta          
        )

    
    @appnotas.callback(
        Output("gra_detallado", "figure"),
        Input("tabla", "derived_virtual_data"),
        Input("tabla", "derived_virtual_selected_rows"),
    )
    def actualizartab(rows, selected_rows):
        if rows is None:
            return px.scatter(title="Sin datos")

        dff = pd.DataFrame(rows)

        if selected_rows:
            dff = dff.iloc[selected_rows]
            fig = px.scatter(
                dff, x="Edad", y="Promedio",
                color="Desempeño", size="Promedio",
                title="Análisis detallado (filas seleccionadas)",
                trendline="ols"
            )
            return fig

        return px.scatter(title="Selecciona filas en la tabla para ver el análisis detallado")

    return appnotas