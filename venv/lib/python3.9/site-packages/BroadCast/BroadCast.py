import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pync import Notifier
from validate_email import validate_email


class mail:
    def __init__(self,username,password):
        #login details
        self.username=username
        self.password=password

    def broadcast(self):
        self.Choice = input("Do You Want to enter ids manually ? y/n :\n")
        if self.Choice == 'y':
            self.ids = []
            self.number = int(input("Enter number of receivers :\n"))
            print("Enter Email ids one by one :\n")
            for _ in range(self.number):
                self.id = input()
                if validate_email(self.id) == False:
                    print("Invalid Email address \n")
                self.ids.append(self.id)
            print("Got", self.number, "ids")

            self.parts = MIMEMultipart()
            self.parts['Subject'] = input("Enter subject :\n")
            text = input("Enter message :\n")
            self.parts.attach(MIMEText(text, 'plain'))

            # Trying to Login
            self.server = smtplib.SMTP('smtp.gmail.com', 587)  # 587 or 465
            self.server.starttls()
            try:
                self.server.login(self.username, self.password)
            except Exception:
                print("Check Login details : Incorrect Username or Password ")
                quit()

            self.message = self.parts.as_string()

            for self.to in self.ids:
                self.server.sendmail(self.username,self.to, self.message)
                print("Done sending to " + str(self.to))

            Notifier.notify("Emails Sent ", title="PythonMail")
            self.server.quit()
        else:
            choice=input("So would you like to provide me with a file that contains all receivers ? y/n :\n")
            if choice=='y':
                fname=input("Enter file name(with extension) : \n")
                f= open(str(fname),'r')
                self.li=[]
                for i in f:
                    self.li.append(i.split())
                self.ids=[]
                for i in range(len(self.li)):
                    self.id = str(self.li[i][0])
                    if validate_email(self.id) == False:
                        print("Invalid Email address in your text file \n"+ self.id)
                    else:
                        self.ids.append(self.id)
                print("Got", len(self.ids), "ids")

                self.parts = MIMEMultipart()
                self.parts['Subject'] = input("Enter subject :\n")
                text = input("Enter message :\n")
                self.parts.attach(MIMEText(text, 'plain'))

                # Trying to Login
                self.server = smtplib.SMTP('smtp.gmail.com', 587)  # 587 or 465
                self.server.starttls()
                try:
                    self.server.login(self.username, self.password)
                except Exception:
                    print("Check Login details : Incorrect Username or Password ")
                    quit()

                self.message = self.parts.as_string()

                for self.to in self.ids:
                    self.server.sendmail(self.username, str(self.to), self.message)
                    print("Done sending to " + str(self.to))

                Notifier.notify("Emails Sent ", title="PythonMail")
                self.server.quit()

