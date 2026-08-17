import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
load_dotenv()
DB=dict(host=os.getenv("DB_HOST","127.0.0.1"),port=int(os.getenv("DB_PORT","3306")),database=os.getenv("DB_NAME","kjc_portal"),user=os.getenv("DB_USER","root"),password=os.getenv("DB_PASSWORD",""))
c=mysql.connector.connect(**DB); cur=c.cursor()
cur.execute("""INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'ADMIN')
ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash),role='ADMIN'""",("KJC Administrator","admin@kjc.edu.in",generate_password_hash("admin123")))
cur.execute("""INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'STUDENT')
ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash),role='STUDENT'""",("Arun Kumar","student@kjc.edu.in",generate_password_hash("student123")))
c.commit()
cur.execute("SELECT id FROM users WHERE email='student@kjc.edu.in'"); uid=cur.fetchone()[0]
cur.execute("""INSERT INTO students(user_id,student_id,course,semester,phone,address) VALUES(%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE course=VALUES(course),semester=VALUES(semester)""",(uid,"KJC2026BCA001","BCA","Semester 3","9876543210","Bengaluru"))
c.commit(); cur.execute("SELECT id FROM students WHERE user_id=%s",(uid,)); sid=cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id=%s",(sid,))
if cur.fetchone()[0]==0: cur.executemany("INSERT INTO attendance(student_id,subject,attended,total) VALUES(%s,%s,%s,%s)",[(sid,"Web Technology",38,42),(sid,"DBMS",34,40),(sid,"Python Programming",36,40)])
cur.execute("SELECT COUNT(*) FROM marks WHERE student_id=%s",(sid,))
if cur.fetchone()[0]==0: cur.executemany("INSERT INTO marks(student_id,subject,internal,assignment,exam) VALUES(%s,%s,%s,%s,%s)",[(sid,"Web Technology",18,9,62),(sid,"DBMS",17,10,58),(sid,"Python Programming",19,9,64)])
cur.execute("SELECT COUNT(*) FROM assignments WHERE student_id=%s",(sid,))
if cur.fetchone()[0]==0: cur.executemany("INSERT INTO assignments(student_id,title,subject,due_date) VALUES(%s,%s,%s,%s)",[(sid,"Responsive Portfolio Website","Web Technology","2026-08-25"),(sid,"ER Diagram Mini Project","DBMS","2026-08-29"),(sid,"Python Data Analysis","Python Programming","2026-09-03")])
cur.execute("SELECT COUNT(*) FROM timetable")
if cur.fetchone()[0]==0: cur.executemany("INSERT INTO timetable(course,semester,day_name,period_time,subject,room) VALUES(%s,%s,%s,%s,%s,%s)",[("BCA","Semester 3","Monday","09:00 - 10:00","Web Technology","A-203"),("BCA","Semester 3","Monday","10:00 - 11:00","DBMS","A-203"),("BCA","Semester 3","Tuesday","09:00 - 10:00","Python Programming","B-104"),("BCA","Semester 3","Wednesday","11:00 - 12:00","Computer Networks","A-204")])
cur.execute("SELECT COUNT(*) FROM notifications")
if cur.fetchone()[0]==0: cur.execute("INSERT INTO notifications(student_id,title,message) VALUES(NULL,%s,%s)",("Welcome to KJC Portal","Your digital campus dashboard is ready."))
cur.execute("SELECT COUNT(*) FROM fees WHERE student_id=%s",(sid,))
if cur.fetchone()[0]==0: cur.execute("INSERT INTO fees(student_id,semester,amount,paid,due_date) VALUES(%s,%s,%s,%s,%s)",(sid,"Semester 3",65000,50000,"2026-09-15"))
cur.execute("SELECT COUNT(*) FROM certificates WHERE student_id=%s",(sid,))
if cur.fetchone()[0]==0: cur.execute("INSERT INTO certificates(student_id,title,issued_on,certificate_no) VALUES(%s,%s,%s,%s)",(sid,"Hackathon Participation","2026-07-18","KJC-HACK-2026-001"))
c.commit(); cur.close(); c.close()
print("Seed complete: student@kjc.edu.in / student123 | admin@kjc.edu.in / admin123")
