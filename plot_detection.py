
import pandas
import plotly.express as px
import plotly.graph_objects as go

in_path = 'out.csv'
df = pandas.read_csv(in_path)
df['time_ms'] = df['t'] * 1000

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df['time_ms'],
    y=df['onset'],
    mode='lines+markers',
    marker=dict(size=4),
    line=dict(width=1),
    name='ax',
))

fig.update_xaxes(tickformat=',')

fig.show()
