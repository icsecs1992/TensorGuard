import pandas as pd
import holoviews as hv
from holoviews import opts
hv.extension('bokeh')

# Sample data
data = {
    'A': [1, 4, 3, 2],
    'B': [4, 1, 3, 2],
    'C': [2, 4, 1, 3],
    'D': [3, 2, 4, 1]
}

df = pd.DataFrame(data)

# Create parallel coordinates with curves
parallel_plot = hv.ParallelCoordinates(df, kdims=['A', 'B', 'C', 'D']).opts(
    opts.ParallelCoordinates(curve=True, color_index='A', cmap='Category10', line_width=2)
)

hv.save(parallel_plot, 'curved_parallel_plot.html')
