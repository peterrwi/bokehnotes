import numpy as np
import pandas as pd

from bokeh.plotting import show, figure, output_notebook, reset_output
from bokeh.layouts import gridplot
from bokeh.models import ColumnDataSource, Span

from bokeh.server.server import Server
from functools import partial
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application


def addErrorBars(p, source, x, y, xerr=[], yerr=[], **kwargs):
    """
    Computes the coordinates for each error bar and adds them to a figure using
    multi_line(). xerr and yerr 

    p: The Bokeh figure object
    source: The ColumnDataSource object with the data
    x, y (str): The column name of the x-axis,y-axis data
    xerr, yerr (lists): The column names for the [low, high] errorbar on x,y. If
        symmetrical, this can be length 1. If nothing is provided, the code will
        attempt to determine the column names. If None or False, no x,y error 
        bars will be drawn.
    """
    data = source.data

    errs_x, errs_y = [], []
    
    # If xerr and yerr aren't provided (and aren't 'None'), try to figure out the values automatically
    if xerr not in [None,False]:
        if len(xerr) == 0:
            if x+"_lo" in data.keys() and x+"_hi" in data.keys():
                xerr = [x+"_lo",x+"_hi"]
            elif x+"_err" in data.keys():
                xerr = [x+"_err",x+"_err"]
            else:
                xerr = None
    if yerr not in [None,False]:
        if len(yerr) == 0:
            if y+"_lo" in data.keys() and y+"_hi" in data.keys():
                yerr = [y+"_lo",y+"_hi"]
            elif y+"_err" in data.keys():
                yerr = [y+"_err",y+"_err"]
            else:
                yerr = None

    # Loop over each entry and set the coordinates of a horizontal errorbar line
    if xerr not in [None,False]:
        if len(xerr) == 1:
            xerr = [xerr[0],xerr[0]]
        for i in range(len(data[x])):
            errs_x.append([data[x][i] - data[xerr[0]][i], data[x][i] + data[xerr[1]][i]])
            errs_y.append([data[y][i], data[y][i]])
    # Repeat for the y errors
    if yerr not in [None,False]:
        if len(yerr) == 1:
            yerr = [yerr[0],yerr[0]]
        for i in range(len(data[x])):
            errs_x.append([data[x][i], data[x][i]])
            errs_y.append([data[y][i] - data[yerr[0]][i], data[y][i] + data[yerr[1]][i]])
    p.multi_line(errs_x, errs_y, **kwargs)


class BKCorner():
    def __init__(self, df, params=[], logify=False, output='notebook', notebook_url="http://localhost:8888", **kwargs):
        self.df = df
        self.params = params
        self.logify = logify
        self.kwargs = kwargs

        if output == 'notebook':
            reset_output()
            output_notebook()
            show(self.modify_doc, notebook_url=notebook_url)
        else:
            reset_output()
            server = Server({'/': self.modify_doc})
            server.start()
            try:
                server = Server({'/': self.modify_doc})
                server.run_until_shutdown()
            except:
                pass
                #print("Server running")
            server.show("/")
            self.server = server

    def modify_doc(self, doc):
        df, params, logify = self.df, self.params, self.logify
        if params == []:
            params = df.columns

        kwargs = {
            "panel_width": 150,
            "label_all_axes": False,
        }
        for key in self.kwargs.keys():
            kwargs[key] = self.kwargs[key]

        if isinstance(logify,bool):
            logify = [logify]*len(params)
        data = {}
        for i in range(len(params)):
            if logify[i]:
                data[params[i]] = np.log10(df[params[i]])
            else:
                data[params[i]] = df[params[i]]

        def callback(attr, old, new):
            indices = source.selected.indices
            for par in params:
                old_data = src_hist[par].data
                edges = np.concatenate([old_data["left"], [old_data["right"][-1]]])
                hist, edges = np.histogram(data[par][indices], density=False, bins=edges)
                new_data = {
                    "top": hist,
                    "left": edges[:-1],
                    "right": edges[1:]
                }   

                src_hist[par].data = new_data

            medians = {par: [np.median(data[par][indices])] for par in params}
            src_medians.data = medians  

        source = ColumnDataSource(data)
        src_hist, src_medians = {}, {}
        for par in params:
            hist, edges = np.histogram(data[par], density=False, bins=20)
            hist_df = pd.DataFrame({
                "top": 0.*hist,
                "left": edges[:-1],
                "right": edges[1:]
            })
            src_hist[par] = ColumnDataSource(hist_df)
        medians = {par: [np.median(data[par])] for par in params}
        src_medians = ColumnDataSource(data = medians)

        TOOLS = 'lasso_select, reset'
        Nparam = len(params)
        ax = np.full((Nparam,Nparam), None).tolist()
        #toggle_botton = Button(label='c')
        for row in range(Nparam):
            for col in range(row+1):
                vline = Span(location=medians[params[col]][0], dimension='height', line_color='black', line_width=1.5, line_dash='dashed')
                hline = Span(location=medians[params[row]][0], dimension='width', line_color='black', line_width=1.5, line_dash='dashed')

                #vline = Span(location=params[col], source=src_medians, dimension='height', line_color='orange', line_width=1.5, line_dash='dashed')
                #hline = Span(location=row, dimension='width', line_color='orange', line_width=1.5, line_dash='dashed')
                if col==0:
                    width = int(kwargs["panel_width"]*1.25)
                else:
                    width = kwargs["panel_width"]
                if row==Nparam-1:
                    height = int(kwargs["panel_width"]*1.25)
                else:
                    height = kwargs["panel_width"]
                if row == col:
                    hist, edges = np.histogram(data[params[col]], density=False, bins=20)
                    ax[row][col] = figure(width=width, height=height, tools=TOOLS) #, title=params[col])
                    ax[row][col].quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
                           fill_color="navy", line_color="white", alpha=0.5)
                    ax[row][col].add_layout(vline)

                    # Histogram of selected points
                    ax[row][col].quad(
                        bottom = 0, top = "top",left = "left", right = "right", source = src_hist[params[col]],
                        fill_color = 'orange', line_color = "white", fill_alpha = 0.5, line_width=0.1)
                else:
                    ax[row][col] = figure(width=width, height=height, tools=TOOLS)
                    ax[row][col].scatter(
                        params[col],params[row],source=source, size=5,
                        fill_color='blue',line_color='navy', fill_alpha=0.4, line_alpha=0.4,
                        nonselection_fill_color='blue', nonselection_line_color='navy',nonselection_alpha=0.4, nonselection_line_alpha=0.4,
                        selection_fill_color='orange', selection_line_color='orange', selection_alpha=0.5,
                    )
                    ax[row][col].add_layout(vline)
                    ax[row][col].add_layout(hline)
                if col == 0:
                    ax[row][col].yaxis.axis_label = params[row]
                else:
                    ax[row][col].yaxis.major_label_text_font_size = '0pt'
                if row == Nparam-1:
                    ax[row][col].xaxis.axis_label = params[col]
                else:
                    ax[row][col].xaxis.major_label_text_font_size = '0pt'
                if kwargs["label_all_axes"]:
                    ax[row][col].yaxis.axis_label = params[row]
                    ax[row][col].xaxis.axis_label = params[col]
        ax_grid = gridplot(ax)

        source.selected.on_change('indices', callback)

        # add the layout to curdoc
        doc.add_root(ax_grid)