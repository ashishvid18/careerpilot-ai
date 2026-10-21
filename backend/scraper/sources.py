
from dataclasses import dataclass


@dataclass(frozen=True)
class JobSource:
    name: str
    base_url: str
    listing_url: str

    job_card_selector: str = ""
    title_selector: str = ""
    company_selector: str = ""
    location_selector: str = ""
    description_selector: str = ""
    job_link_selector: str = ""

    next_page_selector: str = ""
    enabled: bool = False
    notes: str = ""


JOB_SOURCES = [
    JobSource(
        name="Verified Employer Careers",
        base_url="https://example.com",
        listing_url="https://example.com/careers",
        job_card_selector="",
        title_selector="",
        company_selector="",
        location_selector="",
        description_selector="",
        job_link_selector="a",
        next_page_selector="",
        enabled=False,
        notes=(
            "Placeholder only. Replace with a real source "
            "after verifying permission and inspecting its HTML."
        ),
    ),
]


def get_enabled_sources():
    return [
        source
        for source in JOB_SOURCES
        if source.enabled
    ]
