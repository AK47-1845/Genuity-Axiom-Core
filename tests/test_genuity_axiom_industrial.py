import pandas as pd

from genuity_axiom import GenuityAxiomEngine, SynthesisConfig


def test_quality_max_selects_and_reports_candidate_scores():
    df = pd.DataFrame(
        {
            "sample_id": [f"S-{i:04d}" for i in range(120)],
            "material_grade": ["Al", "Ti", "CFRP"] * 40,
            "rpm": [900 + i * 2 for i in range(120)],
            "torque_nm": [140 + (i % 9) * 4 for i in range(120)],
            "nox_ppm": [60 + (i % 13) * 7 for i in range(120)],
            "status": ["Pass"] * 100 + ["Fail"] * 20,
        }
    )

    result = GenuityAxiomEngine().synthesize(
        df,
        config=SynthesisConfig(
            n_samples=160,
            target_col="status",
            quality_mode="max",
        ),
    )

    assert len(result.data) == 160
    assert "sample_id" not in result.data.columns
    assert result.candidate_scores
    assert result.generator_name in result.candidate_scores
    assert result.decision is not None
    assert result.data_card is not None
    assert result.evaluation.membership_attack_score is not None

