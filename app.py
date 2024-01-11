from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
db = SQLAlchemy(app)

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger('attendance_app')

class users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_ = db.Column(db.String(255))
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store the hashed password
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendance_marked_logs = db.relationship('AttendanceLog', backref='marked_by_user')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class departments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_by = db.relationship('User', backref='submitted_departments')

class courses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cource_name = db.Column(db.String(255))
    # department = db.relationship('Department', backref='courses')
    semester = db.Column(db.Integer)  # Example: '1'
    class_name = db.Column(db.String(50))  # Example: 'cs103'
    lecture_hours = db.Column(db.Integer)  # Number of lecture hours
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_by = db.relationship('User', backref='submitted_courses')

class student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    department = db.relationship('Department', backref='students')
    class_name = db.Column(db.String(50))  # Store the course class name here
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_by = db.relationship('User', backref='submitted_students')
    # Establish a one-to-many relationship with the AttendanceLog table based on student_id
    attendance_logs = db.relationship('AttendanceLog', backref='student', lazy='dynamic')
    submitted_by = db.relationship('User', backref='submitted_students')

class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    student = db.relationship('Student', backref='attendance_logs')
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship('Course', backref='attendance_logs')
    present = db.Column(db.Boolean)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)    
    marked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    marked_by = db.relationship('User', backref='attendance_marked_logs')
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_by = db.relationship('User', backref='submitted_attendance_logs')

def generate_random_password(length=12):
    """Generate a random password."""
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# Create the initial user if it doesn't exist
with app.app_context():
    db.create_all()
    initial_user = User.query.filter_by(username='admin').first()
    if not initial_user:
        password = generate_random_password()
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        initial_user = User(username='admin', email='admin@example.com', password_hash=hashed_password)
        db.session.add(initial_user)
        db.session.commit()
        logger.info(f'Initial user "admin" created with password: {password}')


@app.route('/attendance', methods=['POST'])
def create_attendance():
    try:
        data = request.json
        student_id = data.get('student_id')
        date = data.get('updated_at')
        present = data.get('present')

        attendance = AttendanceLog(student_id=student_id, date=date, present=True)
        db.session.add(attendance)
        db.session.commit()
        logger.info(f'Attendance record created for student_id={student_id} on date={date}')
        return jsonify({'message': 'Attendance record created successfully'})
    except Exception as e:
        logger.error(f'Error creating attendance record: {str(e)}')
        return jsonify({'message': 'Error creating attendance record'}), 500

@app.route('/attendance/<int:id>', methods=['GET'])
def get_attendance(id):
    try:
        attendance = AttendanceLog.query.get(id)
        if attendance:
            logger.info(f'Retrieved attendance record with id={id}')
            return jsonify({
                'id': attendance.id,
                'student_id': attendance.student_id,
                'updated_at': attendance.date.strftime('%Y-%m-%d'),
                'present': attendance.present
            })
        logger.warning(f'Attendance record with id={id} not found')
        return jsonify({'message': 'Attendance record not found'}), 404
    except Exception as e:
        logger.error(f'Error retrieving attendance record: {str(e)}')
        return jsonify({'message': 'Error retrieving attendance record'}), 500

@app.route('/attendance/<int:id>', methods=['PUT'])
def update_attendance(id):
    try:
        attendance = AttendanceLog.query.get(id)
        if not attendance:
            logger.warning(f'Attendance record with id={id} not found')
            return jsonify({'message': 'Attendance record not found'}), 404

        data = request.json
        attendance.present = data.get('present')
        db.session.commit()
        logger.info(f'Attendance record with id={id} updated successfully')
        return jsonify({'message': 'Attendance record updated successfully'})
    except Exception as e:
        logger.error(f'Error updating attendance record: {str(e)}')
        return jsonify({'message': 'Error updating attendance record'}), 500

if __name__ == '__main__':
    app.run(debug=True)