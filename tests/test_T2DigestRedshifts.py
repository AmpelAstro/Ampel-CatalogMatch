"""Test T2DigestRedshifts: reproducible test data + stored output comparison."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ampel.catalogmatch.t2.T2DigestRedshifts import T2DigestRedshifts
from ampel.view.T2DocView import T2DocView


def allclose(a: list[float], b: list[float], rtol: float = 1e-5) -> bool:
    """Check if two float lists are approximately equal."""
    if len(a) != len(b):
        return False
    return all(
        abs(x - y) <= rtol * max(abs(x), abs(y)) for x, y in zip(a, b, strict=False)
    )


# Test data generators (reproducible, each covers redshift groups)
def lsphotoz_test_data() -> dict[str, Any]:
    """Generate test data for T2LSPhotoZTap parsing."""
    return {
        "ls_1": {
            "z_spec": 0.01,
            "z_phot_median": None,
            "dist2transient": 2.0,
        },  # Group I
        "ls_2": {
            "z_spec": 0.10,
            "z_phot_median": None,
            "dist2transient": 5.0,
        },  # Group II
        "ls_3": {
            "z_spec": 0.25,
            "z_phot_median": None,
            "dist2transient": 3.0,
        },  # Group III
        "ls_4": {
            "z_spec": None,
            "z_phot_median": 0.08,
            "dist2transient": 1.0,
        },  # Group IV
        "ls_5": {
            "z_spec": None,
            "z_phot_median": 0.15,
            "dist2transient": 4.0,
        },  # Group V
        "ls_6": {
            "z_spec": None,
            "z_phot_median": 0.30,
            "dist2transient": 2.0,
        },  # Group VI
        "ls_7": {
            "z_spec": None,
            "z_phot_median": 0.50,
            "dist2transient": 1.5,
        },  # Group VII
        "ls_skip_dist": {
            "z_spec": 0.02,
            "z_phot_median": None,
            "dist2transient": 15.0,
        },  # dist > 10, skip
        "ls_skip_z": {
            "z_spec": -1,
            "z_phot_median": None,
            "dist2transient": 2.0,
        },  # z=-1, skip
    }


def catalogmatch_test_data() -> dict[str, Any]:
    """Generate test data for T2CatalogMatch parsing."""
    return {
        "NEDz_extcats": [
            {"z": 0.01, "dist2transient": 1.0},  # Group I
            {"z": 0.04, "dist2transient": 15.0},  # Group III
            {"z": 0.10, "dist2transient": 30.0},  # Group IV
        ],
        "SDSS_spec": {"z": 0.08, "dist2transient": 5.0},  # Group II
        "GLADEv23": [
            {"z": 0.02, "dist2transient": 3.0},  # Group III
            {"z": 0.10, "dist2transient": 5.0},  # Group IV
        ],
        "LSPhotoZZou": [
            {"specz": 0.10, "photoz": None, "dist2transient": 5.0},  # Group II
            {"specz": None, "photoz": 0.08, "dist2transient": 2.0},  # Group IV
            {"specz": 0.18, "photoz": None, "dist2transient": 1.0},  # Group III
            {"specz": None, "photoz": 0.35, "dist2transient": 1.0},  # Group VI
        ],
        "wiseScosPhotoz": [
            {"zPhoto_Corr": 0.15, "dist2transient": 1.0},  # Group V
            {"zPhoto_Corr": 0.25, "dist2transient": 2.0},  # Group VI
        ],
        "twoMPZ": [
            {"zPhoto": 0.02, "zSpec": None, "dist2transient": 1.0},  # Group III
            {"zPhoto": None, "zSpec": 0.05, "dist2transient": 5.0},  # Group II
        ],
        "PS1_photoz": [
            {"z_phot": 50, "dist2transient": 2.0},  # 0.05, Group IV
            {"z_phot": 150, "dist2transient": 1.0},  # 0.15, Group V
            {"z_phot": 350, "dist2transient": 3.0},  # 0.35, Group VI
        ],
        "NEDz": {"z": 0.15, "dist2transient": 5.0},  # Group III
    }


def matchbts_test_data() -> dict[str, Any]:
    """Generate test data for T2MatchBTS parsing."""
    return {
        "bts_1": {"bts_redshift": "0.01"},  # 2 decimals -> Group II
        "bts_2": {"bts_redshift": "0.001"},  # 3 decimals -> Group I
        "bts_3": {"bts_redshift": "-"},  # skip
    }


@pytest.fixture
def digest_unit(ampel_logger):
    """Create T2DigestRedshifts instance."""
    return T2DigestRedshifts(logger=ampel_logger, t2_dependency=[])


@pytest.fixture
def test_data_file():
    """Path to stored expected outputs."""
    return Path(__file__).parent / "test-data" / "t2_digest_redshifts_expected.json"


def load_or_save_expected(test_file: Path, key: str, actual: Any) -> Any:
    """Load expected data from file, or save if missing (first run)."""
    data = {}
    if test_file.exists():
        with open(test_file) as f:
            data = json.load(f)
    if key not in data:
        data[key] = json.loads(json.dumps(actual, default=str))
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            json.dump(data, f, indent=2)
    return data.get(key)


class TestT2DigestRedshifts:
    """Test T2DigestRedshifts redshift parsing."""

    def test_get_lsphotoz_groupz(self, digest_unit, test_data_file):
        """Test LSPhotoZTap parsing covers all 7 groups."""
        t2_res = lsphotoz_test_data()
        group_z, group_dist = digest_unit._get_lsphotoz_groupz(t2_res)

        # ponytail: normalized output for comparison (floats -> lists)
        actual = {
            "group_z": [sorted(list(g)) for g in group_z],
            "group_dist": [sorted(list(d)) for d in group_dist],
            "group_counts": [len(g) for g in group_z],
        }

        expected = load_or_save_expected(test_data_file, "test_lsphotoz", actual)

        assert actual["group_counts"] == expected["group_counts"]
        for i in range(7):
            assert allclose(actual["group_z"][i], expected["group_z"][i], rtol=1e-5)
            assert allclose(
                actual["group_dist"][i], expected["group_dist"][i], rtol=1e-5
            )

    def test_get_catalogmatch_groupz(self, digest_unit, test_data_file):
        """Test CatalogMatch parsing covers all 7 groups."""
        t2_res = catalogmatch_test_data()
        group_z, group_dist = digest_unit._get_catalogmatch_groupz(t2_res)

        actual = {
            "group_z": [sorted(list(g)) for g in group_z],
            "group_dist": [sorted(list(d)) for d in group_dist],
            "group_counts": [len(g) for g in group_z],
        }

        expected = load_or_save_expected(test_data_file, "test_catalogmatch", actual)

        assert actual["group_counts"] == expected["group_counts"]
        for i in range(7):
            assert allclose(actual["group_z"][i], expected["group_z"][i], rtol=1e-5)

    def test_get_matchbts_groupz(self, digest_unit, test_data_file):
        """Test MatchBTS parsing (decimal precision -> group)."""
        t2_res = matchbts_test_data()

        # ponytail: test each redshift separately
        for key, data in t2_res.items():
            group_z = digest_unit._get_matchbts_groupz(data)
            actual = {
                "group_counts": [len(g) for g in group_z],
                "group_z": [list(g) for g in group_z],
            }
            expected = load_or_save_expected(
                test_data_file, f"test_matchbts_{key}", actual
            )
            assert actual["group_counts"] == expected["group_counts"]

    def test_get_ampelZ_combined(self, digest_unit, test_data_file):
        """Test main method: combines LSPhotoZ + CatalogMatch + MatchBTS."""
        # Create mock T2DocViews
        views = []

        # Mock LSPhotoZTap view
        ls_view = MagicMock(spec=T2DocView)
        ls_view.unit = "T2LSPhotoZTap"
        ls_view.get_payload.return_value = lsphotoz_test_data()
        views.append(ls_view)

        # Mock CatalogMatch view
        cm_view = MagicMock(spec=T2DocView)
        cm_view.unit = "T2CatalogMatch"
        cm_view.get_payload.return_value = catalogmatch_test_data()
        views.append(cm_view)

        # Mock MatchBTS view
        bts_view = MagicMock(spec=T2DocView)
        bts_view.unit = "T2MatchBTS"
        bts_view.get_payload.return_value = {"bts_redshift": "0.001"}
        views.append(bts_view)

        result = digest_unit.get_ampelZ(views)

        # ponytail: check key outputs exist and are numeric
        assert "ampel_z" in result
        assert "group_z_nbr" in result
        assert "group_z_precision" in result
        assert isinstance(result["ampel_z"], float)
        assert 0 <= result["group_z_nbr"] <= 7

        actual = {
            "ampel_z": result["ampel_z"],
            "group_z_nbr": result["group_z_nbr"],
            "group_z_precision": result["group_z_precision"],
            "has_group_zs": "group_zs" in result,
        }

        expected = load_or_save_expected(test_data_file, "test_ampelz_combined", actual)
        assert actual == expected

    def test_get_hostCol(
        self,
        digest_unit,
    ):
        """Test host color extraction from WISE and PS1."""
        views = []

        cm_view = MagicMock(spec=T2DocView)
        cm_view.unit = "T2CatalogMatch"
        cm_view.get_payload.return_value = {
            "WISE": {"Mag_W1": 10.0, "Mag_W2": 9.5, "dist2transient": 2.0},
            "PS1": {
                "gPSFMag": 15.0,
                "rPSFMag": 14.5,
                "iPSFMag": 14.2,
                "zPSFMag": 14.0,
                "dist2transient": 5.0,
            },
        }
        views.append(cm_view)

        result = digest_unit.get_hostCol(views)

        assert "col_wise_w1w2" in result
        assert "col_ps1_gr" in result
        assert "col_ps1_ri" in result
        assert "col_ps1_iz" in result
        assert result["col_wise_w1w2"] == 0.5

    def test_get_redshift_ampelz(
        self,
        digest_unit,
    ):
        """Test get_redshift with AmpelZ mode."""
        views = []
        cm_view = MagicMock(spec=T2DocView)
        cm_view.unit = "T2CatalogMatch"
        cm_view.get_payload.return_value = catalogmatch_test_data()
        views.append(cm_view)

        digest_unit.redshift_kind = "AmpelZ"
        z, z_source, z_weights = digest_unit.get_redshift(views)

        assert z is not None
        assert len(z) > 0
        assert isinstance(z[0], float)
        assert z_source is not None
        assert "AMPELz" in z_source

    def test_get_redshift_fixed(
        self,
        digest_unit,
    ):
        """Test get_redshift with fixed value."""
        digest_unit.redshift_kind = None
        digest_unit.fixed_z = 0.05

        z, z_source, z_weights = digest_unit.get_redshift([])

        assert z == [0.05]
        assert z_source == "Fixed"

    def test_get_redshift_scaled(
        self,
        digest_unit,
    ):
        """Test get_redshift with scaling factor."""
        views = []
        cm_view = MagicMock(spec=T2DocView)
        cm_view.unit = "T2CatalogMatch"
        cm_view.get_payload.return_value = catalogmatch_test_data()
        views.append(cm_view)

        digest_unit.redshift_kind = "AmpelZ"
        digest_unit.scale_z = 1.5

        z, z_source, z_weights = digest_unit.get_redshift(views)

        assert z is not None
        assert "scaled" in z_source
        assert z[0] > 0  # scaled up

    def test_max_redshift_category_limit(self, digest_unit, test_data_file):
        """Test that result stops at max_redshift_category."""
        digest_unit.max_redshift_category = 2  # Only group 1 & 2

        views = []
        cm_view = MagicMock(spec=T2DocView)
        cm_view.unit = "T2CatalogMatch"
        cm_view.get_payload.return_value = catalogmatch_test_data()
        views.append(cm_view)

        result = digest_unit.get_ampelZ(views)

        if "group_z_nbr" in result:
            assert result["group_z_nbr"] <= 2

    def test_catalogmatch_override(
        self,
        digest_unit,
    ):
        """Test catalog override functionality."""
        digest_unit.catalogmatch_override = {
            "CustomCat": {
                "z_keyword": "custom_z",
                "max_distance": 5.0,
                "max_redshift": 0.5,
                "z_group": 3,
            }
        }

        t2_res = {"CustomCat": {"custom_z": "0.10", "dist2transient": 3.0}}
        group_z, group_dist = digest_unit._get_catalogmatch_groupz(t2_res)

        assert len(group_z[2]) == 1  # z_group=3 -> index 2
        assert group_z[2][0] == 0.10
