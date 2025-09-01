import streamlit as st
import pandas as pd
import re
import dns.resolver
import smtplib
import socket

# -----------------------------
# Email validation functions
# -----------------------------

def validate_regex(email):
    """Check if email matches regex pattern."""
    regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    if not isinstance(email, str):
        return False
    return re.match(regex, email.strip()) is not None

def validate_mx(email):
    """Check if domain has MX record."""
    try:
        domain = email.split('@')[-1]
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False

def validate_smtp(email):
    """Check if SMTP server accepts the email (basic check)."""
    try:
        domain = email.split('@')[-1]
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail("test@example.com")
        code, _ = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False

# -----------------------------
# Streamlit App
# -----------------------------

st.title("📧 Bulk Email Validator")
st.write("Upload an Excel/CSV file containing emails. The app will validate each email in 3 steps: Regex ➝ MX Record ➝ SMTP.")

uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Assume column name is 'email' (case insensitive)
        email_col = None
        for col in df.columns:
            if col.lower() in ["email", "emails", "mail", "e-mail"]:
                email_col = col
                break

        if email_col is None:
            st.error("❌ No 'email' column found in file. Please rename your column to 'email'.")
        else:
            df['email'] = df[email_col].astype(str).str.strip()

            results = []
            progress = st.progress(0)
            status_text = st.empty()

            total = len(df)
            for i, mail in enumerate(df['email']):
                mail = str(mail).strip()

                regex_ok = validate_regex(mail)
                mx_ok = validate_mx(mail) if regex_ok else False
                smtp_ok = validate_smtp(mail) if mx_ok else False

                if regex_ok and mx_ok and smtp_ok:
                    status = "✅ Valid"
                elif regex_ok or mx_ok:
                    status = "⚠ Doubtful"
                else:
                    status = "❌ Invalid"

                results.append({"email": mail, "status": status})

                # Update progress bar
                percent_complete = int(((i+1) / total) * 100)
                progress.progress((i+1) / total)
                status_text.text(f"Processing... {percent_complete}%")

            # Convert to dataframe
            result_df = pd.DataFrame(results)
            st.success("✅ Validation Completed!")

            st.dataframe(result_df)

            # Download button
            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Results as CSV",
                data=csv,
                file_name="email_validation_results.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
