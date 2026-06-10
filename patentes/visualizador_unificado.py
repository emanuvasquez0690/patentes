from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover
    get_script_run_ctx = None

import numpy as np

from patentes.hrhc_visualizador_utils import (
    apply_filters as apply_filters_hrhc,
    fetch_hrhc_convocatoria_21,
    get_available_cities as get_available_cities_hrhc,
    save_temp_cache as save_temp_cache_hrhc,
)
from patentes.patentes_visualizador_utils import (
    apply_filters as apply_filters_patentes,
    fetch_patentes_global,
    get_available_cities as get_available_cities_patentes,
    save_temp_cache as save_temp_cache_patentes,
)


@dataclass(frozen=True)
class ViewConfig:
    key: str
    icon: str
    title: str
    caption: str
    menu_hint: str
    session_df_key: str
    session_cache_key: str
    fetch_fn: Callable[[], pd.DataFrame]
    save_cache_fn: Callable[[pd.DataFrame], object]
    render_fn: Callable[[pd.DataFrame], None]


def apply_custom_style() -> None:
    # Obtener tema del session_state
    is_dark = st.session_state.get("dark_mode", False)
    
    if is_dark:
        # Tema oscuro
        hero_bg = "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)"
        hero_text = "#ffffff"
        card_bg = "#0f3460"
        card_border = "#533483"
        subtitle_opacity = "0.85"
        home_card_bg = "#1a1a2e"
        home_card_border = "#16213e"
        text_color = "#e0e0e0"
    else:
        # Tema claro (original)
        hero_bg = "linear-gradient(135deg, #2E4EF2 0%, #6A7BFF 100%)"
        hero_text = "#ffffff"
        card_bg = "#f8fbff"
        card_border = "#E7EAF3"
        subtitle_opacity = "0.92"
        home_card_bg = "#ffffff"
        home_card_border = "#E7EAF3"
        text_color = "#4b587c"
    
    st.markdown(
        f"""
        <style>
        .hero-card {{
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.9rem;
            background: {hero_bg};
            color: {hero_text};
        }}
        .hero-title {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }}
        .hero-subtitle {{
            font-size: 0.95rem;
            opacity: {subtitle_opacity};
        }}
        .home-card {{
            border: 1px solid {home_card_border};
            border-radius: 12px;
            padding: 0.9rem;
            background: {home_card_bg};
            min-height: 120px;
            margin-bottom: 0.8rem;
        }}
        .selector-caption {{
            color: {text_color};
            font-size: 0.93rem;
            margin-bottom: 0.6rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def fetch_catalogue() -> pd.DataFrame:
    """Carga el catálogo de datasets desde datasets.json."""
    datasets_path = Path(__file__).parent.parent / "datasets.json"
    if not datasets_path.exists():
        st.error("Archivo datasets.json no encontrado. Ejecuta prueba/apis.py primero.")
        return pd.DataFrame()
    try:
        import json
        with open(datasets_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error cargando catálogo: {e}")
        return pd.DataFrame()


def search_catalogue(catalogue_df: pd.DataFrame, query: str, selected_tags: List[str]) -> pd.DataFrame:
    """Filtra el catálogo por búsqueda de texto y tags."""
    if not query and not selected_tags:
        return catalogue_df
    
    filtered_df = catalogue_df.copy()
    query_lower = query.lower() if query else ""
    
    if query:
        # Filtrar por texto en nombre o descripción
        text_mask = (
            filtered_df["nombre"].str.lower().str.contains(query_lower, na=False) |
            filtered_df["descripcion"].str.lower().str.contains(query_lower, na=False)
        )
        filtered_df = filtered_df[text_mask]
    
    if selected_tags:
        # Filtrar por tags (asumiendo tags es una lista en cada fila)
        tag_mask = filtered_df["tags"].apply(lambda tags: any(tag in tags for tag in selected_tags) if tags else False)
        filtered_df = filtered_df[tag_mask]
    
    return filtered_df


@st.cache_data
def preview_dataset(api_url: str, limit: int = 50) -> pd.DataFrame:
    """Obtiene una previsualización limitada del dataset."""
    try:
        params = {"$limit": limit}
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error obteniendo previsualización: {e}")
        return pd.DataFrame()


def save_temp_cache_catalogue(df: pd.DataFrame) -> None:
    """No guarda cache para catálogo, ya que usa st.cache_data."""
    pass


@st.cache_data
def fetch_full_dataset(api_url: str) -> pd.DataFrame:
    """Obtiene el dataset completo usando paginación."""
    try:
        all_records = []
        offset = 0
        page_size = 1000
        
        while True:
            params = {"$limit": page_size, "$offset": offset}
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            chunk = response.json()
            
            if not chunk:
                break
            
            all_records.extend(chunk)
            
            if len(chunk) < page_size:
                break
            
            offset += page_size
            
            # Límite de seguridad para no descargar datasets enormes
            if len(all_records) > 50000:
                st.warning("Dataset muy grande. Mostrando solo los primeros 50,000 registros.")
                break
        
        return pd.DataFrame(all_records)
    except Exception as e:
        st.error(f"Error descargando dataset completo: {e}")
        return pd.DataFrame()


def detect_dataset_type(dataset_info: pd.Series, preview_df: pd.DataFrame) -> str:
    """Detecta el tipo de dataset para aplicar visualización adaptada."""
    name = dataset_info.get("nombre", "").lower()
    columns = preview_df.columns.str.lower().tolist()
    
    # Detectar patentes
    if ("patente" in name or 
        any(col in columns for col in ["pais", "region", "ciudad", "naturaleza", "solicitante"])):
        return "patentes"
    
    # Detectar HRHC
    if ("grupos" in name or "investigacion" in name or "hrhc" in name or
        any(col in columns for col in ["nme_pais_gr", "nme_region_gr", "nme_clasificacion_gr"])):
        return "hrhc"
    
    return "generic"


def render_adaptive_preview(selected_dataset: pd.Series) -> None:
    """Renderiza previsualización adaptada según el tipo de dataset."""
    api_url = selected_dataset["api_url"]
    
    with st.spinner("Cargando previsualización..."):
        preview_df = preview_dataset(api_url)
    
    if preview_df.empty:
        st.warning("No se pudo cargar la previsualización del dataset.")
        return
    
    dataset_type = detect_dataset_type(selected_dataset, preview_df)
    
    st.subheader(f"Previsualización: {selected_dataset['nombre']}")
    
    # Información del dataset
    with st.expander("Información del Dataset", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Tipo detectado:** {dataset_type.title()}")
            st.write(f"**Última actualización:** {selected_dataset.get('ultima_actualizacion', 'N/A')}")
        with col2:
            st.write(f"**Tags:** {', '.join(selected_dataset.get('tags', []))}")
            st.write(f"**API URL:** {api_url}")
    
    # Botón de descarga
    col_download, col_refresh = st.columns([1, 1])
    with col_download:
        if st.button("📥 Descargar Dataset Completo", key="download_full"):
            with st.spinner("Descargando dataset completo..."):
                full_df = fetch_full_dataset(api_url)
                if not full_df.empty:
                    csv = full_df.to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar CSV",
                        data=csv,
                        file_name=f"{selected_dataset['nombre'].replace(' ', '_')}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                    st.success(f"Dataset descargado: {len(full_df)} registros")
                else:
                    st.error("No se pudo descargar el dataset completo.")
    
    with col_refresh:
        if st.button("🔄 Recargar Previsualización", key="refresh_preview"):
            st.rerun()
    
    # Renderizar según tipo
    if dataset_type == "patentes":
        render_patentes_preview(preview_df)
    elif dataset_type == "hrhc":
        render_hrhc_preview(preview_df)
    else:
        render_generic_preview(preview_df)


def render_patentes_preview(df: pd.DataFrame) -> None:
    """Previsualización adaptada para datasets de patentes."""
    # Limpiar dataframe como en patentes_visualizador_utils
    df = df.copy()
    columns_to_fill = ["pais", "region", "ciudad", "naturaleza", "solicitante", "a_o_concesi_n"]
    for column in columns_to_fill:
        if column not in df.columns:
            df[column] = ""
    
    for col in ["pais", "region", "ciudad", "naturaleza", "solicitante"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    
    df["region"] = df["region"].replace("", "SIN_REGION")
    df["ciudad"] = df["ciudad"].replace("", "SIN_CIUDAD")
    df["anio_concesion"] = pd.to_numeric(df["a_o_concesi_n"], errors="coerce")
    
    # Filtros simples
    with st.sidebar:
        st.header("Filtros Rápidos")
        if "pais" in df.columns:
            paises = sorted(df["pais"].dropna().unique().tolist())
            selected_pais = st.selectbox("País", ["Todos"] + paises, key="preview_pais")
            if selected_pais != "Todos":
                df = df[df["pais"] == selected_pais]
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros", f"{len(df):,}")
    col2.metric("Regiones", f"{df['region'].nunique():,}")
    col3.metric("Ciudades", f"{df['ciudad'].nunique():,}")
    col4.metric("Países", f"{df['pais'].nunique():,}")
    
    # Gráficos
    left, right = st.columns(2)
    with left:
        if "region" in df.columns:
            region_counts = df["region"].value_counts().head(15)
            fig_region = px.bar(
                region_counts, 
                x=region_counts.index, 
                y=region_counts.values,
                title="Top 15 regiones por patentes"
            )
            st.plotly_chart(fig_region, use_container_width=True)
    
    with right:
        if "naturaleza" in df.columns:
            nat_counts = df["naturaleza"].value_counts().head(10)
            fig_nat = px.pie(
                nat_counts, 
                values=nat_counts.values, 
                names=nat_counts.index,
                title="Distribución por naturaleza"
            )
            st.plotly_chart(fig_nat, use_container_width=True)
    
    st.dataframe(df.head(50))


def render_hrhc_preview(df: pd.DataFrame) -> None:
    """Previsualización adaptada para datasets de grupos de investigación."""
    # Limpiar como en hrhc_visualizador_utils
    df = df.copy()
    required = ["nme_pais_gr", "nme_region_gr", "nme_departamento_gr", "nme_municipio_gr", 
                "nme_clasificacion_gr", "nme_gran_area_gr", "nme_convocatoria", "ano_convo"]
    
    for column in required:
        if column not in df.columns:
            df[column] = ""
    
    text_cols = ["nme_pais_gr", "nme_region_gr", "nme_departamento_gr", "nme_municipio_gr", 
                 "nme_clasificacion_gr", "nme_gran_area_gr", "nme_convocatoria"]
    
    for column in text_cols:
        df[column] = df[column].fillna("").astype(str).str.strip()
    
    df = df[df["nme_pais_gr"].str.upper() == "COLOMBIA"]
    df["region"] = df["nme_departamento_gr"].replace("", pd.NA).fillna(df["nme_region_gr"]).fillna("SIN_REGION")
    df["ciudad"] = df["nme_municipio_gr"].replace("", "SIN_CIUDAD")
    df["clasificacion"] = df["nme_clasificacion_gr"].replace("", "SIN_CLASIFICACION")
    df["gran_area"] = df["nme_gran_area_gr"].replace("", "SIN_AREA")
    df["anio_convocatoria"] = pd.to_datetime(df["ano_convo"], errors="coerce").dt.year
    
    # Filtros simples
    with st.sidebar:
        st.header("Filtros Rápidos")
        if "region" in df.columns:
            regiones = sorted(df["region"].dropna().unique().tolist())
            selected_region = st.selectbox("Región", ["Todas"] + regiones, key="preview_region")
            if selected_region != "Todas":
                df = df[df["region"] == selected_region]
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Grupos", f"{len(df):,}")
    col2.metric("Regiones", f"{df['region'].nunique():,}")
    col3.metric("Ciudades", f"{df['ciudad'].nunique():,}")
    col4.metric("Áreas", f"{df['gran_area'].nunique():,}")
    
    # Gráficos
    left, right = st.columns(2)
    with left:
        if "region" in df.columns:
            region_counts = df["region"].value_counts().head(15)
            fig_region = px.bar(
                region_counts, 
                x=region_counts.index, 
                y=region_counts.values,
                title="Top 15 regiones por grupos"
            )
            st.plotly_chart(fig_region, use_container_width=True)
    
    with right:
        if "gran_area" in df.columns:
            area_counts = df["gran_area"].value_counts().head(10)
            fig_area = px.pie(
                area_counts, 
                values=area_counts.values, 
                names=area_counts.index,
                title="Distribución por gran área"
            )
            st.plotly_chart(fig_area, use_container_width=True)
    
    st.dataframe(df.head(50))


def render_generic_preview(df: pd.DataFrame) -> None:
    """Previsualización genérica para datasets no reconocidos."""
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas en muestra", f"{len(df):,}")
    col2.metric("Columnas", f"{len(df.columns):,}")
    col3.metric("Tipos de datos únicos", f"{df.dtypes.nunique():,}")
    
    # Contar valores no nulos
    non_null_pct = (df.notna().sum().sum() / (len(df) * len(df.columns))) * 100
    col4.metric("Completitud (%)", f"{non_null_pct:.1f}")
    
    # Tipos de columnas
    with st.expander("Tipos de Columnas"):
        dtypes_df = pd.DataFrame({
            "Columna": df.columns,
            "Tipo": df.dtypes.astype(str),
            "No Nulos": df.notna().sum(),
            "Únicos": df.nunique()
        })
        st.dataframe(dtypes_df)
    
    # Gráficos
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        st.subheader("Análisis Numérico")
        left, right = st.columns(2)
        
        with left:
            # Histograma de la primera columna numérica
            if len(numeric_cols) > 0:
                fig_hist = px.histogram(
                    df, 
                    x=numeric_cols[0], 
                    title=f"Distribución de {numeric_cols[0]}",
                    marginal="box"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with right:
            # Boxplot si hay más de una numérica
            if len(numeric_cols) > 1:
                fig_box = px.box(
                    df[numeric_cols[:5]],  # Máximo 5 para no sobrecargar
                    title="Boxplots de variables numéricas"
                )
                st.plotly_chart(fig_box, use_container_width=True)
    
    # Gráfico de categorías si hay columnas categóricas
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if categorical_cols:
        st.subheader("Análisis Categórico")
        # Tomar la primera columna categórica con pocos valores únicos
        cat_col = None
        for col in categorical_cols:
            if df[col].nunique() <= 20:  # Máximo 20 categorías
                cat_col = col
                break
        
        if cat_col:
            cat_counts = df[cat_col].value_counts().head(15)
            fig_cat = px.bar(
                cat_counts, 
                x=cat_counts.index, 
                y=cat_counts.values,
                title=f"Top categorías en {cat_col}",
                labels={cat_col: "Categoría", "y": "Frecuencia"}
            )
            st.plotly_chart(fig_cat, use_container_width=True)
    
    # Muestra de datos
    st.subheader("Muestra de Datos")
    st.dataframe(df.head(20))


def render_catalogue(catalogue_df: pd.DataFrame) -> None:
    """Renderiza la vista del catálogo de datasets en estilo tabla con selección de fila."""
    st.subheader("Catálogo de Datasets")
    
    # Filtros en sidebar
    with st.sidebar:
        st.header("Filtros")
        search_query = st.text_input("Buscar por nombre o descripción", key="catalog_search")
        
        # Obtener todos los tags únicos
        all_tags = set()
        for tags_list in catalogue_df["tags"].dropna():
            if isinstance(tags_list, list):
                all_tags.update(tags_list)
        all_tags = sorted(list(all_tags))
        
        selected_tags = st.multiselect("Filtrar por tags", options=all_tags, key="catalog_tags")
    
    # Aplicar filtros
    filtered_catalogue_df = search_catalogue(catalogue_df, search_query, selected_tags)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total datasets", len(catalogue_df))
    col2.metric("Datasets filtrados", len(filtered_catalogue_df))
    col3.metric("Tags únicos", len(all_tags))
    
    if filtered_catalogue_df.empty:
        st.info("No se encontraron datasets que coincidan con los filtros.")
        return
    
    # Preparar tabla para mostrar
    display_df = filtered_catalogue_df.copy()
    display_df["descripcion_corta"] = display_df["descripcion"].str[:100] + "..."
    display_df["tags_str"] = display_df["tags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    display_df = display_df[["nombre", "descripcion_corta", "tags_str", "ultima_actualizacion", "api_url"]]
    display_df.columns = ["Nombre", "Descripción", "Tags", "Última Actualización", "API URL"]
    
    # Mostrar tabla con selección de fila
    event = st.dataframe(
        display_df, 
        selection_mode="single-row",
        on_select="rerun",
        key="catalog_table"
    )
    
    # Obtener dataset seleccionado
    selected_rows = event.selection.rows
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_dataset = filtered_catalogue_df.iloc[selected_idx]
        
        st.divider()
        render_adaptive_preview(selected_dataset)
    else:
        st.info("Selecciona una fila de la tabla para ver la previsualización del dataset.")


def render_portal_header() -> None:
    # Cargar y mostrar logos
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if Path("png rionegro logo.png").exists():
            st.image("png rionegro logo.png", width=300)
    
    with col3:
        if Path("logo innovación.webp").exists():
            st.image("logo innovación.webp", width=300)
    
    # Header original
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Portal unificado de datos abiertos</div>
            <div class="hero-subtitle">Selecciona un visualizador y explora estadisticas con filtros en el panel lateral.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_config_by_key(view_key: str) -> Optional[ViewConfig]:
    for config in VIEW_REGISTRY.values():
        if config.key == view_key:
            return config
    return None


def render_sidebar_toolbar() -> str:
    view_names = list(VIEW_REGISTRY.keys())

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"
    if "toolbar_selected_name" not in st.session_state:
        st.session_state["toolbar_selected_name"] = view_names[0]
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    with st.sidebar:
        # Toggle para modo oscuro
        st.session_state["dark_mode"] = st.toggle(
            "🌙 Modo oscuro",
            value=st.session_state["dark_mode"],
            key="theme_toggle"
        )
        st.divider()
        
        st.markdown("## Menu")
        if st.button("🏠 Inicio", key="home_toolbar_btn", use_container_width=True):
            st.session_state["current_page"] = "home"

        selected_name = st.selectbox(
            "Visualizadores",
            options=view_names,
            index=view_names.index(st.session_state["toolbar_selected_name"])
            if st.session_state["toolbar_selected_name"] in view_names
            else 0,
            key="toolbar_view_select",
        )
        st.session_state["toolbar_selected_name"] = selected_name

        if st.button("Abrir visualizador", key="toolbar_open_btn", use_container_width=True, type="primary"):
            st.session_state["current_page"] = VIEW_REGISTRY[selected_name].key

        st.caption(VIEW_REGISTRY[selected_name].menu_hint)
        st.divider()

    return st.session_state["current_page"]


def render_home_page() -> None:
    st.subheader("Bienvenido")
    st.write(
        "Esta es la pagina principal. Selecciona un visualizador desde la toolbar lateral o desde las opciones disponibles."
    )

    view_names = list(VIEW_REGISTRY.keys())
    per_row = min(3, max(1, len(view_names)))

    for start in range(0, len(view_names), per_row):
        row = st.columns(per_row)
        for idx, name in enumerate(view_names[start : start + per_row]):
            config = VIEW_REGISTRY[name]
            with row[idx]:
                st.markdown('<div class="home-card">', unsafe_allow_html=True)
                st.markdown(f"### {config.icon} {name}")
                st.caption(config.menu_hint)
                if st.button(
                    f"Entrar a {name}",
                    key=f"home_open_{config.key}",
                    use_container_width=True,
                ):
                    st.session_state["toolbar_selected_name"] = name
                    st.session_state["current_page"] = config.key
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


def load_data(config: ViewConfig) -> pd.DataFrame:
    if config.session_df_key not in st.session_state:
        with st.spinner("Descargando datos desde Socrata..."):
            st.session_state[config.session_df_key] = config.fetch_fn()
            cache_path = config.save_cache_fn(st.session_state[config.session_df_key])
            st.session_state[config.session_cache_key] = str(cache_path)
    return st.session_state[config.session_df_key]


def refresh_data(config: ViewConfig) -> pd.DataFrame:
    with st.spinner("Recargando datos desde Socrata..."):
        st.session_state[config.session_df_key] = config.fetch_fn()
        cache_path = config.save_cache_fn(st.session_state[config.session_df_key])
        st.session_state[config.session_cache_key] = str(cache_path)
    return st.session_state[config.session_df_key]


def render_patentes(df: pd.DataFrame) -> None:
    with st.sidebar:
        st.header("Filtros")
        alcance = st.selectbox(
            "Cobertura",
            options=["Solo Colombia", "Internacional"],
            key="patentes_scope",
        )

        if alcance == "Solo Colombia":
            scoped_df = df[df["pais"].str.upper() == "CO"].copy()
        else:
            scoped_df = df.copy()
            country_options = sorted(scoped_df["pais"].dropna().unique().tolist())
            selected_countries = st.multiselect(
                "Pais",
                options=country_options,
                key="patentes_countries",
            )
            if selected_countries:
                scoped_df = scoped_df[scoped_df["pais"].isin(selected_countries)]

        regions = sorted(scoped_df["region"].dropna().unique().tolist())
        selected_regions = st.multiselect("Region", options=regions, key="patentes_regions")
        city_options = get_available_cities_patentes(scoped_df, selected_regions)
        selected_cities = st.multiselect("Ciudad", options=city_options, key="patentes_cities")

    filtered_df = apply_filters_patentes(scoped_df, selected_regions, selected_cities)

    if filtered_df.empty:
        st.warning("No hay datos para los filtros seleccionados en Patentes.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros", f"{len(filtered_df):,}")
    col2.metric("Regiones", f"{filtered_df['region'].nunique():,}")
    col3.metric("Ciudades", f"{filtered_df['ciudad'].nunique():,}")
    if alcance == "Internacional":
        col4.metric("Paises", f"{filtered_df['pais'].nunique():,}")
    else:
        col4.metric("Solicitantes unicos", f"{filtered_df['solicitante'].nunique():,}")

    left, right = st.columns(2)
    with left:
        region_counts = (
            filtered_df.groupby("region", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(15)
        )
        fig_region = px.bar(
            region_counts,
            x="region",
            y="size",
            title="Top 15 regiones por numero de patentes",
            labels={"region": "Region", "size": "Cantidad"},
        )
        st.plotly_chart(fig_region, width="stretch")

    with right:
        city_counts = (
            filtered_df.groupby("ciudad", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(15)
        )
        fig_city = px.bar(
            city_counts,
            x="ciudad",
            y="size",
            title="Top 15 ciudades por numero de patentes",
            labels={"ciudad": "Ciudad", "size": "Cantidad"},
        )
        st.plotly_chart(fig_city, width="stretch")

    left2, right2 = st.columns(2)
    with left2:
        yearly = (
            filtered_df.dropna(subset=["anio_concesion"])
            .groupby("anio_concesion", as_index=False)
            .size()
            .sort_values("anio_concesion")
        )
        if yearly.empty:
            st.info("No hay año de concesion valido para la seleccion actual.")
        else:
            yearly["anio_concesion"] = yearly["anio_concesion"].astype(int)
            fig_year = px.line(
                yearly,
                x="anio_concesion",
                y="size",
                markers=True,
                title="Evolucion anual de concesiones",
                labels={"anio_concesion": "Año", "size": "Cantidad"},
            )
            st.plotly_chart(fig_year, width="stretch")

    with right2:
        nat = (
            filtered_df.groupby("naturaleza", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(10)
        )
        fig_nat = px.pie(
            nat,
            values="size",
            names="naturaleza",
            title="Distribucion por naturaleza",
        )
        st.plotly_chart(fig_nat, width="stretch")

    st.subheader("Datos filtrados")
    st.dataframe(filtered_df, width="stretch")


def render_hrhc(df: pd.DataFrame) -> None:
    with st.sidebar:
        st.header("Filtros")
        regions = sorted(df["region"].dropna().unique().tolist())
        selected_regions = st.multiselect("Region", options=regions, key="hrhc_regions")
        city_options = get_available_cities_hrhc(df, selected_regions)
        selected_cities = st.multiselect("Ciudad", options=city_options, key="hrhc_cities")

    filtered_df = apply_filters_hrhc(df, selected_regions, selected_cities)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros", f"{len(filtered_df):,}")
    col2.metric("Regiones", f"{filtered_df['region'].nunique():,}")
    col3.metric("Ciudades", f"{filtered_df['ciudad'].nunique():,}")
    col4.metric("Instituciones", f"{filtered_df['inst_aval'].nunique():,}")

    left, right = st.columns(2)
    with left:
        by_region = (
            filtered_df.groupby("region", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(15)
        )
        fig_region = px.bar(
            by_region,
            x="region",
            y="size",
            title="Top 15 regiones por grupos",
            labels={"region": "Region", "size": "Cantidad"},
        )
        st.plotly_chart(fig_region, width="stretch")

    with right:
        by_city = (
            filtered_df.groupby("ciudad", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(15)
        )
        fig_city = px.bar(
            by_city,
            x="ciudad",
            y="size",
            title="Top 15 ciudades por grupos",
            labels={"ciudad": "Ciudad", "size": "Cantidad"},
        )
        st.plotly_chart(fig_city, width="stretch")

    left2, right2 = st.columns(2)
    with left2:
        by_year = (
            filtered_df.dropna(subset=["anio_creacion_grupo"])
            .groupby("anio_creacion_grupo", as_index=False)
            .size()
            .sort_values("anio_creacion_grupo")
        )
        if by_year.empty:
            st.info("No hay fechas de creacion validas para la seleccion actual.")
        else:
            by_year["anio_creacion_grupo"] = by_year["anio_creacion_grupo"].astype(int)
            fig_year = px.line(
                by_year,
                x="anio_creacion_grupo",
                y="size",
                markers=True,
                title="Evolucion por año de creacion de grupos",
                labels={"anio_creacion_grupo": "Año", "size": "Cantidad"},
            )
            st.plotly_chart(fig_year, width="stretch")

    with right2:
        by_area = (
            filtered_df.groupby("gran_area", as_index=False)
            .size()
            .sort_values("size", ascending=False)
            .head(12)
        )
        fig_area = px.pie(
            by_area,
            values="size",
            names="gran_area",
            title="Distribucion por gran area",
        )
        st.plotly_chart(fig_area, width="stretch")

    st.subheader("Datos filtrados")
    st.dataframe(filtered_df, width="stretch")


VIEW_REGISTRY: Dict[str, ViewConfig] = {
    "Patentes por territorio": ViewConfig(
        key="patentes",
        icon="📄",
        title="Patentes por territorio",
        caption="Patentes por region, ciudad, año y naturaleza (Colombia o internacional).",
        menu_hint="Analiza patentes por ubicacion y tendencia anual",
        session_df_key="df_patentes_co",
        session_cache_key="cache_path_patentes",
        fetch_fn=fetch_patentes_global,
        save_cache_fn=save_temp_cache_patentes,
        render_fn=render_patentes,
    ),
    "Grupos de investigacion": ViewConfig(
        key="hrhc",
        icon="🧪",
        title="Grupos de investigacion - Convocatoria 21",
        caption="Grupos por region, ciudad, año de creacion y gran area.",
        menu_hint="Explora grupos de investigacion por territorio y area",
        session_df_key="df_hrhc",
        session_cache_key="cache_path_hrhc",
        fetch_fn=fetch_hrhc_convocatoria_21,
        save_cache_fn=save_temp_cache_hrhc,
        render_fn=render_hrhc,
    ),
    "Catálogo de datasets": ViewConfig(
        key="catalogo",
        icon="📚",
        title="Catálogo de Datasets",
        caption="Explora y consulta datasets disponibles en datos.gov.co",
        menu_hint="Busca y previsualiza datasets del catálogo",
        session_df_key="df_catalogo",
        session_cache_key="cache_path_catalogo",
        fetch_fn=fetch_catalogue,
        save_cache_fn=save_temp_cache_catalogue,
        render_fn=render_catalogue,
    ),
}


def main() -> None:
    st.set_page_config(page_title="Portal Datos Abiertos Colombia", layout="wide")
    apply_custom_style()  # Se aplicará con el tema correcto
    render_portal_header()

    current_page = render_sidebar_toolbar()
    
    # Re-aplicar estilos después de cambiar tema
    apply_custom_style()
    
    if current_page == "home":
        render_home_page()
        return

    config = get_config_by_key(current_page)
    if config is None:
        render_home_page()
        return

    st.title(config.title)
    st.caption(config.caption)

    df = load_data(config)
    if st.button("Recargar datos de este modulo"):
        df = refresh_data(config)

    if df.empty:
        st.warning("No hay datos para la seleccion actual.")
        return
    config.render_fn(df)


if __name__ == "__main__":
    if get_script_run_ctx is not None and get_script_run_ctx() is not None:
        main()
    else:
        print("Este modulo debe ejecutarse con: streamlit run streamlit_app.py")
