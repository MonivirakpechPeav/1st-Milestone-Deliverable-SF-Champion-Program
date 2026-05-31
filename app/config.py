"""Shared constants for the Data Governance Agent."""

PII_CATEGORIES = {
    "Email":         r"e[\._]?mail",
    "Phone":         r"phone|mobile|cell|fax",
    "SSN / SIN":     r"ssn|social[\._]?sec|sin\b",
    "Date of Birth": r"\bdob\b|birth[\._]?date|date[\._]?birth|birthdate",
    "Address":       r"\baddress\b|street|postal|zip[\._]?code",
    "Payment Card":  r"credit[\._]?card|card[\._]?num|cvv\b|ccn\b|\bpan\b",
    "Government ID": r"passport|drivers?[\._]?lic|nat[\._]?id|national[\._]?id",
    "IP Address":    r"\bip[\._]?addr",
    "Financial":     r"salary|income|wage|compensation",
    "Bank Account":  r"account[\._]?num|bank[\._]?acct|routing|iban|swift",
    "Tax ID":        r"\btin\b|\bein\b|tax[\._]?id",
    "Health":        r"diagnos|medical[\._]?rec|patient[\._]?id|health[\._]?id|prescription",
}

PRIVILEGED_ROLES = ("ACCOUNTADMIN", "SECURITYADMIN", "SYSADMIN", "ORGADMIN")

HISTORY_SCHEMA = "GOVERNANCE_AGENT"
HISTORY_TABLE  = "SCAN_HISTORY"

GRADE_BANDS = [
    (90, "A", "#2ecc71"),
    (75, "B", "#3498db"),
    (60, "C", "#f39c12"),
    (40, "D", "#e67e22"),
    (0,  "F", "#e74c3c"),
]
