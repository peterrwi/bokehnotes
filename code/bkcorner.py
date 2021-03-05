import numpy as np
import pandas as pd

from bokeh.plotting import show, figure, output_notebook, reset_output
from bokeh.layouts import gridplot
from bokeh.models import ColumnDataSource, Span
from bokeh.server.server import Server

class BKCorner():
    def __init__(self, df, params=[], trim_factor=1, logify=False, output='notebook', port=5006, notebook_url="http://localhost:8888", **kwargs):
        self.df = df.iloc[::trim_factor].reset_index(drop=True)
        self.params = params
        self.logify = logify
        self.kwargs = kwargs

        if output == 'notebook':
            reset_output()
            output_notebook()
            show(self.modify_doc, notebook_url=notebook_url)
        elif output == 'server':
            reset_output()
            server = Server({'/': self.modify_doc}, port=port)
            server.start()
            try:
                server.run_until_shutdown()
            except:
                print("Server already running")
            self.server = server

    def modify_doc(self, doc):
        df, params, logify = self.df, self.params, self.logify
        if params == []:
            params = df.columns

        kwargs = {
            "panel_width": 150,
            "label_all_axes": False,
            "title": False,
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
                    if kwargs['title']:
                        _title = params[col]
                    else:
                        _title = None
                    ax[row][col] = figure(width=width, height=height, tools=TOOLS, title=_title)
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