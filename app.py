import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import re
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Analisis Publikasi",
    page_icon="📊",
    layout="wide"
)

# --- FUNGSI & PERSIAPAN DATA ---

# Membuat direktori sementara jika belum ada
if not os.path.exists('temp'):
    os.makedirs('temp')

# Fungsi untuk memisahkan nama penulis dengan lebih baik
def split_authors(author_string):
    if not isinstance(author_string, str):
        return []
    authors = [a.strip() for a in re.split(r'[,;]', author_string) if a.strip()]
    return authors

# Fungsi load data dengan cache agar lebih cepat
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data_terpetakan_final.csv')
        df['authors_list'] = df['original_author'].apply(split_authors)
        df['publication_year'] = pd.to_numeric(df['publication_year'], errors='coerce')
        df.dropna(subset=['publication_year'], inplace=True)
        df['publication_year'] = df['publication_year'].astype(int)
        return df
    except FileNotFoundError:
        st.error("File 'data_terpetakan_final.csv' tidak ditemukan. Mohon pastikan file berada di folder yang sama dengan aplikasi.")
        return None

df = load_data()

# --- NAVIGASI SIDEBAR ---
st.sidebar.title("Navigasi 🗺️")
page = st.sidebar.radio("Pilih Halaman:", ["Analisis Umum", "Peta Kolaborasi Peneliti"])

# --- KONTEN HALAMAN ---
if df is not None:
    # HALAMAN 1: ANALISIS UMUM
    if page == "Analisis Umum":
        st.title("📊 Dashboard Analisis Umum Publikasi")
        st.markdown("Halaman ini menyajikan wawasan umum dari keseluruhan data publikasi.")

        # --- Membuat 2 kolom untuk layout yang lebih rapi ---
        col1, col2 = st.columns(2)

        with col1:
            # 1. Grafik Tren Publikasi per Tahun
            st.subheader("📈 Tren Jumlah Publikasi per Tahun")
            yearly_counts = df[df['publication_year'] > 1980]['publication_year'].value_counts().sort_index().reset_index()
            yearly_counts.columns = ['Tahun', 'Jumlah Publikasi']
            fig1 = px.line(yearly_counts, x='Tahun', y='Jumlah Publikasi', markers=True)
            st.plotly_chart(fig1, use_container_width=True)

            # 2. Grafik Jurnal Paling Populer
            st.subheader("🏆 Top 15 Jurnal Publikasi")
            top_journals = df['journal'].value_counts().nlargest(15).sort_values(ascending=True).reset_index()
            top_journals.columns = ['Jurnal', 'Jumlah']
            fig3 = px.bar(top_journals, y='Jurnal', x='Jumlah', orientation='h', text_auto=True)
            fig3.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig3, use_container_width=True)

        with col2:
            # 3. Grafik Distribusi SDG
            st.subheader("🎯 Distribusi Publikasi berdasarkan SDG")
            sdg_counts = df['sdg_mapping'].value_counts().reset_index()
            sdg_counts.columns = ['SDG', 'Jumlah']
            fig2 = px.bar(sdg_counts, x='SDG', y='Jumlah', color='SDG', text_auto=True)
            st.plotly_chart(fig2, use_container_width=True)

            # 4. Grafik Distribusi Mapping Level
            st.subheader("🔍 Proporsi Tingkat Pemetaan (Mapping Level)")
            mapping_counts = df['mapping_level'].value_counts().reset_index()
            mapping_counts.columns = ['Level', 'Jumlah']
            fig4 = px.pie(mapping_counts, names='Level', values='Jumlah', hole=0.4)
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)


    # HALAMAN 2: PETA KOLABORASI
    elif page == "Peta Kolaborasi Peneliti":
        st.title("🤝 Peta Jaringan Kolaborasi Peneliti")
        st.markdown("Pilih tipe visualisasi untuk melihat jaringan kolaborasi antar peneliti.")

        visualization_type = st.selectbox(
            'Pilih Tipe Visualisasi:',
            ('Berdasarkan SDG', 'Berdasarkan Peneliti')
        )

        if visualization_type == 'Berdasarkan SDG':
            st.subheader('Peta Kolaborasi berdasarkan SDG')
            sdg_list = sorted(df['sdg_mapping'].dropna().unique().tolist())
            selected_sdg = st.selectbox('Pilih SDG:', sdg_list)

            if selected_sdg:
                df_sdg = df[(df['sdg_mapping'] == selected_sdg) & (df['authors_list'].str.len() > 1)]
                if df_sdg.empty:
                    st.warning(f"Tidak ada data kolaborasi (>1 penulis) untuk {selected_sdg}.")
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

        elif visualization_type == 'Berdasarkan Peneliti':
            st.subheader('Peta Kolaborasi berdasarkan Peneliti')
            all_authors_list = [author for sublist in df['authors_list'].dropna() for author in sublist]
            all_authors = sorted(list(set(all_authors_list)))
            selected_author = st.selectbox('Pilih Peneliti:', all_authors)

            if selected_author:
                df_author = df[df['authors_list'].apply(lambda authors: selected_author in authors and len(authors) > 1)]
                if df_author.empty:
                    st.warning(f"Tidak ditemukan data kolaborasi untuk '{selected_author}'.")
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
