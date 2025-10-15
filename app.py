import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

# Create a temporary directory for HTML files if it doesn't exist
if not os.path.exists('temp'):
    os.makedirs('temp')

# Load and prepare the data
@st.cache_data
def load_data():
    df = pd.read_csv('data_terpetakan_final.csv')
    # Assuming authors are comma-separated, this might need adjustment based on the actual separator.
    df['authors_list'] = df['original_author'].str.split(',')
    return df

df = load_data()

st.title('Dashboard Peta Kolaborasi Peneliti')

# Sidebar for user selection
st.sidebar.title('Opsi Visualisasi')
visualization_type = st.sidebar.selectbox(
    'Pilih Tipe Visualisasi:',
    ('Peta Kolaborasi berdasarkan SDG', 'Peta Kolaborasi berdasarkan Peneliti')
)

if visualization_type == 'Peta Kolaborasi berdasarkan SDG':
    st.header('Peta Kolaborasi berdasarkan SDG')

    # Get unique SDGs
    sdg_list = sorted(df['sdg_mapping'].dropna().unique().tolist())
    selected_sdg = st.selectbox('Pilih SDG:', sdg_list)

    if selected_sdg:
        # Filter data by selected SDG
        df_sdg = df[df['sdg_mapping'] == selected_sdg].dropna(subset=['authors_list'])

        # Create a graph
        G = nx.Graph()

        # Iterate over each paper in the filtered dataframe
        for authors in df_sdg['authors_list']:
            authors = [author.strip() for author in authors]
            
            # Add nodes for authors
            for author in authors:
                if not G.has_node(author):
                    G.add_node(author, title=author)
            
            # Add edges for co-authorships
            if len(authors) > 1:
                for i in range(len(authors)):
                    for j in range(i + 1, len(authors)):
                        if not G.has_edge(authors[i], authors[j]):
                            G.add_edge(authors[i], authors[j])

        # Create a pyvis network
        net = Network(height='600px', width='100%', notebook=True, cdn_resources='in_line')
        net.from_nx(G)
        
        # Customize node appearance
        for node in net.nodes:
            node['size'] = 15
            node['font'] = {'size': 12}

        # Generate and display the graph HTML
        try:
            path = os.path.join('temp', 'collaboration_graph_sdg.html')
            net.save_graph(path)
            with open(path, 'r', encoding='utf-8') as HtmlFile:
                source_code = HtmlFile.read()
                components.html(source_code, height=610)
        except Exception as e:
            st.error(f"Error generating graph: {e}")

elif visualization_type == 'Peta Kolaborasi berdasarkan Peneliti':
    st.header('Peta Kolaborasi berdasarkan Peneliti')

    # Get unique authors
    all_authors = sorted(list(set(author.strip() for authors_list in df['authors_list'].dropna() for author in authors_list)))
    selected_author = st.selectbox('Pilih Peneliti:', all_authors)

    if selected_author:
        # Find papers by the selected author
        df_author = df[df['original_author'].str.contains(selected_author, na=False)].dropna(subset=['authors_list'])

        # Create a graph
        G = nx.Graph()

        # Add the selected author as the central node
        G.add_node(selected_author, color='red', size=25)

        # Find co-authors and create edges
        for authors in df_author['authors_list']:
            authors = [author.strip() for author in authors]
            if selected_author in authors:
                for author in authors:
                    if author != selected_author:
                        if not G.has_node(author):
                            G.add_node(author, title=author, size=15)
                        if not G.has_edge(selected_author, author):
                            G.add_edge(selected_author, author)

        # Create a pyvis network
        net = Network(height='600px', width='100%', notebook=True, cdn_resources='in_line')
        net.from_nx(G)

        # Customize node appearance
        for node in net.nodes:
            if node['id'] == selected_author:
                node['color'] = 'red'
                node['size'] = 25
            else:
                node['size'] = 15
            node['font'] = {'size': 12}

        # Generate and display the graph HTML
        try:
            path = os.path.join('temp', 'collaboration_graph_researcher.html')
            net.save_graph(path)
            with open(path, 'r', encoding='utf-8') as HtmlFile:
                source_code = HtmlFile.read()
                components.html(source_code, height=610)
        except Exception as e:
            st.error(f"Error generating graph: {e}")