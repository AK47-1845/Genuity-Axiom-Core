import pandas as pd
import importlib
from pathlib import Path
import sys

from genuity_axiom import EngineeringConstraintSet, GenuityAxiomEngine


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
pramana = importlib.import_module("pramana")


def test_pramana_generates_constraint_compliant_material_data():
    assert pramana.GenuityAxiomEngine is GenuityAxiomEngine
    assert pramana.__version__
    real = pd.DataFrame(
        {
            "sample_id": [f"S-{i:03d}" for i in range(60)],
            "material": ["aluminum", "titanium", "cfrp"] * 20,
            "tensile_strength_mpa": [500 + (i % 9) * 15 for i in range(60)],
            "yield_strength_mpa": [430 + (i % 9) * 12 for i in range(60)],
            "density_gcc": [2.7, 4.4, 1.6] * 20,
            "pass_fail": ["Pass"] * 54 + ["Fail"] * 6,
        }
    )
    constraints = (
        EngineeringConstraintSet()
        .add_bound("tensile_strength_mpa", min_value=0)
        .add_bound("yield_strength_mpa", min_value=0)
        .add_comparison("yield_strength_mpa", "le", "tensile_strength_mpa")
    )

    result = GenuityAxiomEngine().synthesize(
        real,
        n_samples=120,
        target_col="pass_fail",
        constraints=constraints,
    )

    assert len(result.data) == 120
    assert "sample_id" not in result.data.columns
    assert result.constraints.passed
    assert result.evaluation.overall_score >= 0.0
    assert result.generator_name in {
        "gmm",
        "kde",
        "gaussian_copula",
        "stratified_bootstrap",
        "bootstrap",
    }
