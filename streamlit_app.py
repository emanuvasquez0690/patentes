from patentes.visualizador_unificado import main

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover
    get_script_run_ctx = None


def _running_under_streamlit() -> bool:
    return get_script_run_ctx is not None and get_script_run_ctx() is not None


if __name__ == "__main__":
    if _running_under_streamlit():
        main()
    else:
        print("Este proyecto debe ejecutarse con: streamlit run streamlit_app.py")

