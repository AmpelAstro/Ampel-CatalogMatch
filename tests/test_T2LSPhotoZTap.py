from unittest.mock import Mock

import pytest

from ampel.catalogmatch.t2.T2LSPhotoZTap import NamedSecret, T2LSPhotoZTap

CSV = "ra,dec,z_phot_median,z_phot_mean,z_phot_std,z_phot_l68,z_phot_u68,z_spec,dered_mag_g,dered_mag_r,dered_mag_z,dered_mag_w1,dered_mag_w2,dered_mag_w3,dered_mag_w4,snr_g,snr_r,snr_z,snr_w1,snr_w2,snr_w3,snr_w4\n150.0001269198027,1.9977514628901791,0.817497,0.848754,0.344019,0.534578,1.126618,0.4237,24.02235,23.497692,23.029818,22.62755,NaN,18.921059,NaN,6.424314,6.621605,3.833218,1.55841,-0.445872,0.770882,-0.524093\n149.9970157868833,2.000466013202627,0.647819,0.627022,0.146599,0.472521,0.755294,-99,22.979948,22.324043,21.769316,22.477175,21.90846,NaN,NaN,14.184462,19.305738,10.026225,1.773364,1.389925,-1.392426,-1.49257\n"


@pytest.fixture
def t2lsphotoztap(ampel_logger):
    unit = T2LSPhotoZTap(
        datalab_user=NamedSecret(label="datalab_secret", value="fakeuser"),
        datalab_pwd=NamedSecret(label="datalab_secret", value="fakepassword"),
        match_radius=15.0,
        logger=ampel_logger,
    )
    unit.session = Mock(get=Mock(return_value=Mock(ok=True, content=CSV.encode())))
    return unit


def test_match(t2lsphotoztap, snapshot):
    result = t2lsphotoztap.process({"body": {"ra": 150.0, "dec": 2.0}})

    assert snapshot == result
