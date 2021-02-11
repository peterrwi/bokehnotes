import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.layouts import row, column
from bokeh.models import CrosshairTool, WheelZoomTool, ResetTool, PanTool, BoxSelectTool, HoverTool, BoxZoomTool
from bokeh.models import ColumnDataSource, CustomJS, Div, DatePicker, FileInput

from base64 import b64decode

# First choose some default data to show
spectra = np.loadtxt('caramel_file_viewer/spectra.txt')
cont = np.loadtxt('caramel_file_viewer/continuum.txt')
times = np.loadtxt('caramel_file_viewer/times.txt')
cont[:,0] /= 86400.
times[:,0] /= 86400.
cont[:,0] -= 2450000
times[:,0] -= 2450000
wave = spectra[0]
spec = spectra[1::2]
err = spectra[2::2]


df_cont = pd.DataFrame(cont, columns=['time','flux','flux_err'])
df_int = pd.DataFrame(
    np.vstack([
        times[:,0],
        np.sum(spec,axis=1),
        np.sqrt(np.sum(err**2,axis=1))
    ]).T,
    columns=['time','flux','flux_err']
)

# TODO: Temporary fix -- currently appending np.zeros() spectra to the end of the
#       spectrum DataFrame. This is to account for the new uploaded files to have
#       more spectra than the default. Currently maxed at 200.
npad = 200
pad = np.zeros((npad-len(spec),len(spec[0])))
df_spec = pd.DataFrame(np.vstack([wave,spec,pad]).T, columns=['wave'] + [str(i) for i in range(npad)])  #, columns=['wave']+times[:,0].tolist())
source_spec = ColumnDataSource(df_spec)
df_cont = pd.DataFrame(cont, columns=['time','flux','flux_err'])
source_cont = ColumnDataSource(df_cont)
source_int = ColumnDataSource(df_int)

# Create the figure panels
# Continuum
p1 = figure(
    width=400,height=150,
    x_axis_label='HJD - 2450000',
    y_axis_label='Continuum',
    tools=""
)
p1.scatter('time','flux', color='blue', source=source_cont, name='continuum')

# Integrated emission line
p2 = figure(
    width=400,height=150,
    x_axis_label='HJD - 2450000',
    y_axis_label='Emission line',
    x_range=p1.x_range,
    tools=""
)
p2.scatter('time','flux', color='orange', source=source_int, name='integrated')

# Emission line spectra
p3 = figure(
    width=300,height=300,
    x_axis_label='Wavelength (Ang)',
    y_axis_label='Flux',
)

for i in range(npad):
    p3.line('wave', str(i), source=source_spec, color='grey', width=0.5, alpha=0.5)
# Create "highlighted" versions of each spectrum, but set visible=False
line_highlighted = {}
for i in range(npad):
    line_highlighted[i] = p3.line('wave', str(i), source=source_spec, color='orange', width=2, visible=False)

# CustomJS callback for the hover tool
callback_hover_js = CustomJS(args=dict(line=line_highlighted, source=source_int), code="""
    const data = source.data;
    const times = data.time;
    
    // Reset all previously highlighted lines
    for (var i=0; i<times.length; i++) {
        line[i].properties.visible.spec.value = false;
        line[i].change.emit();
    }
    
    // Get the x position of the cursor
    const geometry = cb_data.geometry;
    const xval = geometry['x'];

    // Find the closest of the plotted dates
    var closest;
    var distance = 1e9;  // Require maximum 1e9 day distance
    for (var i=0; i<times.length; i++) {
        if (Math.abs(xval - times[i]) < distance) {
            closest = i;
            distance = Math.abs(xval - times[i]);
        }
    }
    
    // Dynamically set the maximum distance to highlight
    // This should account for, various lengths of observing campaigns.
    const maxdist = (times[times.length-1] - times[0])/50;
    if (distance < maxdist) {
        line[closest].properties.visible.spec.value = true;
        line[closest].change.emit();
    }
    """)

TOOLTIPS = [
    ('MJD', '@time'),
    ('Flux','@flux'),
    ('Error','@flux_err')
]
TOOLS = [
    PanTool(),
    WheelZoomTool(dimensions='width'),
    CrosshairTool(dimensions='height'),
    HoverTool(
         tooltips=TOOLTIPS,
         mode='vline',
         #names=['continuum','integrated'],
         line_policy='none',
         callback=callback_hover_js
     )
]
for tool in TOOLS:
    p1.add_tools(tool)
    p2.add_tools(tool)
p1.toolbar.active_scroll = TOOLS[1]
p2.toolbar.active_scroll = TOOLS[1]
p1.toolbar_location = None
p2.toolbar_location = None

# Array to keep track of which files have been loaded
new_files = np.array([0,0,0])
def update_data():
    new_files = np.array([0,0,0])
    print("New files loaded")
    
    cont[:,0] /= 86400.
    times[:,0] /= 86400.
    cont[:,0] -= 2450000
    times[:,0] -= 2450000
    
    new_data_int = {'time': times[:,0], 'flux': np.sum(spec,axis=1), 'flux_err': np.sqrt(np.sum(err**2,axis=1))}
    new_data_cont = {'time': cont[:,0], 'flux': cont[:,1], 'flux_err': cont[:,2]}
    new_data_spec = {'wave': wave}
    
    for i in range(len(spec)):
        new_data_spec[str(i)] = spec[i]
    for i in range(len(spec),npad):
        new_data_spec[str(i)] = np.zeros(len(spec[0]))

    source_int.data = new_data_int
    source_cont.data = new_data_cont
    source_spec.data = new_data_spec

def upload_spectra(attr, old, new):
    global wave, spec, err
    decoded = b64decode(new).decode('ascii')
    spectra = np.array([[float(item) for item in line.split(' ')] for line in decoded.splitlines()[1:]])
    wave = spectra[0]
    spec = spectra[1::2]
    err = spectra[2::2]
    
    new_files[0] = 1
    if np.prod(new_files) == 1:
        update_data()

def upload_continuum(attr, old, new):
    global cont
    decoded = b64decode(new).decode('ascii')
    cont = np.array([[float(item) for item in line.split(' ')] for line in decoded.splitlines()])

    new_files[1] = 1
    if np.prod(new_files) == 1:
        update_data()

def upload_times(attr, old, new):
    global times
    decoded = b64decode(new).decode('ascii')
    times = np.array([[float(item) for item in line.split(' ')] for line in decoded.splitlines()])
    
    new_files[2] = 1
    if np.prod(new_files) == 1:
        update_data()

div_spec = Div(text="Spectrum:")
div_time = Div(text="Times:")
div_cont = Div(text="Continuum:")
file_input_spec = FileInput(accept=".txt")
file_input_spec.on_change('value', upload_spectra)
file_input_time = FileInput(accept=".txt")
file_input_time.on_change('value', upload_times)
file_input_cont = FileInput(accept=".txt")
file_input_cont.on_change('value', upload_continuum)

# Set the layout with the sliders and plot
layout = row(
    column(p1, p2),
    p3,
    column(div_spec, file_input_spec, div_time, file_input_time, div_cont, file_input_cont)
)

# add the layout to curdoc
curdoc().add_root(layout)