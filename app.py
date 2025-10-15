import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import re
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Publication Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- DATA & FUNCTIONS ---

# Create a temporary directory if it doesn't exist
if not os.path.exists('temp'):
    os.makedirs('temp')

# Function to split author names more reliably
def split_authors(author_string):
    if not isinstance(author_string, str):
        return []
    # Splits authors by comma or semicolon
    authors = [a.strip() for a in re.split(r'[,;]', author_string) if a.strip()]
    return authors

# Cached function to load and process data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data_terpetakan_final.csv')
        # Clean author data
        df['authors_list'] = df['original_author'].apply(split_authors)
        # Clean publication year data
        df['publication_year'] = pd.to_numeric(df['publication_year'], errors='coerce')
        df.dropna(subset=['publication_year'], inplace=True)
        df['publication_year'] = df['publication_year'].astype(int)
        
        # --- FIX APPLIED HERE ---
        # Convert journal column to string type BEFORE using .str accessor to prevent AttributeError
        df['journal'] = df['journal'].astype(str).str.strip().str.title()
        # Replace blank/NaN values (which become 'Nan' after astype(str)) with a proper label
        df['journal'].replace(['Nan', ''], 'Not Available', inplace=True)

        return df
    except FileNotFoundError:
        st.error("Error: 'data_terpetakan_final.csv' not found. Please ensure the file is in the same repository folder.")
        return None

df = load_data()

# --- SDG DEFINITIONS ---
sdg_definitions = {
    "SDG 1": "No Poverty",
    "SDG 2": "Zero Hunger",
    "SDG 3": "Good Health and Well-being",
    "SDG 4": "Quality Education",
    "SDG 5": "Gender Equality",
    "SDG 6": "Clean Water and Sanitation",
    "SDG 7": "Affordable and Clean Energy",
    "SDG 8": "Decent Work and Economic Growth",
    "SDG 9": "Industry, Innovation, and Infrastructure",
    "SDG 10": "Reduced Inequality",
    "SDG 11": "Sustainable Cities and Communities",
    "SDG 12": "Responsible Consumption and Production",
    "SDG 13": "Climate Action",
    "SDG 14": "Life Below Water",
    "SDG 15": "Life on Land",
    "SDG 16": "Peace, Justice, and Strong Institutions",
    "SDG 17": "Partnerships for the Goals"
}

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation 🗺️")
page = st.sidebar.radio("Choose a page:", ["General Analysis", "Researcher Collaboration Network"])

with st.sidebar.expander("ℹ️ About the SDGs"):
    st.write("The 17 Sustainable Development Goals are:")
    for key, value in sdg_definitions.items():
        st.write(f"**{key}**: {value}")

# --- PAGE CONTENT ---
if df is not None:
    # PAGE 1: GENERAL ANALYSIS
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

            st.subheader("🏆 Top 15 Journals by Publication Count")
            top_journals = df['journal'].value_counts().nlargest(15).sort_values(ascending=True).reset_index()
            top_journals.columns = ['Journal', 'Count']
            fig3 = px.bar(top_journals, y='Journal', x='Count', orientation='h', text_auto=True)
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

    # PAGE 2: COLLABORATION NETWORK
    elif page == "Researcher Collaboration Network":
        st.title("🤝 Researcher Collaboration Network Map")
        st.markdown("Choose a visualization type to explore the collaboration network.")
        st.info("""
        **Note:** This map is generated by connecting authors who have co-authored a paper. 
        For this to work, author names in the `original_author` column of your CSV file must be separated by a **comma (,)** or a **semicolon (;)**. 
        If the graph appears empty, please check your data file's format.
        """)

        visualization_type = st.selectbox(
            'Select Visualization Type:',
            ('By SDG', 'By Researcher')
        )

        if visualization_type == 'By SDG':
            st.subheader('Collaboration Map by SDG')
            sdg_list = sorted(df['sdg_mapping'].dropna().unique().tolist())
            selected_sdg = st.selectbox('Select an SDG:', sdg_list)
            if selected_sdg:
                df_sdg = df[(df['sdg_mapping'] == selected_sdg) & (df['authors_list'].str.len() > 1)]
                if df_sdg.empty:
                    st.warning(f"No collaboration data (>1 author per paper) found for {selected_sdg}. This may be due to data formatting.", icon="⚠️")
                else:
                    G = nx.Graph()
                    for authors_list in df_sdg['authors_list']:
                        for i in range(len(authors_list)):
                            for j in range(i + 1, len(authors_list)):
                                G.add_edge(authors_list[i], authors_list[j])
                    net = Network(height='600px', width='100%', notebook=True, cdn_resources='in_line')
                    net.from_nx(G)
                    for node in net.nodes:
                        node['size'] = 15
                    path = os.path.join('temp', 'graph_sdg.html')
                    net.save_graph(path)
                    with open(path, 'r', encoding='utf-8') as HtmlFile:
                        source_code = HtmlFile.read()
                        components.html(source_code, height=610)

        elif visualization_type == 'By Researcher':
            st.subheader('Collaboration Map by Researcher')
            all_authors_list = [author for sublist in df['authors_list'].dropna() for author in sublist]
            all_authors = sorted(list(set(all_authors_list)))
            selected_author = st.selectbox('Select a Researcher:', all_authors)
            if selected_author:
                df_author = df[df['authors_list'].apply(lambda authors: selected_author in authors and len(authors) > 1)]
                if df_author.empty:
                    st.warning(f"No collaboration data found for '{selected_author}'. This could mean all their publications are single-authored or the data is not formatted with separators.", icon="⚠️")
                else:
                    G = nx.Graph()
                    G.add_node(selected_author, color='red', size=25)
                    for authors_list in df_author['authors_list']:
                        for co_author in authors_list:
                            if co_author != selected_author:
                                G.add_node(co_author, size=15)
                                G.add_edge(selected_author, co_author)
                    net = Network(height='600px', width='100%', notebook=True, cdn_resources='in_line')
                    net.from_nx(G)
                    path = os.path.join('temp', 'graph_researcher.html')
                    net.save_graph(path)
                    with open(path, 'r', encoding='utf-8') as HtmlFile:
                        source_code = HtmlFile.read()
                        components.html(source_code, height=610)
