#!/usr/bin/env python
# File              : Ampel-CatalogMatch/ampel/catalogmatch/t2/T2LSPhotoZTap.py
# License           : BSD-3-Clause
# Author            : jnordin
# Date              : 20.04.2021
# Last Modified Date: 21.04.2021
# Last Modified By  : jnordin

import csv
import math
from collections.abc import Sequence
from functools import cached_property
from io import StringIO
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from ampel.abstract.AbsPointT2Unit import AbsPointT2Unit
from ampel.content.DataPoint import DataPoint
from ampel.enum.DocumentCode import DocumentCode
from ampel.secret.NamedSecret import NamedSecret
from ampel.struct.UnitResult import UnitResult
from ampel.types import UBson

from ..base.CatalogMatchUnit import retry_transient_errors
from ..util.coordinates import angular_separation


def convert(datum: str) -> bool | int | float | str:
    """
    Convert a string to a bool, int, float or str.
    """
    if datum.lower() in ("true", "false"):
        return datum.lower() == "true"
    try:
        return int(datum)
    except ValueError:
        pass
    try:
        return float(datum)
    except ValueError:
        pass
    return datum


# adapted from datalab dl/helpers/util/convert
def parse_csv(inp: str) -> Sequence[dict[str, bool | int | float | str]]:
    # When there are duplicate column names in the table, it would not work when converting to Astropy Table and Votable, so we
    # have to add '_n' as an identifier to the duplicate column names.
    lines = StringIO(inp)
    try:
        header = next(lines)
    except StopIteration:
        return []
    col_dict: dict[str, int] = {}
    for field in header.strip().split(","):
        if field in col_dict:
            col_dict[field] += 1
        else:
            col_dict[field] = 1

    reader = csv.DictReader(
        lines,
        fieldnames=[
            field if count == 1 else f"{field}_{count}"
            for field, count in col_dict.items()
        ],
    )
    return [{k: convert(v) for k, v in row.items()} for row in reader]


class T2LSPhotoZTap(AbsPointT2Unit):
    """
    Query the NOIR DataLab service for photometric redshifts from the
    Legacy Survey.

    Other queries can in principle be made as long as the string format parameters are the same (ra, dec, match_radius).

    """

    # Astro DataLab user id
    datalab_user: NamedSecret[str]
    datalab_pwd: NamedSecret[str]

    # Match parameters
    match_radius: float = 10  # in arcsec

    # Query. Candidate position and radius will be added
    query: str = "SELECT ra, dec, photo_z.z_phot_median, photo_z.z_phot_mean, photo_z.z_phot_std, photo_z.z_phot_l68, z_phot_u68, photo_z.z_spec, tractor.dered_mag_g, tractor.dered_mag_r, tractor.dered_mag_z, tractor.dered_mag_w1, tractor.dered_mag_w2 , tractor.dered_mag_w3, tractor.dered_mag_w4, tractor.snr_g, tractor.snr_r, tractor.snr_z, tractor.snr_w1, tractor.snr_w2, tractor.snr_w3, tractor.snr_w4 FROM ls_dr9.tractor as tractor JOIN ls_dr9.photo_z as photo_z on photo_z.ls_id = tractor.ls_id WHERE 't' = Q3C_RADIAL_QUERY(ra, dec,%.6f,%.6f,%.6f)"

    # run only on first datapoint by default
    # NB: this assumes that docs are created by DualPointT2Ingester
    ingest: dict = {"eligible": {"pps": "first"}}

    # Path to noir queries
    datalab_query_url: str = "https://datalab.noirlab.edu/query"

    @cached_property
    def session(self) -> requests.Session:
        """Obtain a session with an auth token"""
        session = requests.Session()
        parts = urlparse(self.datalab_query_url)
        response = session.get(
            urlunparse((parts.scheme, parts.netloc, "/auth/login", "", "", "")),
            params={
                "username": self.datalab_user.get(),
                "profile": "default",
                "debug": "False",
            },
            headers={"X-DL-Password": self.datalab_pwd.get()},
        )
        response.raise_for_status()
        session.headers.update({"X-DL-AuthToken": response.text})
        return session

    @retry_transient_errors()
    def _astrolab_query(self, ra: float, dec: float) -> Sequence[dict[str, Any]]:
        self.logger.debug(f"Querying {ra} {dec}")

        r = self.session.get(
            f"{self.datalab_query_url}/query",
            params={
                "sql": self.query % (ra, dec, self.match_radius / 3600),
                "ofmt": "csv",
                "async": "False",
            },
            timeout=300,
        )
        if not r.ok:
            self.logger.debug(f"DL query failed at {ra} {dec}")
            return []

        # First convert to string and then to dict
        ret_dict = parse_csv(str(r.content.decode()))

        self.logger.debug(f"Got {len(ret_dict)} matches")

        return ret_dict

    def add_separation(
        self, match_dict: Sequence[dict[str, Any]], target_ra: float, target_dec: float
    ) -> Sequence[dict[str, Any]]:
        """
        Iterate through catalog entries (dict) and add separation to target.
        """
        c = math.pi / 180

        for el in match_dict:
            if "dec" in el and "ra" in el:
                el["dist2transient"] = angular_separation(
                    target_ra * c, target_dec * c, el["ra"] * c, el["dec"] * c
                ) * (3600 / c)  # to arcsecs
            else:
                el["dist2transient"] = None

        return match_dict

    def process(self, datapoint: DataPoint) -> UBson | UnitResult:
        return_all: bool = (
            False  # whether to return all matches or closest match (default)
        )
        """
        Query DataLab through the unit query string combined with 
        transient position. 

        :returns: 
        {
        0:  {'ra': 247.033806830109,
             'dec': 63.8236957439316,
             'z_phot_median': 0.364699,
             'z_phot_mean': 0.640077,
             'z_phot_l68': 0.14177,
             'z_phot_u68': 1.30389,
             'z_spec': -99,
             ...,
             'dist2transient': 0.30846301868050724},
        1:  { ... },
        }


        Note that, when a match is found, the distance of the lightcurve object
        to the match counterpart is also returned as the 'dist2transient' key.
        """

        try:
            transient_ra = datapoint["body"]["ra"]
            transient_dec = datapoint["body"]["dec"]
        except KeyError:
            ##return T2RunState.MISSING_INFO
            return UnitResult(code=DocumentCode.T2_MISSING_INFO)

        # Query Datalab
        match_list = self._astrolab_query(transient_ra, transient_dec)

        # Add separation between target and query detection
        if len(match_list) > 0:
            match_list = self.add_separation(match_list, transient_ra, transient_dec)

        # Return a T2 result (dict-like)
        if len(match_list) > 0:
            if return_all:
                return {f"T2LSPhotoZTap{k}": item for k, item in enumerate(match_list)}
            min_dist = min(match_list, key=lambda x: x["dist2transient"])
            return {"T2LSPhotoZTap": min_dist}
        return {"T2LSPhotoZTap": None}
