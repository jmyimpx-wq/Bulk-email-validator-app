import streamlit as st
import pandas as pd
import re
import dns.resolver
import smtplib
import socket

# ------------------------------
# Email Validation Helpers
# ------------------------------

DISPOSABLE_DOMAINS = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "yopmail.com"}
ROLE_PREFIXES = {"admin", "info", "sales", "support", "contact", "help", "office"}

def validate_regex(email: str) -> bool:
    regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(regex, email) is not None

def validate_disposable(email: str) -> bool:
    domain = email.split('@')[-1]
    return domain.lower() in DISPOSABLE_DOMAINS

def validate_role_based(email: str) -> bool:
    prefix = email.split('@')[0].split('.')[0].lower()
    return prefix in ROLE_PREFIXES

def validate_mx(domain: str) -> bool:
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except:
        return False

def check_catch_all(domain: str) -> bool:
    test_email = "thisaddressshouldnotexist123@" + domain
    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail("test@" + domain)
        code, _ = server.rcpt(test_email)
        server.quit()
        return code == 250
    except:
        return False

def validate_smtp(email: str) -> bool:
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail("test@" + domain)
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except:
        return False

def classify_email(email: str, use_smtp: bool = False) -> str:
    if not validate_regex(email):
        return "Invalid"

    domain = email.split('@')[-1]

    if not validate_mx(domain):
        return "Invalid"

    if validate_disposable(email):
        return "Doubtful"

    if validate_role_based(email):
        return "Doubtful"

    if check_catch_all(domain):
        return "Doubtful"

    if use_smtp and not validate_smtp(email):
        return "Doubtful"

    return "Valid"


# ------------------------------
# Streamlit App
# ------------------------------
st.title("📧 Advanced Bulk Email Validator (NeverBounce Style)")

uploaded_file = st.file_uploader("Upload Excel/CSV with Emails", type=["xlsx", "csv"])
use_smtp = st.checkbox("Enable SMTP validation (slower, less reliable)")

if uploaded_file:
    # Load data
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    email_col = st.selectbox("Select Email Column", df.columns)

    results = []
    total = len(df)

    progress = st.progress(0)
    status_text = st.empty()

    for i, email in enumerate(df[email_col]):
        if isinstance(email, str) and "@" in email:
            result = classify_email(email.strip(), use_smtp)
        else:
            result = "Invalid"

        results.append(result)

        pct = int(((i + 1) / total) * 100)
        progress.progress(pct)
        status_text.text(f"Processing {i+1}/{total} emails... ({pct}%)")

    df["Validation Result"] = results

    st.success("✅ Validation completed!")
    st.dataframe(df.head(20))

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Results CSV", csv, "validated_emails.csv", "text/csv")
