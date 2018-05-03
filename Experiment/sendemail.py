# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText

def sendemail(to,mfrom,subject,body):
    # me == the sender's email address
    # you == the recipient's email address
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mfrom
    msg['To'] = to

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP('cs.stanford.edu')
    s.sendmail(to, [mfrom], msg.as_string())
    s.quit()

if __name__ == "__main__":
    sendemail('bst@stanford.edu','bst@stanford.edu','test subject','test body')
