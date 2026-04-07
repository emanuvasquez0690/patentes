from dataclasses import dataclass
from typing import Callable, Dict, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

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
    st.markdown(
        """
        <style>
        .hero-card {
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.9rem;
            background: linear-gradient(135deg, #2E4EF2 0%, #6A7BFF 100%);
            color: #ffffff;
        }
        .hero-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }
        .hero-subtitle {
            font-size: 0.95rem;
            opacity: 0.92;
        }
        .selector-card {
            border: 1px solid #E7EAF3;
            border-radius: 14px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.8rem;
            background: linear-gradient(135deg, #f8fbff 0%, #f3f7ff 100%);
        }
        .toolbar-card {
            border: 1px solid #DCE5FF;
            border-radius: 14px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.8rem;
            background: #ffffff;
        }
        .home-card {
            border: 1px solid #E7EAF3;
            border-radius: 12px;
            padding: 0.9rem;
            background: #ffffff;
            min-height: 120px;
            margin-bottom: 0.8rem;
        }
        .selector-caption {
            color: #4b587c;
            font-size: 0.93rem;
            margin-bottom: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_portal_header() -> None:
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

    with st.sidebar:
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
}


def main() -> None:
    st.set_page_config(page_title="Portal Datos Abiertos Colombia", layout="wide")
    apply_custom_style()
    render_portal_header()

    current_page = render_sidebar_toolbar()
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
    main()
