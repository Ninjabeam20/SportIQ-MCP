from pathlib import Path


def test_public_docs_do_not_claim_zero_telemetry_or_host_secrets():
    readme = Path("README.md").read_text()
    security = Path("SECURITY.md").read_text()
    forbidden = ("No data collection.", "zero API keys", "all 44 tools work out of the box")
    assert all(claim not in readme for claim in forbidden)
    assert "zero API keys" not in security


def test_security_docs_do_not_advertise_unenforced_output_limits():
    security = Path("SECURITY.md").read_text()
    assert "Tools cap list payloads at 200 items" not in security
    assert "no application-level MCP request-size limit" in security


def test_security_reporting_discourages_public_disclosure():
    security = Path("SECURITY.md").read_text()
    assert "Do not open a public issue" in security
