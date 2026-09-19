"""Explicit mappings inspected against official IRS, ACS and IATI specifications."""

import csv
import io
import json
import re
import time
from datetime import date, datetime

from .common import (
    MAX_ROWS,
    ImportProblem,
    archive_entries,
    deadline_check,
    decimal_string,
    envelope,
    finish,
    issue,
    size_check,
    xml_root,
)

IRS_NS = "http://www.irs.gov/efile"
VERSIONS = {2022: "2022v5.0", 2023: "2023v5.1", 2024: "2024v5.0"}
IRS_FIELDS = {
    "990": {
        "revenue": "CYTotalRevenueAmt",
        "expenses": "CYTotalExpensesAmt",
        "assets": "TotalAssetsEOYAmt",
        "liabilities": "TotalLiabilitiesEOYAmt",
        "net_assets": "NetAssetsOrFundBalancesEOYAmt",
        "program_expenses": "TotalFunctionalExpensesGrp/ProgramServicesAmt",
        "functional_total": "TotalFunctionalExpensesGrp/TotalAmt",
        "cash_noninterest": "CashNonInterestBearingGrp/EOYAmt",
        "savings_temporary_investments": "SavingsAndTempCashInvstGrp/EOYAmt",
        "net_assets_without_donor_restriction": "NoDonorRestrictionNetAssetsGrp/EOYAmt",
    },
    "990EZ": {
        "revenue": "TotalRevenueAmt",
        "expenses": "TotalExpensesAmt",
        "assets": "Form990TotalAssetsGrp/EOYAmt",
        "liabilities": "SumOfTotalLiabilitiesGrp/EOYAmt",
        "net_assets": "NetAssetsOrFundBalancesEOYAmt",
        "program_expenses": "TotalProgramServiceExpensesAmt",
    },
    "990PF": {
        "revenue": "AnalysisOfRevenueAndExpenses/TotalRevAndExpnssAmt",
        "expenses": "AnalysisOfRevenueAndExpenses/TotalExpensesRevAndExpnssAmt",
        "charitable_disbursements": "AnalysisOfRevenueAndExpenses/TotalExpensesDsbrsChrtblAmt",
        "assets": "Form990PFBalanceSheetsGrp/TotalAssetsEOYAmt",
        "liabilities": "Form990PFBalanceSheetsGrp/TotalLiabilitiesEOYAmt",
        "net_assets": "Form990PFBalanceSheetsGrp/TotNetAstOrFundBalancesEOYAmt",
        "assets_fair_market": "Form990PFBalanceSheetsGrp/TotalAssetsEOYFMVAmt",
    },
}


def _ein(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{9}", value):
        raise ImportProblem("invalid_ein", "EIN must be a nine-character digit string.")
    return value


def _date(value, fmt=None):
    if not value:
        return None
    try:
        return (
            datetime.strptime(value, fmt).date() if fmt else date.fromisoformat(value)
        ).isoformat()
    except (TypeError, ValueError) as exc:
        raise ImportProblem("invalid_date", "Source contains an invalid reporting date.") from exc


def _text(node, path, ns=""):
    found = node.find("/".join(f"{{{ns}}}{part}" if ns else part for part in path.split("/")))
    return found.text.strip() if found is not None and found.text else None


def _xml_irs(payload, result, metadata):
    root = xml_root(payload)
    if root.tag != f"{{{IRS_NS}}}Return":
        raise ImportProblem(
            "unsupported_namespace", "Expected an IRS e-file Return with its official namespace."
        )
    header = root.find(f"{{{IRS_NS}}}ReturnHeader")
    data = root.find(f"{{{IRS_NS}}}ReturnData")
    if header is None or data is None:
        raise ImportProblem("missing_header", "IRS ReturnHeader and ReturnData are required.")
    year_raw = _text(header, "TaxYr", IRS_NS)
    year = int(year_raw) if year_raw and year_raw.isdigit() else None
    if year not in VERSIONS:
        raise ImportProblem(
            "unsupported_tax_year", "Inspected mappings support tax years 2022, 2023 and 2024."
        )
    version = root.get("returnVersion")
    if version != VERSIONS[year]:
        raise ImportProblem(
            "unsupported_schema_version",
            "Return version has not been verified against the supported mapping.",
        )
    form = _text(header, "ReturnTypeCd", IRS_NS)
    if form not in IRS_FIELDS:
        raise ImportProblem(
            "unsupported_form",
            "Supported XML forms are 990, 990EZ and 990PF; 990N uses a separate adapter.",
        )
    bodies = [child for child in data if child.tag in {f"{{{IRS_NS}}}IRS{k}" for k in IRS_FIELDS}]
    if len(bodies) != 1 or bodies[0].tag != f"{{{IRS_NS}}}IRS{form}":
        raise ImportProblem("form_mismatch", "The return body disagrees with the declared form.")
    body = bodies[0]
    ein = _ein(_text(header, "Filer/EIN", IRS_NS))
    begin = _date(_text(header, "TaxPeriodBeginDt", IRS_NS))
    end = _date(_text(header, "TaxPeriodEndDt", IRS_NS))
    if not begin or not end or begin > end:
        raise ImportProblem("invalid_period", "An ordered tax reporting period is required.")
    amended = _text(body, "AmendedReturnInd", IRS_NS)
    if amended not in {None, "X"}:
        raise ImportProblem("invalid_amendment", "Unexpected IRS amendment checkbox value.")
    record = {
        "kind": "foundation_filing" if form == "990PF" else "nonprofit_filing",
        "external_id": f"irs:{ein}:{begin}:{end}:{result['checksum']}",
        "ein": ein,
        "name": _text(header, "Filer/BusinessName/BusinessNameLine1Txt", IRS_NS),
        "tax_year": year,
        "form": form,
        "schema_version": version,
        "period_start": begin,
        "period_end": end,
        "amended": amended == "X",
        "currency": "USD",
        "unit": "dollars",
        "active_revision": False,
        "filing_address_zip": _text(header, "Filer/USAddress/ZIPCd", IRS_NS),
        "service_area": None,
        "locators": {},
    }
    for name, path in IRS_FIELDS[form].items():
        record[name] = decimal_string(_text(body, path, IRS_NS))
        record["locators"][name] = f"/Return/ReturnData/IRS{form}/{path}"
        if record[name] is None:
            issue(
                result,
                "unavailable_field",
                "The filing does not report this field.",
                field=name,
                severity="warning",
            )
    record["program_descriptions"] = []
    if form == "990":
        first_description = _text(body, "Desc", IRS_NS)
        if first_description:
            record["program_descriptions"].append(
                {"text": first_description, "locator": "/Return/ReturnData/IRS990/Desc"}
            )
        for group in (
            "ProgSrvcAccomActy2Grp",
            "ProgSrvcAccomActy3Grp",
            "ProgSrvcAccomActyOtherGrp",
        ):
            for index, node in enumerate(body.findall(f"{{{IRS_NS}}}{group}"), 1):
                description = _text(node, "Desc", IRS_NS)
                if description:
                    record["program_descriptions"].append(
                        {
                            "text": description,
                            "locator": f"/Return/ReturnData/IRS990/{group}[{index}]/Desc",
                        }
                    )
    if form == "990":
        mission = _text(body, "MissionDesc", IRS_NS)
        record["mission"] = mission
    result["records"].append(record)
    issue(
        result,
        "revision_selection_required",
        "Persist this revision and explicitly select the active revision; amendments do not overwrite originals.",
        severity="warning",
    )


def _csv_rows(payload, required):
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
            raise ImportProblem(
                "unsupported_columns", "Required official source columns are missing."
            )
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ImportProblem("duplicate_column", "Source column names must be unique.")
        for number, row in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise ImportProblem("row_limit", "Filter the local source to at most 5,000 rows.")
            if None in row or any(value is None for value in row.values()):
                raise ImportProblem("column_count", "Source row width disagrees with its header.")
            yield number, row
    except (csv.Error, UnicodeDecodeError) as exc:
        raise ImportProblem("invalid_csv", "Source must be well-formed UTF-8 CSV.") from exc


def _index(payload, result, metadata):
    required = [
        "RETURN_ID",
        "FILING_TYPE",
        "EIN",
        "TAX_PERIOD",
        "SUB_DATE",
        "TAXPAYER_NAME",
        "RETURN_TYPE",
        "DLN",
        "OBJECT_ID",
    ]
    filters = metadata.get("filter_eins", [])
    for number, row in _csv_rows(payload, required):
        ein = _ein(row["EIN"])
        if filters and ein not in filters:
            continue
        period = row["TAX_PERIOD"]
        if not re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", period):
            raise ImportProblem("invalid_period", "Index TAX_PERIOD must be YYYYMM.")
        result["records"].append(
            {
                "kind": "filing_index",
                "external_id": row["OBJECT_ID"],
                "ein": ein,
                "name": row["TAXPAYER_NAME"],
                "tax_period": period,
                "submission_raw": row["SUB_DATE"],
                "form": row["RETURN_TYPE"],
                "return_id": row["RETURN_ID"],
                "filing_type": row["FILING_TYPE"],
                "dln": row["DLN"],
                "locator": f"row:{number}",
                "download_url": None,
            }
        )


def _bmf(payload, result, metadata):
    required = ["EIN", "NAME", "ZIP", "STATUS", "TAX_PERIOD", "NTEE_CD"]
    for number, row in _csv_rows(payload, required):
        result["records"].append(
            {
                "kind": "eo_bmf_snapshot",
                "external_id": _ein(row["EIN"]),
                "ein": row["EIN"],
                "name": row["NAME"],
                "filing_address_zip": row["ZIP"],
                "status_code": row["STATUS"],
                "tax_period": row["TAX_PERIOD"] or None,
                "ntee_code": row["NTEE_CD"] or None,
                "subsection": row.get("SUBSECTION"),
                "deductibility_code": row.get("DEDUCTIBILITY"),
                "service_area": None,
                "current_status_certified": False,
                "locator": f"row:{number}",
            }
        )


def _pipes(payload, count):
    try:
        for number, row in enumerate(
            csv.reader(io.StringIO(payload.decode("utf-8-sig")), delimiter="|"), 1
        ):
            if number > MAX_ROWS:
                raise ImportProblem("row_limit", "Filter the source to at most 5,000 rows.")
            if len(row) == count + 1 and row[-1] == "":
                row.pop()
            if len(row) != count:
                raise ImportProblem(
                    "column_count", "Pipe-delimited source does not match the official layout."
                )
            yield number, row
    except (csv.Error, UnicodeDecodeError) as exc:
        raise ImportProblem("invalid_text", "The pipe-delimited source is malformed.") from exc


def _notice(payload, result, metadata):
    for number, row in _pipes(payload, 26):
        if row[3] != "T" or row[4] not in {"T", "F"}:
            raise ImportProblem("invalid_notice", "Invalid gross-receipts or termination flag.")
        result["records"].append(
            {
                "kind": "filing_notice",
                "external_id": f"irs990n:{_ein(row[0])}:{row[1]}",
                "ein": row[0],
                "tax_year": int(row[1]),
                "name": row[2],
                "form": "990N",
                "gross_receipts_threshold_confirmed": True,
                "terminated": row[4] == "T",
                "period_start": _date(row[5], "%m-%d-%Y"),
                "period_end": _date(row[6], "%m-%d-%Y"),
                "revenue": None,
                "expenses": None,
                "locator": f"row:{number}",
            }
        )


def _revocations(payload, result, metadata):
    for number, row in _pipes(payload, 12):
        revoked = _date(row[9], "%m/%d/%Y")
        effective = "2020-07-15" if revoked and "2020-04-01" <= revoked <= "2020-07-14" else revoked
        result["records"].append(
            {
                "kind": "revocation_event",
                "external_id": f"revocation:{_ein(row[0])}:{revoked}",
                "ein": row[0],
                "name": row[1],
                "subsection": row[8],
                "revocation_date_raw": revoked,
                "revocation_effective_date": effective,
                "posting_date": _date(row[10], "%m/%d/%Y"),
                "reinstatement_date": _date(row[11], "%m/%d/%Y"),
                "insolvency_inferred": False,
                "locator": f"row:{number}",
            }
        )


def _acs(payload, result, metadata):
    year = metadata.get("snapshot_year")
    geo_type = metadata.get("geography_type")
    geo_columns = {
        "state": ["state"],
        "county": ["state", "county"],
        "tract": ["state", "county", "tract"],
        "zcta": ["zip code tabulation area"],
    }
    if year != 2023 or geo_type not in geo_columns:
        raise ImportProblem(
            "unsupported_acs_configuration",
            "Verified ACS5 mapping is 2023; use state, county, tract or zcta geography.",
        )
    table = json.loads(payload)
    if not isinstance(table, list) or len(table) < 2 or len(table) > MAX_ROWS + 1:
        raise ImportProblem("invalid_acs", "Expected a bounded Census API array with a header.")
    columns = table[0]
    expected = ["B17001_001E", "B17001_001M", "B17001_002E", "B17001_002M"]
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise ImportProblem("invalid_acs", "Invalid Census API header.")
    if len(columns) != len(set(columns)) or not set(expected + geo_columns[geo_type]).issubset(
        columns
    ):
        raise ImportProblem(
            "invalid_acs", "Census variables or exact geography identifiers are missing."
        )
    for number, values in enumerate(table[1:], 2):
        if not isinstance(values, list) or len(values) != len(columns):
            raise ImportProblem("invalid_acs", "Census row width disagrees with its header.")
        row = dict(zip(columns, values, strict=True))
        geography = {key: row[key] for key in geo_columns[geo_type]}
        if any(not isinstance(value, str) or not value.isdigit() for value in geography.values()):
            raise ImportProblem(
                "invalid_geography", "Census geography codes must remain digit strings."
            )
        record = {
            "kind": "community_context",
            "external_id": f"acs5:{year}:{geo_type}:{':'.join(geography.values())}",
            "dataset": "acs/acs5",
            "snapshot_year": year,
            "period_start": "2019-01-01",
            "period_end": "2023-12-31",
            "geography_type": geo_type,
            "geography": geography,
            "boundary_vintage": metadata.get("boundary_vintage"),
            "crosswalk_vintage": metadata.get("crosswalk_vintage"),
            "universe": "Population for whom poverty status is determined",
            "unit": "people",
            "measure": "poverty_status",
            "food_insecurity_measure": False,
            "variables": {},
            "locator": f"row:{number}",
        }
        for variable in expected:
            value = decimal_string(row[variable])
            annotation = row.get(variable + "A")
            missing = value is None or value.startswith("-") or bool(annotation)
            record["variables"][variable] = {
                "value": None if missing else value,
                "raw": row[variable],
                "annotation": annotation,
                "locator": f"row:{number}/{variable}",
            }
        record["estimate"] = record["variables"]["B17001_002E"]["value"]
        record["margin_of_error"] = record["variables"]["B17001_002M"]["value"]
        record["denominator"] = record["variables"]["B17001_001E"]["value"]
        record["denominator_margin_of_error"] = record["variables"]["B17001_001M"]["value"]
        result["records"].append(record)


def _narratives(node, path):
    return [
        {"text": n.text.strip(), "language": n.get("{http://www.w3.org/XML/1998/namespace}lang")}
        for n in node.findall(path)
        if n.text and n.text.strip()
    ]


def _iati(payload, result, metadata):
    root = xml_root(payload)
    if root.tag != "iati-activities" or root.get("version") != "2.03":
        raise ImportProblem("unsupported_iati", "Only IATI 2.03 activity documents are supported.")
    for i, activity in enumerate(root.findall("iati-activity"), 1):
        if i > MAX_ROWS:
            raise ImportProblem("row_limit", "Too many activities.")
        identity = _text(activity, "iati-identifier")
        reporting = activity.find("reporting-org")
        if not identity or reporting is None or not reporting.get("ref"):
            raise ImportProblem(
                "missing_iati_identity",
                "Activity identifier and reporting organization reference are required.",
            )
        locator = f"/iati-activities/iati-activity[{i}]"
        record = {
            "kind": "iati_activity",
            "external_id": identity,
            "reporting_org": reporting.get("ref"),
            "title": _narratives(activity, "title/narrative"),
            "description": _narratives(activity, "description/narrative"),
            "organizations": [
                {
                    "ref": n.get("ref"),
                    "role": n.get("role"),
                    "type": n.get("type"),
                    "names": _narratives(n, "narrative"),
                }
                for n in activity.findall("participating-org")
            ],
            "countries": [dict(n.attrib) for n in activity.findall("recipient-country")],
            "sectors": [dict(n.attrib) for n in activity.findall("sector")],
            "documents": [
                {
                    "url": n.get("url"),
                    "format": n.get("format"),
                    "title": _narratives(n, "title/narrative"),
                }
                for n in activity.findall("document-link")
            ],
            "budgets": [],
            "transactions": [],
            "planned_disbursements": [],
            "results": [],
            "locator": locator,
            "evidence_status": "source_reported_unreviewed",
        }
        for tag, key in [
            ("budget", "budgets"),
            ("transaction", "transactions"),
            ("planned-disbursement", "planned_disbursements"),
        ]:
            transaction_refs = set()
            for j, node in enumerate(activity.findall(tag), 1):
                if tag == "transaction" and node.get("ref"):
                    if node.get("ref") in transaction_refs:
                        raise ImportProblem(
                            "duplicate_transaction",
                            "Duplicate transaction references require source correction.",
                        )
                    transaction_refs.add(node.get("ref"))
                value = node.find("value")
                if value is None:
                    raise ImportProblem(
                        "missing_iati_value", "Financial entries require a value element."
                    )
                entry = {
                    "amount": decimal_string(value.text),
                    "currency": value.get("currency", activity.get("default-currency")),
                    "value_date": _date(value.get("value-date")),
                    "type": node.get("type"),
                    "ref": node.get("ref"),
                    "locator": f"{locator}/{tag}[{j}]",
                }
                for child, field in [
                    ("transaction-type", "transaction_type"),
                    ("transaction-date", "transaction_date"),
                    ("period-start", "period_start"),
                    ("period-end", "period_end"),
                ]:
                    child_node = node.find(child)
                    entry[field] = (
                        None
                        if child_node is None
                        else child_node.get("code", child_node.get("iso-date"))
                    )
                record[key].append(entry)
        for j, result_node in enumerate(activity.findall("result"), 1):
            for k, indicator in enumerate(result_node.findall("indicator"), 1):
                periods = []
                for period in indicator.findall("period"):
                    start = period.find("period-start")
                    end = period.find("period-end")
                    periods.append(
                        {
                            "period_start": None if start is None else _date(start.get("iso-date")),
                            "period_end": None if end is None else _date(end.get("iso-date")),
                            "targets": [
                                {
                                    **dict(n.attrib),
                                    "dimensions": [dict(d.attrib) for d in n.findall("dimension")],
                                    "locations": [dict(d.attrib) for d in n.findall("location")],
                                }
                                for n in period.findall("target")
                            ],
                            "actuals": [
                                {
                                    **dict(n.attrib),
                                    "dimensions": [dict(d.attrib) for d in n.findall("dimension")],
                                    "locations": [dict(d.attrib) for d in n.findall("location")],
                                }
                                for n in period.findall("actual")
                            ],
                        }
                    )
                baseline = indicator.find("baseline")
                record["results"].append(
                    {
                        "result_type": result_node.get("type"),
                        "measure": indicator.get("measure"),
                        "ascending": indicator.get("ascending"),
                        "title": _narratives(indicator, "title/narrative"),
                        "baseline": None if baseline is None else dict(baseline.attrib),
                        "periods": periods,
                        "locator": f"{locator}/result[{j}]/indicator[{k}]",
                    }
                )
        result["records"].append(record)


ADAPTERS = {
    "irs_xml": _xml_irs,
    "irs_index": _index,
    "eo_bmf": _bmf,
    "form990n": _notice,
    "revocations": _revocations,
    "acs5": _acs,
    "iati": _iati,
}


def parse_source(payload: bytes, adapter: str, metadata: dict | None = None) -> dict:
    result = envelope(payload, adapter)
    metadata = metadata or {}
    start = time.monotonic()
    try:
        size_check(payload)
        if adapter not in ADAPTERS:
            raise ImportProblem("unsupported_adapter", "This source adapter is not implemented.")
        ADAPTERS[adapter](payload, result, metadata)
        deadline_check(start)
        seen = set()
        unique = []
        for record in result["records"]:
            if record["external_id"] in seen:
                issue(
                    result,
                    "duplicate_record",
                    "Duplicate external record omitted.",
                    severity="warning",
                )
                continue
            seen.add(record["external_id"])
            record["source"] = {
                "source_kind": metadata.get("source_kind", "ngo_contributed"),
                "source_url": metadata.get("source_url"),
                "upload_id": metadata.get("upload_id"),
                "retrieved_at": metadata.get("retrieved_at"),
                "checksum": result["checksum"],
                "parser_version": result["parser_version"],
                "transformations": ["explicit schema normalization"],
            }
            if metadata.get("archive_member"):
                record["source"]["archive_member"] = metadata["archive_member"]
            if record["source"]["source_kind"] not in {
                "public_source",
                "ngo_contributed",
                "synthetic_demo",
            }:
                raise ImportProblem("source_kind", "Unsupported source classification.")
            unique.append(record)
        result["records"] = unique
        if not unique:
            issue(
                result,
                "empty_source",
                "The source contained no supported records.",
                severity="warning",
            )
        result["preview"] = unique[:10]
    except (ImportProblem, ValueError, TypeError, KeyError) as exc:
        # A malformed public-source document is rejected atomically.
        result["records"] = []
        result["preview"] = []
        issue(
            result,
            getattr(exc, "code", "malformed_source"),
            str(exc)
            if isinstance(exc, ImportProblem)
            else "The source does not match its supported schema.",
        )
    return finish(result)


def parse_archive(payload: bytes, adapter: str, metadata: dict | None = None) -> list[dict]:
    entries = archive_entries(payload)
    return [
        parse_source(content, adapter, {**(metadata or {}), "archive_member": name})
        for name, content in entries.items()
        if not name.endswith("/")
    ]
