import os
import sys
module_path = os.path.abspath(os.path.join("src/"))
if module_path not in sys.path:
    sys.path.append(module_path)

import random
import pandas as pd
import json
import os
from helpers import create_instance, _return_single_dict_match, get_rubric_assessment, get_output_data
from initial_requests import get_initial_info

#canvasapi 
from canvasapi import Canvas

# DASH
from jupyter_dash import JupyterDash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

# Env details
from dotenv import load_dotenv
load_dotenv() 

URL = os.getenv("API_INSTANCE")
KEY = os.getenv("API_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")
GRAPH_URL = f"{URL}/api/graphql"

print(GRAPH_URL)


canvas = create_instance(URL, KEY)

def drop_down_div(list_of_dicts, dropdown_id, div_id):
    """
    """
    first_value = list_of_dicts[0].get("value")
    
    html_div = html.Div([
        dcc.Dropdown(options=list_of_dicts, value=first_value, id=dropdown_id),
        html.Div(id=div_id)
    ])
    
    return(html_div)

def app():

    # Get course id
    # once confirmed move to next step

    # 
    app = JupyterDash(__name__)
    app.config.suppress_callback_exceptions = True

    app.layout = html.Div(
        children = [
            html.H1("Welcome!"),
            html.Div(
                children=[
                    html.H2("Input Course ID"),
                    html.Div(
                        children = [
                            dcc.Input(id="input-course-id", type="number", style={"display": "inline-block"}),
                            html.Button("Submit", id="submit-course-id", n_clicks=0, style={"display": "inline-block"})
                            ])]),
            html.Div(children="Enter your course id", id="course-details-display"),
            html.Br(),
            html.Div(children=[], id="confirmed-course"),
        ], 
        id="initial-input-course")
        
    @app.callback(
        Output("course-details-display", "children"),
        Input("submit-course-id", "n_clicks"),
        State("input-course-id", "value")
        )

    def update_output(n_clicks, value):

        if canvas==None:
            return(
                html.P(f"Error creating session. Confirm you have an active token and a green confirmation at the top noting 'Token Valid: ... '", style={"color": "red"})
            )


        if n_clicks > 0:

            try:
                course = canvas.get_course(value)
                return(
                    html.Div(children = [
                        html.P(f"You have selected: {course.name}", style={"color": "green"}),
                        html.Button(f"Confirm {course.name}", id="confirm-course", n_clicks=0),
                        dcc.Store(id="course-data")
                    ])
                    )
            except Exception as err:
                return(
                    html.P(f"Error with course id {value}:\n{err}\nPlease submit another course id.", style={"color": "red"})
                    )
            
        else:
            return(f"Please enter a course ID and press submit :D")

    @app.callback(
        [Output("confirmed-course", "children"),
         Output("course-data", "data")],
        Input("confirm-course", "n_clicks"),
        State("input-course-id", "value")
    )

    def the_course_has_been_confirmed(n_clicks, value):
        if n_clicks >= 1:
            data = get_initial_info(GRAPH_URL, int(value), KEY)
            assignments = data["data"]["course"]["assignmentsConnection"]["nodes"]
            #TODO only return assignments with rubrics in list
            assignments_list = [{"label": i.get("name"), "value": i.get("_id")} for i in assignments]

            new_div = html.Div(children=[
                drop_down_div(assignments_list, "assignments-dropdown", "assignments-dropdown-container"),
                html.Div(children=[], id="selected-assignment"), 
                dcc.Store(id="reviews-data")],
                id="assignments-selector-container")
            
            return(new_div, data)

        else:
            raise PreventUpdate

    @app.callback(
        [Output("selected-assignment", "children"),
        Output("reviews-data", "data")],
        [Input("assignments-dropdown", "value"),
        Input("course-data", "data")]
    )

    def show_selected_assignment(assignment_value, data):

        if data is None:
            raise PreventUpdate

        else:

            assignments_info = data["data"]["course"]["assignmentsConnection"]["nodes"]
            assignment = _return_single_dict_match(assignments_info, "_id", str(assignment_value))

            assignment_name = assignment.get("name")
            rubric = assignment.get("rubric")

            if rubric is None:
                rubric_title = "No Rubric"
                return(html.P("No rubric found for this assignment."), None)

            else:    
                rubric_title = rubric.get("title")

                try:
                    #TODO show submissions count
                    #TODO show users with no submissions
                    #TODO check for incomplete rubrics
                    submissions = assignment.get("submissionsConnection").get("nodes")

                    #reviews_list = [get_rubric_assessment(i) for i in submissions]
                    #print(get_output_data(submissions))
                    reviews_list = get_output_data(submissions)
                    

                    df = pd.DataFrame(reviews_list)
                    #df = df.drop(["points", "descriptions", "comments"], axis=1)

                    new_html = html.Div([html.H3(f"{assignment_name} ({assignment_value})"),
                    html.H4(f"Rubric: {rubric_title}"),
                    dash_table.DataTable(df.to_dict("records"), [{"name": i, "id": i} for i in df.columns]),
                    html.Br(),
                    html.Div(
                        [
                            html.Button("Download CSV", id="btn_csv", n_clicks=0),
                            dcc.Download(id="download-dataframe-csv"),
                            html.Div(children=[], id="final-output-container")
                        ])], id="returning-assignment-details")

                    return(new_html, reviews_list)

                except Exception as err:
                    return(html.Div([html.H3(f"{assignment_name} ({assignment_value})"), html.H4(f"Rubric: {rubric_title}"), 
                    html.P(f"This rubric has no assessment data. {err}")]), 
                    None)

    @app.callback(
        Output("final-output-container", "children"),
        Output("download-dataframe-csv", "data"),
        Input("reviews-data", "data"),
        Input("btn_csv", "n_clicks"),
        prevent_initial_call=True
    )

    def save_csv(reviews_data, button_clicks):

        if reviews_data is None:
            raise PreventUpdate

        elif button_clicks > 0:
            df = pd.DataFrame(reviews_data)
            csv_name = "my_csv.csv"
            return(f"Complete! See csv: {csv_name}", dcc.send_data_frame(df.to_csv, csv_name))
        
        else:
           raise PreventUpdate



    app.run_server(mode="inline")

    

    

