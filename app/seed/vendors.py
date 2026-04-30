from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Vendor

# Curated list of common enterprise software/SaaS vendors. Admins can extend
# this via /admin/vendors at runtime.
VENDORS = [
    {"name": "Microsoft", "website": "https://www.microsoft.com",
     "description": "Office 365, Teams, Azure, Windows, Dynamics 365"},
    {"name": "SAP", "website": "https://www.sap.com",
     "description": "ERP, S/4HANA, SuccessFactors, Ariba"},
    {"name": "Oracle", "website": "https://www.oracle.com",
     "description": "Datenbanken, Cloud Infrastructure, NetSuite"},
    {"name": "Salesforce", "website": "https://www.salesforce.com",
     "description": "CRM, Sales Cloud, Service Cloud"},
    {"name": "Adobe", "website": "https://www.adobe.com",
     "description": "Creative Cloud, Acrobat, Experience Cloud"},
    {"name": "Atlassian", "website": "https://www.atlassian.com",
     "description": "Jira, Confluence, Bitbucket"},
    {"name": "Google", "website": "https://workspace.google.com",
     "description": "Google Workspace, Cloud Platform"},
    {"name": "Amazon Web Services", "website": "https://aws.amazon.com",
     "description": "Cloud Compute, Storage, Datenbanken (AWS)"},
    {"name": "IBM", "website": "https://www.ibm.com",
     "description": "Cloud, Watson, Mainframe"},
    {"name": "Cisco", "website": "https://www.cisco.com",
     "description": "Networking, Webex, Security"},
    {"name": "ServiceNow", "website": "https://www.servicenow.com",
     "description": "ITSM, IT Operations, Workflows"},
    {"name": "Workday", "website": "https://www.workday.com",
     "description": "HCM, Finanzen, Personalmanagement"},
    {"name": "VMware", "website": "https://www.vmware.com",
     "description": "Virtualisierung, vSphere, Tanzu"},
    {"name": "Red Hat", "website": "https://www.redhat.com",
     "description": "Enterprise Linux, OpenShift"},
    {"name": "GitHub", "website": "https://github.com",
     "description": "Source Control, CI/CD, Copilot"},
    {"name": "GitLab", "website": "https://gitlab.com",
     "description": "DevOps Platform, Source Control, CI/CD"},
    {"name": "Citrix", "website": "https://www.citrix.com",
     "description": "Virtual Apps, NetScaler, ShareFile"},
    {"name": "Siemens", "website": "https://www.siemens.com",
     "description": "Industrie-Software, MES, PLM"},
    {"name": "DATEV", "website": "https://www.datev.de",
     "description": "Steuerberatung, Buchhaltung, Personalwirtschaft"},
    {"name": "Sonstiger", "website": None,
     "description": "Sonstiger / nicht aufgeführter Hersteller — bitte unten frei eintragen"},
]


def seed_vendors(session: Session) -> None:
    for data in VENDORS:
        existing = session.query(Vendor).filter(Vendor.name == data["name"]).first()
        if existing:
            # Update description / website on re-seed (don't override is_active)
            existing.description = data.get("description")
            existing.website = data.get("website")
        else:
            session.add(Vendor(**data))
    session.flush()
