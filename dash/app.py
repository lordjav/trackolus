import sqlalchemy, pandas, plotly.express

def create_graph():
    engine = sqlalchemy.create_engine("sqlite:///general_data.db")
    df = pandas.read_sql_query('SELECT * FROM inventory', engine)
    figure = plotly.express.bar(df, x='SKU', y='quantity').write_image('assets/image.svg')
    

create_graph()