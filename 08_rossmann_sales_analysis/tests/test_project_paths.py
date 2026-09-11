import importlib.util
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    module_path = PROJECT_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_pipeline = _load_module("rossmann_run_pipeline", "run_pipeline.py")
check_results = _load_module("rossmann_check_results", "check_results.py")
get_master_csv_path = check_results.get_master_csv_path


def test_project_root_resolves_notebook_and_output_paths():
    project_dir = PROJECT_DIR
    assert project_dir.name == "08_rossmann_sales_analysis"
    assert (project_dir / "rossmann_sales_analysis.ipynb").is_file()

    notebook = run_pipeline.get_notebook_path()
    output_dir = run_pipeline.get_output_dir()

    assert notebook.name == "rossmann_sales_analysis.ipynb"
    assert notebook.parent == project_dir
    assert output_dir.parent == project_dir


def test_check_results_uses_project_relative_output_path():
    csv_path = get_master_csv_path()
    assert csv_path.parent.name == "output"
    assert csv_path.name == "rossmann_master_tableau.csv"
