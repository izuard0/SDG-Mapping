import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import re
import plotly.express as px
from itertools import combinations
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
    # This function now handles cases where there's only one author more gracefully.
    if not isinstance(author_string, str):
        return []
    # We still split by comma or semicolon for cases that have them.
    authors = [a.strip() for a in re.split(r'[,;]', author_string) if a.strip()]
    return authors

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data_terpetakan_final.csv')
        # We use the original_author field directly now for grouping, as per your logic.
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
        st.title("🤝 Potential Collaboration Network by SDG")
        st.markdown("""
        This network connects researchers who have published work on the **same SDG topic**. 
        Use the dropdown to **filter the view** and see the specific collaboration cluster for each SDG.
        """)

        # --- NEW LOGIC INSPIRED BY YOUR SCRIPT ---
        
        # 1. Group unique authors for each SDG
        df_mapped = df[df['sdg_mapping'].notna()].copy()
        collaboration_groups = df_mapped.groupby('sdg_mapping')['original_author'].unique()

        # 2. Build the graph based on shared SDGs
        G = nx.Graph()
        # Map authors to all their SDGs for hover info
        author_sdg_map = defaultdict(set)
        
        for sdg, authors in collaboration_groups.items():
            # Clean up author names within the group
            unique_authors_in_sdg = {author.strip() for author_str in authors for author in split_authors(author_str)}
            
            # Add SDG info to each author
            for author in unique_authors_in_sdg:
                author_sdg_map[author].add(sdg)

            # Create edges between all authors in the same SDG group
            for author1, author2 in combinations(unique_authors_in_sdg, 2):
                if G.has_edge(author1, author2):
                    G[author1][author2]['weight'] += 1
                else:
                    G.add_edge(author1, author2, weight=1)

        # 3. Prepare data for filtering
        sdg_list = ["- Show All -"] + sorted(df['sdg_mapping'].dropna().unique().tolist())
        selected_sdg = st.selectbox('Select an SDG to filter the network:', sdg_list)

        # 4. Filter the graph if an SDG is selected
        if selected_sdg != "- Show All -":
            # Get all authors related to the selected SDG
            authors_in_selected_sdg = {author.strip() for author_str in collaboration_groups.get(selected_sdg, []) for author in split_authors(author_str)}
            # Create a subgraph containing only these authors
            Sub_G = G.subgraph(authors_in_selected_sdg)
        else:
            Sub_G = G

        st.subheader("Graph Statistics")
        stats_col1, stats_col2 = st.columns(2)
        stats_col1.metric("Researchers Displayed (Nodes)", Sub_G.number_of_nodes())
        stats_col2.metric("Potential Collaborations (Edges)", Sub_G.number_of_edges())

        if Sub_G.number_of_nodes() > 0:
            # Add hover data to nodes
            for node in Sub_G.nodes():
                sdgs = author_sdg_map.get(node, set())
                title = f"{node}<br><b>SDGs:</b> {', '.join(sorted(list(sdgs)))}" if sdgs else node
                Sub_G.nodes[node]['title'] = title

            # 5. Visualize the (potentially filtered) graph
            net = Network(height='750px', width='100%', notebook=True, cdn_resources='in_line', directed=False)
            net.from_nx(Sub_G)

            # Increase node size based on degree (number of connections)
            for node in net.nodes:
                node['size'] = 10 + Sub_G.degree(node['id']) * 3

            try:
                path = os.path.join('temp', 'sdg_collaboration_graph.html')
                net.save_graph(path)
                with open(path, 'r', encoding='utf-8') as HtmlFile:
                    source_code = HtmlFile.read()
                    components.html(source_code, height=800, scrolling=True)
            except Exception as e:
                st.error(f"An error occurred while generating the graph: {e}")
        else:
            st.warning(f"No potential collaborations found for '{selected_sdg}'. This might mean there is only one author publishing on this topic in the dataset.")
