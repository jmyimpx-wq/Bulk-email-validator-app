import streamlit as st
import re
import dns.resolver
import smtplib
import socket
import pandas as pd

# -------------------
# Validation Functions
# -------------------

def validate_regex(email: str) -> bool:
    regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(regex, email) is not None

def check_mx(email: str) -> bool:
    try:
        domain = email.split("@")[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except:
        return False

def check_smtp(email: str) -> bool:
    try:
        domain = email.split("@")[1]
        records = dns.resolver.resolve(domain, "MX")
        mx_record = str(records[0].exchange)
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail("test@example.com")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except:
        return False

def classify_email(regex_ok, mx_ok, smtp_ok):
    if regex_ok and mx_ok and smtp_ok:
        return "✅ Valid"
    elif regex_ok or mx_ok or smtp_ok:
        return "⚠️ Doubtful"
    else:
        return "❌ Invalid"

# -------------------
# Streamlit App
# -------------------

st.title("📧 Email Validator App")
st.write("Validate emails with Regex, MX record, and SMTP checks.")

# --- Single Email Check ---
st.subheader("Single Email Validation")
email = st.text_input("Enter email to validate:")

if st.button("Validate Email"):
    if email:
        regex_ok = validate_regex(email)
        mx_ok = check_mx(email) if regex_ok else False
        smtp_ok = check_smtp(email) if mx_ok else False
        status = classify_email(regex_ok, mx_ok, smtp_ok)

        st.write("### Validation Results:")
        st.write(f"Regex Check: {regex_ok}")
        st.write(f"MX Record Found: {mx_ok}")
        st.write(f"SMTP Deliverable: {smtp_ok}")
        st.write(f"**Final Status: {status}**")
    else:
        st.warning("Please enter an email.")

# --- Bulk Upload ---
st.subheader("Bulk Email Validation")
uploaded_file = st.file_uploader("Upload CSV or Excel with an `email` column", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if "email" not in df.columns:
        st.error("No 'email' column found! Please include an 'email' column in your file.")
    else:
        results = []
        for mail in df["email"]:
            regex_ok = validate_regex(mail)
            mx_ok = check_mx(mail) if regex_ok else False
            smtp_ok = check_smtp(mail) if mx_ok else False
            status = classify_email(regex_ok, mx_ok, smtp_ok)
            results.append([mail, regex_ok, mx_ok, smtp_ok, status])

        result_df = pd.DataFrame(results, columns=["Email", "Regex Check", "MX Record", "SMTP Deliverable", "Final Status"])

        st.success("Validation completed!")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="validated_emails.csv",
            mime="text/csv",
        )
