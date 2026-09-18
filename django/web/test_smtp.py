import smtplib

def test_smtp_connection():
    try:
        server = smtplib.SMTP('smtp-relay.brevo.com', 587)
        server.ehlo()
        server.starttls()
        server.login('sadhikali0867@gmail.com', 'NdcSyY40fFtQEIHU')
        print("SMTP connection successful")
        server.quit()
    except Exception as e:
        print(f"SMTP connection error: {e}")

if __name__ == "__main__":
    test_smtp_connection()

