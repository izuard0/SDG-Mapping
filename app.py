import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import re
import plotly.express as px
from collections import defaultdict

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Publication Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- DATA & FUNCTIONS ---
if not os.path.exists('temp'):
    os.makedirs('temp')

def split_authors(author_string):
    if not isinstance(author_string, str):
        return []
    authors = [a.strip() for a in re.split(r'[,;]', author_string) if a.strip()]
    return authors

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data_terpetakan_final.csv')
        df['authors_list'] = df['original_author'].apply(split_authors)
        df['publication_year'] = pd.to_numeric(df['publication_year'], errors='coerce')
        df.dropna(subset=['publication_year'], inplace=True)
        df['publication_year'] = df['publication_year'].astype(int)
        df['journal'] = df['journal'].astype(str).str.strip().str.title()
        df['journal'].replace(['Nan', ''], 'Not Available', inplace=True)
        return df
    except FileNotFoundError:
        st.error("Error: 'data_terpetakan_final.csv' not found.")
        return None

df = load_data()

# --- SDG DEFINITIONS ---
sdg_definitions = {
    "SDG 1": "No Poverty", "SDG 2": "Zero Hunger", "SDG 3": "Good Health and Well-being",
    "SDG 4": "Quality Education", "SDG 5": "Gender Equality", "SDG 6": "Clean Water and Sanitation",
    "SDG 7": "Affordable and Clean Energy", "SDG 8": "Decent Work and Economic Growth",
    "SDG 9": "Industry, Innovation, and Infrastructure", "SDG 10": "Reduced Inequality",
    "SDG 11": "Sustainable Cities and Communities", "SDG 12": "Responsible Consumption and Production",
    "SDG 13": "Climate Action", "SDG 14": "Life Below Water", "SDG 15": "Life on Land",
    "SDG 16": "Peace, Justice, and Strong Institutions", "SDG 17": "Partnerships for the Goals"
}

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation 🗺️")
page = st.sidebar.radio("Choose a page:", ["General Analysis", "Researcher Collaboration Network"])

with st.sidebar.expander("ℹ️ About the SDGs"):
    for key, value in sdg_definitions.items():
        st.write(f"**{key}**: {value}")

# --- PAGE CONTENT ---
if df is not None:
    if page == "General Analysis":
        st.title("📊 General Publication Analysis Dashboard")
        st.markdown("This page presents general insights from the publication dataset.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Publication Trend by Year")
            yearly_counts = df[df['publication_year'] > 1980]['publication_year'].value_counts().sort_index().reset_index()
            yearly_counts.columns = ['Year', 'Count']
            fig1 = px.line(yearly_counts, x='Year', y='Count', markers=True, labels={'Count': 'Number of Publications'})
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader("🏆 Top 15 Most Prolific Researchers")
            all_authors_df = df.explode('authors_list')
            top_authors = all_authors_df['authors_list'].value_counts().nlargest(15).sort_values(ascending=True).reset_index()
            top_authors.columns = ['Researcher', 'Count']
            fig3 = px.bar(top_authors, y='Researcher', x='Count', orientation='h', text_auto=True, labels={'Count': 'Number of Publications'})
            fig3.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig3, use_container_width=True)

        with col2:
            st.subheader("🎯 Publication Distribution by SDG")
            sdg_counts = df['sdg_mapping'].value_counts().reset_index()
            sdg_counts.columns = ['SDG', 'Count']
            fig2 = px.bar(sdg_counts, x='SDG', y='Count', color='SDG', text_auto=True)
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("🔍 Mapping Level Proportions")
            mapping_counts = df['mapping_level'].value_counts().reset_index()
            mapping_counts.columns = ['Level', 'Count']
            fig4 = px.pie(mapping_counts, names='Level', values='Count', hole=0.4)
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)

    elif page == "Researcher Collaboration Network":
        st.title("🤝 Researcher Collaboration Network Map")
        st.markdown("This network shows all co-author relationships. Use the dropdown to **highlight** researchers associated with a specific SDG.")
        
        # --- Build the full collaboration graph ---
        G = nx.Graph()
        collaboration_df = df[df['authors_list'].str.len() > 1]
        for _, row in collaboration_df.iterrows():
            authors = row['authors_list']
            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    G.add_edge(authors[i], authors[j])
        
        # --- NEW: Display Graph Statistics for Debugging ---
        st.subheader("Graph Statistics")
        stats_col1, stats_col2 = st.columns(2)
        stats_col1.metric("Total Researchers (Nodes)", G.number_of_nodes())
        stats_col2.metric("Total Collaborations (Edges)", G.number_of_edges())

        if G.number_of_nodes() == 0:
            st.error("The collaboration graph is empty. This means no papers with more than one author were found. Please check that author names in your CSV are separated by a comma (,) or semicolon (;).")
        else:
            # Map every researcher to the SDGs they've published in
            researcher_sdg_map = defaultdict(set)
            for _, row in df.iterrows():
                sdg = row['sdg_mapping']
                if pd.notna(sdg):
                    for author in row['authors_list']:
                        researcher_sdg_map[author].add(sdg)

            # Add SDG info to each node in the graph for hover text
            for node in G.nodes():
                sdgs = researcher_sdg_map.get(node, set())
                title = f"{node}<br><b>SDGs:</b> {', '.join(sorted(list(sdgs)))}" if sdgs else node
                G.nodes[node]['title'] = title
                G.nodes[node]['sdgs'] = sdgs
            
            # Create the Pyvis network
            net = Network(height='750px', width='100%', notebook=True, cdn_resources='in_line', directed=False)
            net.from_nx(G)

            st.subheader("Highlight Network by SDG")
            sdg_list = ["- Show All -"] + sorted(df['sdg_mapping'].dropna().unique().tolist())
            selected_sdg = st.selectbox('Select an SDG to highlight researchers:', sdg_list)
            
            if selected_sdg != "- Show All -":
                for node in net.nodes:
                    if selected_sdg in G.nodes[node].get('sdgs', set()):
                        node['color'] = '#FF4B4B' # Bright Red
                        node['size'] = 25
                    else:
                        node['color'] = '#97C2FC' # Light Blue
                        node['size'] = 15
            
            try:
                path = os.path.join('temp', 'full_collaboration_graph.html')
                net.save_graph(path)
                with open(path, 'r', encoding='utf-8') as HtmlFile:
                    source_code = HtmlFile.read()
                    components.html(source_code, height=800, scrolling=True)
            except Exception as e:
                st.error(f"An error occurred while generating the graph: {e}")
