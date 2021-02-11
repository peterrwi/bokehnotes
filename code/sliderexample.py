import numpy as np

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Slider
from bokeh.layouts import row, column
from bokeh.io import curdoc

# First set the starting data and create the plot
x = np.linspace(0,10,500)
y = 2.0 * np.sin(1.0 * x + np.pi)
source = ColumnDataSource(data=dict(x=x,y=y))

p = figure(plot_width=400, plot_height=200, y_range=(-5,5), x_range=(0,10))
p.line('x','y',source=source)
    
# Create the sliders
slider_amp = Slider(start=0, end=5, value=2, step=.1, title="Amplitude")
slider_freq = Slider(start=0.1, end=10, value=1.0, step=.1, title="Frequency")
slider_phase = Slider(start=0, end=2.0*np.pi, value=np.pi, step=.1, title="Phase")

# Set the code to update the data when the sliders are change
def update(attr, old, new):
    A = slider_amp.value
    freq = slider_freq.value
    phase = slider_phase.value
        
    new_data = {}
    new_data['x'] = source.data['x']
    new_data['y'] = A * np.sin(freq * x + phase)

    source.data = new_data

# Let bokeh know that when the value of any of the sliders changes it should run the callback code
slider_amp.on_change('value', update)
slider_freq.on_change('value', update)
slider_phase.on_change('value', update)
    
# Set the layout with the sliders and plot
layout = row(column(slider_amp, slider_freq, slider_phase), p)

# add the layout to curdoc
curdoc().add_root(layout)