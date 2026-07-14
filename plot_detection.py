
import pandas
import plotly.express as px

in_path = 'out.csv'
df = pandas.read_csv(in_path)

fig = px.line(df, x='sample', y="onset")
fig.show()
