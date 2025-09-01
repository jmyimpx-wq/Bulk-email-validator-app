import streamlit as st
import pandas as pd
import re
import dns.resolver
import smtplib
import socket
from concurrent.futures import ThreadPoolExecutor

# ----------------------------
# Utility functions
# ----------------------------

DISPOSABLE_DOMAINS = {
    "tempmail.com", "guerrillamail.com", "10minutemail.com", "mailinator.com"
}

ROLE_BASED_PREFIXES = {
    "admin", "support", "info", "sales", "contact", "office"
}

COMMON_TYPO_DOMAINS = {
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com",
}


def is_valid_syntax(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def check_dns_mx(domain: str) -> bool:
    try:
        records = dns.resolver.resolve(domain, "MX")
        return len(records) > 0
    except Exception:
        return False


def is_disposable(domain: str) -> bool:
    return domain.lower() in DISPOSABLE_DOMAINS


def is_role_based(email: str) -> bool:
    prefix = email.split("@")[0].lower()
    return prefix in ROLE_BASED_PREFIXES


def suggest_domain_fix(domain: str) -> str:
    return COMMON_TYPO_DOMAINS.get(domain.lower(), domain)


def smtp_check(email: str) -> bool:
    try:
        domain = email.split("@")[1]
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_record = str(mx_records[0].exchange)
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail("test@example.com")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False


def validate_email(email: str, smtp_enabled=False) -> dict:
    score = 0
    reasons = []

    # Syntax
    if is_valid_syntax(email):
        score += 20
    else:
        reasons.append("Invalid syntax")
        return {"email": email, "status": "Invalid", "score": score, "reason": ", ".join(reasons)}

    local, domain = email.split("@")

    # Typo correction
    fixed_domain = suggest_domain_fix(domain)
    if fixed_domain != domain:
        reasons.append(f"Domain corrected: {domain} → {fixed_domain}")
        domain = fixed_domain
        email = f"{local}@{domain}"

    # DNS check
    if check_dns_mx(domain):
        score += 25
    else:
        reasons.append("No MX record")

    # Disposable check
    if is_disposable(domain):
        reasons.append("Disposable domain")
        score -= 20

    # Role-based
    if is_role_based(email):
        reasons.append("Role-based address")
        score -= 10

    # SMTP check
    if smtp_enabled:
        if smtp_check(email):
            score += 25
        else:
            reasons.append("SMTP failed")
            score -= 15

    # Final classification
    if score >= 80:
        status = "Valid"
    elif 40 <= score < 80:
        status = "Doubtful"
    else:
        status = "Invalid"

    return {"email": email, "status": status, "score": score, "reason": ", ".join(reasons)}


# ----------------------------
# Streamlit App
# ----------------------------

st.set_page_config(page_title="Advanced Bulk Email Validator", page_icon="📧", layout="wide")
st.title("📧 Advanced Bulk Email Validator (NeverBounce Style)")

uploaded_file = st.file_uploader("Upload Excel/CSV with Emails", type=["csv", "xlsx"])
smtp_enabled = st.checkbox("Enable SMTP validation (slower, less reliable)")

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if "email" not in df.columns:
        st.error("Your file must have a column named 'email'")
    else:
        emails = df["email"].dropna().unique().tolist()
        results = []

        progress = st.progress(0)
        status_text = st.empty()

        with ThreadPoolExecutor(max_workers=10) as executor:
            for i, result in enumerate(executor.map(lambda e: validate_email(e, smtp_enabled), emails)):
                results.append(result)
                progress.progress((i + 1) / len(emails))
                status_text.text(f"Processing {i+1}/{len(emails)} emails...")

        result_df = pd.DataFrame(results)
        st.success("Validation complete ✅")
        st.dataframe(result_df)

        # Download button
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Results CSV", csv, "validated_emails.csv", "text/csv")
