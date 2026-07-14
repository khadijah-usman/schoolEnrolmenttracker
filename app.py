from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admissions.db'
app.config['SECRET_KEY'] = 'admissions-secret-key-2025'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# ── Passcodes (change these before deploying) ──────────────
ADMIN_PASSCODE   = 'admin2025'
UNIFORM_PASSCODE = 'uniform2025'

db = SQLAlchemy(app)

# ═══════════════════════════════════════════════════════════
#  PIPELINE CONFIG
# ═══════════════════════════════════════════════════════════

STAGES = [
    'Enquiry',
    'Tour Scheduled',
    'Application Pack Purchased',
    'Application Submitted',
    'Assessment/Interview Invitation',
    'Admission Pack Issued',
    'Payment of Fees',
    'Documents Returned',
    'Welcome Pack / Enrolled',
    'Rejected',
    'Withdrawn',
]

STAGE_COLORS = {
    'Enquiry':                         'secondary',
    'Tour Scheduled':                  'info',
    'Application Pack Purchased':      'info',
    'Application Submitted':           'primary',
    'Assessment/Interview Invitation': 'warning',
    'Admission Pack Issued':           'success',
    'Payment of Fees':                 'success',
    'Documents Returned':              'success',
    'Welcome Pack / Enrolled':         'dark',
    'Rejected':                        'danger',
    'Withdrawn':                       'secondary',
}

STAGE_CHECKLIST = {
    'Enquiry': [
        'Enquiry form completed',
    ],
    'Tour Scheduled': [
        'Tour appointment booked',
        'Tour completed',
    ],
    'Application Pack Purchased': [
        'Application form issued',
        'Prospectus issued',
    ],
    'Application Submitted': [
        'Application form',
        '2 passport photographs',
        'Birth certificate / Declaration of age',
        'National Identification Number (NIN)',
        'Immunization card',
        'International passport data page',
        'Previous school transcript and recommendation letter (transfer students only)',
    ],
    'Assessment/Interview Invitation': [
        'Invitation letter with assessment details',
        'Assessment completed',
        'Assessment details / decision',
        'Space allocated within 48 hours',
    ],
    'Admission Pack Issued': [
        'Admission letter / resumption date',
        'Fee schedule',
        'Bank details',
        'Uniform list',
        'Meal form',
        'Club list',
        'Bus shuttle service fee (optional and subject to availability)',
        'Acceptance form',
    ],
    'Payment of Fees': [
        'Payment of fees confirmed',
    ],
    'Documents Returned': [
        'Proof of tuition fee payment',
        'Meal form returned',
        'Club form returned',
        'Acceptance form returned',
    ],
    'Welcome Pack / Enrolled': [
        'Class assigned',
        'Student handbook issued',
        'House assigned',
        'Club assigned',
        'Pickup card issued',
        'Bus service manual (if subscribed)',
    ],
    'Rejected': [],
    'Withdrawn': [],
}

ACTIVE_STAGES = [s for s in STAGES if s not in ('Rejected', 'Withdrawn')]

ACADEMIC_YEARS = ['2023/2024', '2024/2025', '2025/2026', '2026/2027', '2027/2028']

STAGE_SOFT = {
    'Enquiry':                         ('#f1f5f9', '#475569'),
    'Tour Scheduled':                  ('#e0f2fe', '#0369a1'),
    'Application Pack Purchased':      ('#e0f2fe', '#0369a1'),
    'Application Submitted':           ('#ede9fe', '#5b21b6'),
    'Assessment/Interview Invitation': ('#fef3c7', '#92400e'),
    'Admission Pack Issued':           ('#cffafe', '#155e75'),
    'Payment of Fees':                 ('#dcfce7', '#166534'),
    'Documents Returned':              ('#dcfce7', '#14532d'),
    'Welcome Pack / Enrolled':         ('#bbf7d0', '#14532d'),
    'Rejected':                        ('#fee2e2', '#7f1d1d'),
    'Withdrawn':                       ('#f1f5f9', '#475569'),
}

STAGE_HEX = {
    'Enquiry':                         '#94a3b8',
    'Tour Scheduled':                  '#0ea5e9',
    'Application Pack Purchased':      '#06b6d4',
    'Application Submitted':           '#6366f1',
    'Assessment/Interview Invitation': '#f59e0b',
    'Admission Pack Issued':           '#14b8a6',
    'Payment of Fees':                 '#10b981',
    'Documents Returned':              '#22c55e',
    'Welcome Pack / Enrolled':         '#0f172a',
    'Rejected':                        '#ef4444',
    'Withdrawn':                       '#64748b',
}

# ── Classes & capacity ─────────────────────────────────────
CLASS_MAX = 25

CLASSES_LIST = [
    'Nursery 1', 'Nursery 2', 'Nursery 3',
    'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5', 'Year 6',
    'Year 7', 'Year 8', 'Year 9', 'Year 10', 'Year 11', 'Year 12',
]

# Existing students already enrolled (before this admissions system)
EXISTING_STUDENTS = {
    'Nursery 1':  4,
    'Nursery 2':  9,
    'Nursery 3': 13,
    'Year 1':    12,
    'Year 2':    20,
    'Year 3':    12,
    'Year 4':    17,
    'Year 5':    18,
    'Year 6':    17,
    'Year 7':    20,
    'Year 8':    19,
    'Year 9':    24,
    'Year 10':   18,
    'Year 11':   13,
    'Year 12':   16,
}

# Existing students to seed into the uniform system
EXISTING_UNIFORM_STUDENTS = {
    'Nursery 1': [
        'AYYANAN UMAR FAROUK', 'AISHA HANAN MUHAMMAD', 'FATIMA ALIYU', 'BILAL UMAR',
    ],
    'Nursery 2': [
        'HAJARA IBRAHIM MOHAMMED', 'MANAF HAMZA GALADIMA', 'AISHA FAISAL UMAR',
        'IDRIS FAROUQ IDRIS', 'ALQASIM MUHAMMAD SULAIMAN', 'UMMU SALAMA NOOR ABDULLAHI',
        'KAHDIJA ISMAIL ABDULAZEEZ', 'IREDUMARE EBUNMARE KHALID', 'BUHARI YUSUF',
    ],
    'Nursery 3': [
        'FARUK SAIFULLA FARUK', 'AISHA YAKUBU SHEHU', 'MARYAM AMINU BAKIN KASUWA',
        'AFNAN HAMZA GALADIMA', 'MARYAM ABDULAZEEZ ISMAIL', 'FATIMA MUHAMMAD SULAIMAN',
        'FATIMAH ZARAH IBRAHIM', 'AMEL KARIM AMADOU', 'AMATULLAH HAMISU YADUDU',
        'FATIMA IDRIS SALEH', 'HAUWAU BAMODU YERIMA', 'ANAS RAFIU OLAWUYI', 'NAFIU YUSUF',
    ],
    'Year 1': [
        'AISHA AHMAD ZAYD', 'AHMAD AHMAD ZAYD', 'HARUNA IBRAHIM BABA', 'BUHARI USMAN MAGAJI',
        'SALMA ABDULKADIR RAHIS', 'RUQAYYA AMAL IBRAHIM', 'AISHA MAS\'UD IBRAHIM',
        'ZAINAB ABDULAZEEZ ISMAIL', 'UMAR ABDULRAHMAN', 'AISHA DILLI ALIYU',
        'HAUWAU USMAN DANMUSA', 'KAREEMA FAROUK IDRIS',
    ],
    'Year 2': [
        'MUSTAPHA IBRAHIM SHETTIMA', 'AMINA MODIBBO', 'MARYAM USMAN MAGAJI',
        'MOHAMMED MURITALA ABIODUN AYINDE', 'ABDALLAH TIJJANI MUHAMMAD',
        'ABDULKADIR AMINU BAKIN KASUWA', 'KHADIJA ALI BUBA', 'ABIHAN UMAR FARUK',
        'SAADATU JAFARU RIBADU', 'NURIYYA UMAR FARUK', 'FAISAL SANUSI UMAR',
        'KHADIJA SURAJ ABDULLAHI', 'ISMAIL HAMISU YADUDU', 'KHADIJA KAURE ALI',
        'ZAIN YUSSUF OLUWABOGTOMI', 'HANANE KARIM AMADOU', 'IDRIS SAIDU HARUNA',
        'ASMAU SIDDIQ MUSA', 'MUHAMMAD BAMODU YERIMA', 'USMAN SHUAIBU',
    ],
    'Year 3': [
        'AMINA IBRAHIM BABA', 'MUHAMMAD JAMILU UMAR', 'YASMIN ABDULMUMIN SADIQ',
        'USMAN IDRIS SALEH', 'YASIRA ISHAQ', 'KASHIM GONI ABATCHA',
        'NANA FATIMA ZAHRA MUHAMMAD HUSSEINI', 'MUHAMMAD ABDULLAHI GERIE',
        'MARYAM AMNA HAMIDU', 'RAHMA ISAH ABBAS', 'AFIYAH RAFIU OLAWUYI',
        'ASHRAF MUHAMMAD DANTORO',
    ],
    'Year 4': [
        'HAJARA DANJUMA NOOR', 'FATIMA IBRAHIM SHETTIMA', 'AHMAD MODIBBO',
        'UMMU ABIHA UMAR FAROUK', 'MUS\'AB UMAR FAROUK', 'MUSTAPHA AMINU BAKIN KASUWA',
        'AHMAD SANUSI SULAIMAN', 'SAFIYYAH SAIFULLAH FARUK', 'ABDULJABBAR YUSUF YUSUFARI',
        'MUHAMMAD ALAMIN HUSSAIN', 'HALIMA GONI ABATCHA', 'NANA GONI ABATCHA',
        'ABUBAKAR BAMODU YERIMA', 'ABUBAKAR SHUAIBU', 'BILIKSU DEENI SAEED',
        'MUHAMMAD AWWAL JIRIL ONIMISI', 'ZAINAB LAWAL',
    ],
    'Year 5': [
        'MARYAM GARBA UMAR', 'AHMAD ZAYD AHMAD', 'ABUBAKAR ABDULKADIR RAHIS',
        'FATIMA BASHIR GWADABE', 'ABUBAKAR MUSATAPHA BABA-KUSA', 'HAJARA BABA GANA ZANNA',
        'HAUWA ALI KHAIRAT', 'MARYAM HAMZA GALADIMA', 'SAFIYYAH MUHAMMAD',
        'SALIM SANUSI UMAR', 'MARYAM IDRIS SALEH', 'BATUL GONI ABATCHA',
        'MUHAMMAD NAEEM AKOREDU', 'KHADIJA USMAN DANMUSA', 'INUWA MUHAMMAD NURA DANKADAI',
        'MARYAM SHUAIBU', 'FATIMA ABDULLAHI MUHAMMAD GERIE', 'MUHAMMAD AWWAL JIRIL ONIMISI',
    ],
    'Year 6': [
        'AISHAT SURAJ ABDULLAHI', 'ADAM HASSAN', 'KHALID UMAR ABDULLAHI',
        'HALIMA YAKUBU SHEHU', 'AISHA KYAURE ALI', 'MUHAMMAD HUSSAINI BUHARI',
        'ABUBAKAR ABDULMUMIN BELLO', 'BILKISU KABIR TAFIDA', 'IBRAHIM ABUBAKAR USMAN',
        'MUHAMMAD SAEED GARBA', 'FATIMA AMINU HASSAN ZAHRA', 'ABDALLAH NASIR IMAM',
        'MADJULIN BILAL MUHAMMAD', 'ZULAIHAT SURAJ BABURA', 'SAID SURAJ BABURA',
        'AHMAD SURAJ BABURA', 'SAID SANI SANI',
    ],
    'Year 7': [
        'RUMAISA UMAR FAROUK', 'ABDULLAHI ALI BUBA', 'FATIMA SAID SAIDU',
        'RUKAYYA ABDUL NINGI', 'MARYAM YUSUF ABUBAKAR', 'MUHAMMAD IBRAHIM BABA',
        'HINDATU USMAN DANMUSA', 'JIBRIL BAMODU YERIMA', 'UMAR BASHAR',
        'ABDULLAHI USMAN SHUAIBU', 'AISHA ASHIRU SOLI', 'MUHAMMADALI ABDULMUMIN',
        'AISHA SURAJ ABDULLAHI', 'AISHA ALI KYUARE', 'MADJULIN BILAL',
        'ADAM HASSAN', 'AMINA ISAH ABBAS', 'HALIMA YAKUBU SHEHU',
        'SAEED SHUAIBU ISMAIL', 'AMEER MUHAMMAD DANTORO',
    ],
    'Year 8': [
        'Zainab Musa Abdulhamid', 'Bilkisu Almakura', 'Maya Ali',
        'Rukayya Tijjani Muhammad', 'Aisha Aminu Bakin Kasuwa', 'Muhammad Mustapha Rufau',
        'Husseni Baba Kusa M', 'Alameen Ali', 'Abdallah Zayd Ahmad',
        'Sulaiman Suraj Abdullahi', 'Abubakar Ibrahim Shettima', 'Nana Abdulkadir Rahis',
        'Hauwa Hamza Galadima', 'Hadiza Modibbo', 'Maryam Samateh',
        'Muhammad Bello Nura Dankadai', 'Abubakar Adnan Aminu',
        'Aisha Jibril Ohunene', 'Rumaisa Lawal',
    ],
    'Year 9': [
        'Adnan Masduk Muhammad', 'Bilkisu Ibrahim Arabi', 'Miral Bilal', 'Ahmed Ahmed',
        'Farouk Umar Wakili', 'Faizullah Abdulmalik', 'Sultana Abdulmaleek', 'Abdullah Hassan',
        'Zakaria Ali Gana', 'Aliyu Isa Yahaya', 'Ahmad Almakura', 'Nana Aisha Idris',
        'Maryam Saidu Idris', 'Umar Ibrahim Shettima', 'Maryam Magoro Muhammad',
        'Abdul-Hamid Shehu Galadima', 'Iman Abdullahi', 'Zahir Yussuf Oluwabogtomi',
        'Nabil Attahiru Umar', 'Aliyu Ibrahim', 'Imran Ahmad Ajuji',
        'Fateemah Shuaibu Ismail', 'Hannatu Adnan Aminu', 'Aisha Jibril Ohunene',
    ],
    'Year 10': [
        'Maryam Ibrahim Baba', 'Walid Umar Farouk', "Nana Asma'u Bashar", 'Amina Samateh',
        'Bilkisu Modibbo', 'Aisha Ali Buba', 'Habiba Abdulmuminu', 'Maryam Sanusi Sulaiman',
        'Fatima Lawal Idris', 'Aman Bint Badamasuiy', 'Niima Abubakar Wada',
        'Hassan Abdullahi Muhammad Gerie', 'Hussaini Abdullahi Muhammad Gerie',
        'Yusuf Abdullahi Muhammad Gerie', 'Abdullahi Ahmad Ajuji', 'Ahmed Tahir',
        'Muhammad Abubakar Ali', 'Ameerah Muhammad Dantoro',
    ],
    'Year 11': [
        'Muhammad Umar Farouk', 'Muhammad Alaamin Gidado', 'Amina Sulaiamn Damagun',
        'Abdulkadir Muhammad Chindo', 'Abdurrahim Ibrahim Buga', 'Jamila Abubakar',
        'Muhammad Ibrahim Shettima', 'Mutmainat Lukman Babawale', 'Abdulrahman Kyaure',
        'Arwa Alameen Ibrahim', 'Abdulmaleek Alameen Ibrahim', 'Rukayya Sadik Mahmud',
        'Aisha Humaira Bashir',
    ],
    'Year 12': [
        'Ibrahim Garba Umar', 'Ummusalma Maiyaki', 'Aljarnatu Modibbo',
        'Abdullahi Suraj Abdullahi', 'Abdullahi Ibrahim Arabi', 'Rabiat Ahmed Nakwada',
        'Nana Aishatu Abdullahi', 'Hauwa Shehu Muhammed', 'Khadija Baba Gana',
        'Amal Abdulmumin Ali', 'Khalil Tijjani Abubakar', 'Al-Amin Shehu Galadima',
        'Ahmad Abubakar', 'Aisha Isa Yahaya', 'Hauwa Mohammed Ciroma',
        'Abdallah Ahmad Tijjani',
    ],
}

# ── Assessment subjects ────────────────────────────────────
ASSESSMENT_SUBJECTS = ['Math', 'Science', 'English', 'Deen', 'Arabic', 'Quran Oral']

# ── Uniform items ──────────────────────────────────────────
# Default fallback (not used directly — section lists below are used per class)
UNIFORM_ITEMS = ['Sportwear', 'Shirt', 'Friday Wear', 'Cardigan', 'Socks']

# Items per section (boys + girls combined — officer ticks what applies per student)
NURSERY_UNIFORM_ITEMS = [
    'Sportwear',
    'Shirt',           # boys
    'Short',           # boys
    'Blouse',          # girls
    'Pinafore',        # girls
    'Friday Wear',
    'Cardigan',
    'Socks',
    'Panty Hose',      # girls
    'White Hijab',     # girls
    'Blue Hijab',      # girls
]

PRIMARY_UNIFORM_ITEMS = [
    'Sportwear',
    'Shirt',           # boys
    'Trouser',         # boys
    'Blouse',          # girls
    'Pinafore / Trouser',  # girls
    'Friday Wear',
    'Cardigan',
    'Socks',
    'White Hijab',     # girls
    'Blue Hijab',      # girls
]

SECONDARY_UNIFORM_ITEMS = [
    'Sportwear',
    'Shirt - Long Sleeve',   # boys
    'Trouser',               # boys
    'Skirt',                 # girls
    'Friday Wear',
    'Blazer',
    'Tie',
    'White Hijab',           # girls
    'Blue Hijab',            # girls
]

SECTION_UNIFORM_ITEMS = {
    'Nursery 1': NURSERY_UNIFORM_ITEMS,
    'Nursery 2': NURSERY_UNIFORM_ITEMS,
    'Nursery 3': NURSERY_UNIFORM_ITEMS,
    'Year 1':  PRIMARY_UNIFORM_ITEMS,
    'Year 2':  PRIMARY_UNIFORM_ITEMS,
    'Year 3':  PRIMARY_UNIFORM_ITEMS,
    'Year 4':  PRIMARY_UNIFORM_ITEMS,
    'Year 5':  PRIMARY_UNIFORM_ITEMS,
    'Year 6':  PRIMARY_UNIFORM_ITEMS,
    'Year 7':  SECONDARY_UNIFORM_ITEMS,
    'Year 8':  SECONDARY_UNIFORM_ITEMS,
    'Year 9':  SECONDARY_UNIFORM_ITEMS,
    'Year 10': SECONDARY_UNIFORM_ITEMS,
    'Year 11': SECONDARY_UNIFORM_ITEMS,
    'Year 12': SECONDARY_UNIFORM_ITEMS,
}


# ═══════════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════════

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_name = db.Column(db.String(150), nullable=False)
    date_of_birth = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    class_applying = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20))
    previous_school = db.Column(db.String(200))
    address = db.Column(db.Text)
    parent_name = db.Column(db.String(150), nullable=False)
    parent_email = db.Column(db.String(150))
    parent_phone = db.Column(db.String(30))
    second_parent_name = db.Column(db.String(150))
    second_parent_phone = db.Column(db.String(30))
    enquiry_date = db.Column(db.String(20), default=lambda: date.today().isoformat())
    stage = db.Column(db.String(80), default='Enquiry')
    notes = db.Column(db.Text)

    stage_histories = db.relationship('StageHistory', backref='student', lazy=True,
                                      cascade='all, delete-orphan',
                                      order_by='StageHistory.changed_at')
    checklist_items = db.relationship('ChecklistItem', backref='student', lazy=True,
                                      cascade='all, delete-orphan')
    activity_notes = db.relationship('ActivityNote', backref='student', lazy=True,
                                     cascade='all, delete-orphan',
                                     order_by='ActivityNote.created_at.desc()')


class StageHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    stage = db.Column(db.String(80), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    stage = db.Column(db.String(80), nullable=False)
    item = db.Column(db.String(300), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)


class ActivityNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UniformStudent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    student_name = db.Column(db.String(150), nullable=False)
    class_name = db.Column(db.String(100), nullable=False)
    accepted = db.Column(db.Boolean, default=False)
    accepted_at = db.Column(db.DateTime)
    is_new = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('UniformCollectionItem', backref='uniform_student',
                            cascade='all, delete-orphan', lazy=True)


class UniformCollectionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uniform_student_id = db.Column(db.Integer, db.ForeignKey('uniform_student.id'))
    name = db.Column(db.String(100), nullable=False)
    collected = db.Column(db.Boolean, default=False)
    collected_at = db.Column(db.DateTime)


class UniformItemTemplate(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    position   = db.Column(db.Integer, default=0)
    class_name = db.Column(db.String(100), nullable=True)


class AssessmentDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False, unique=True)
    assessment_date = db.Column(db.String(20))
    assessment_time = db.Column(db.String(20))
    assessment_number = db.Column(db.String(50))


class AssessmentScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    score = db.Column(db.String(20))
    passed = db.Column(db.Boolean)


# ═══════════════════════════════════════════════════════════
#  DB SETUP & MIGRATION
# ═══════════════════════════════════════════════════════════

def seed_checklist(student, stage):
    valid_items = STAGE_CHECKLIST.get(stage, [])
    existing = {ci.item: ci.completed for ci in
                ChecklistItem.query.filter_by(student_id=student.id, stage=stage).all()}
    needs_reorder = list(existing.keys()) != valid_items
    if needs_reorder:
        ChecklistItem.query.filter_by(student_id=student.id, stage=stage).delete(synchronize_session=False)
        for item_text in valid_items:
            db.session.add(ChecklistItem(
                student_id=student.id, stage=stage, item=item_text,
                completed=existing.get(item_text, False),
            ))
    else:
        for item_text in valid_items:
            if item_text not in existing:
                db.session.add(ChecklistItem(student_id=student.id, stage=stage, item=item_text))
    db.session.commit()


def cleanup_all_checklists():
    for student in Student.query.all():
        affected_stages = {r[0] for r in db.session.query(ChecklistItem.stage)
                          .filter_by(student_id=student.id).distinct().all()}
        affected_stages.add(student.stage)
        for stage in affected_stages:
            seed_checklist(student, stage)


def get_uniform_items(class_name=None):
    if class_name:
        templates = UniformItemTemplate.query.filter_by(class_name=class_name).order_by(UniformItemTemplate.position).all()
        if templates:
            return [t.name for t in templates]
    return SECTION_UNIFORM_ITEMS.get(class_name, UNIFORM_ITEMS)


def seed_uniform_item_templates():
    for cls in CLASSES_LIST:
        if UniformItemTemplate.query.filter_by(class_name=cls).count() == 0:
            defaults = SECTION_UNIFORM_ITEMS.get(cls, UNIFORM_ITEMS)
            for i, name in enumerate(defaults):
                db.session.add(UniformItemTemplate(name=name, position=i, class_name=cls))
    db.session.commit()


def sync_uniform_items():
    for us in UniformStudent.query.filter_by(accepted=True).all():
        raw = us.class_name.strip()
        canonical = next((c for c in CLASSES_LIST if c.lower() == raw.lower()), raw.title())
        valid_names = get_uniform_items(canonical)
        UniformCollectionItem.query.filter(
            UniformCollectionItem.uniform_student_id == us.id,
            UniformCollectionItem.name.notin_(valid_names),
        ).delete(synchronize_session=False)
        existing = {ci.name for ci in UniformCollectionItem.query.filter_by(uniform_student_id=us.id).all()}
        for item_name in valid_names:
            if item_name not in existing:
                db.session.add(UniformCollectionItem(
                    uniform_student_id=us.id, name=item_name, collected=False
                ))
    db.session.commit()


def seed_existing_uniform_students():
    for class_name, names in EXISTING_UNIFORM_STUDENTS.items():
        for name in names:
            us = UniformStudent.query.filter_by(
                student_name=name, class_name=class_name
            ).first()
            if not us:
                us = UniformStudent(
                    student_id=None,
                    student_name=name,
                    class_name=class_name,
                    accepted=True,
                    accepted_at=datetime.utcnow(),
                    is_new=False,
                )
                db.session.add(us)
                db.session.flush()
                for item_name in get_uniform_items(class_name):
                    db.session.add(UniformCollectionItem(
                        uniform_student_id=us.id,
                        name=item_name,
                        collected=False,
                    ))
            else:
                us.is_new = False  # fix any already-seeded records
    db.session.commit()


def migrate_db():
    with db.engine.connect() as conn:
        cols = {row[1] for row in conn.execute(db.text('PRAGMA table_info(student)'))}
        new_cols = [
            ('gender', 'VARCHAR(10)'),
            ('academic_year', 'VARCHAR(20)'),
            ('address', 'TEXT'),
            ('second_parent_name', 'VARCHAR(150)'),
            ('second_parent_phone', 'VARCHAR(30)'),
        ]
        for col, col_type in new_cols:
            if col not in cols:
                conn.execute(db.text(f'ALTER TABLE student ADD COLUMN {col} {col_type}'))
        tpl_cols = {row[1] for row in conn.execute(db.text('PRAGMA table_info(uniform_item_template)'))}
        if 'class_name' not in tpl_cols and 'uniform_item_template' in db.inspect(db.engine).get_table_names():
            conn.execute(db.text('ALTER TABLE uniform_item_template ADD COLUMN class_name VARCHAR(100)'))
        conn.commit()


with app.app_context():
    db.create_all()
    migrate_db()
    cleanup_all_checklists()
    seed_uniform_item_templates()
    seed_existing_uniform_students()
    sync_uniform_items()


# ═══════════════════════════════════════════════════════════
#  AUTH DECORATORS
# ═══════════════════════════════════════════════════════════

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_auth'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def uniform_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('uniform_auth'):
            return redirect(url_for('uniform_login'))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_auth'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form.get('passcode') == ADMIN_PASSCODE:
            session.permanent = True
            session['admin_auth'] = True
            return redirect(url_for('dashboard'))
        flash('Incorrect passcode. Please try again.', 'danger')
    return render_template('login.html', role='admin',
                           title='Admissions Portal',
                           subtitle='Enter your admin passcode to continue')


@app.route('/logout')
def admin_logout():
    session.pop('admin_auth', None)
    return redirect(url_for('admin_login'))


@app.route('/uniform/login', methods=['GET', 'POST'])
def uniform_login():
    if session.get('uniform_auth'):
        return redirect(url_for('uniform_dashboard'))
    if request.method == 'POST':
        if request.form.get('passcode') == UNIFORM_PASSCODE:
            session.permanent = True
            session['uniform_auth'] = True
            return redirect(url_for('uniform_dashboard'))
        flash('Incorrect passcode. Please try again.', 'danger')
    return render_template('login.html', role='uniform',
                           title='Uniform Collection',
                           subtitle='Enter your passcode to access uniform records')


@app.route('/uniform/logout')
def uniform_logout():
    session.pop('uniform_auth', None)
    return redirect(url_for('uniform_login'))


# ═══════════════════════════════════════════════════════════
#  ADMISSIONS ROUTES  (all require admin_required)
# ═══════════════════════════════════════════════════════════

@app.route('/')
@admin_required
def dashboard():
    stage_counts = {s: Student.query.filter_by(stage=s).count() for s in STAGES}
    total = Student.query.count()
    enrolled = stage_counts.get('Welcome Pack / Enrolled', 0)
    rejected = stage_counts.get('Rejected', 0)
    withdrawn = stage_counts.get('Withdrawn', 0)
    in_progress = total - enrolled - rejected - withdrawn
    recent = Student.query.order_by(Student.id.desc()).limit(5).all()
    conversion = round(enrolled / total * 100) if total > 0 else 0
    active_counts = {s: stage_counts[s] for s in ACTIVE_STAGES}
    max_count = max(active_counts.values()) if active_counts else 1

    # Class capacity — existing baseline + newly enrolled via admissions
    newly_enrolled = {row[0]: row[1] for row in db.session.query(
        Student.class_applying, func.count(Student.id)
    ).filter(
        Student.stage == 'Welcome Pack / Enrolled',
        Student.class_applying != None,
        Student.class_applying != ''
    ).group_by(Student.class_applying).all()}

    class_capacity = []
    total_existing = sum(EXISTING_STUDENTS.values())
    total_new_enrolled = 0
    for cls in CLASSES_LIST:
        existing = EXISTING_STUDENTS.get(cls, 0)
        new_in = newly_enrolled.get(cls, 0)
        total_new_enrolled += new_in
        total_in_class = existing + new_in
        pct = min(100, round(total_in_class / CLASS_MAX * 100))
        class_capacity.append({
            'name': cls, 'existing': existing,
            'new': new_in, 'count': total_in_class, 'pct': pct,
        })

    return render_template(
        'dashboard.html',
        stage_counts=stage_counts, total=total, enrolled=enrolled,
        rejected=rejected, in_progress=in_progress, withdrawn=withdrawn,
        recent=recent, stage_colors=STAGE_COLORS, stages=STAGES,
        active_stages=ACTIVE_STAGES, conversion=conversion,
        max_count=max_count or 1, stage_hex=STAGE_HEX, stage_soft=STAGE_SOFT,
        class_capacity=class_capacity, class_max=CLASS_MAX,
        total_existing=total_existing, total_new_enrolled=total_new_enrolled,
    )


@app.route('/admissions')
@admin_required
def admissions():
    stage_filter = request.args.get('stage', '')
    search = request.args.get('search', '').strip()
    year_filter = request.args.get('year', '')
    query = Student.query
    if stage_filter:
        query = query.filter_by(stage=stage_filter)
    if year_filter:
        query = query.filter_by(academic_year=year_filter)
    if search:
        query = query.filter(
            db.or_(
                Student.child_name.ilike(f'%{search}%'),
                Student.parent_name.ilike(f'%{search}%'),
            )
        )
    students = query.order_by(Student.id.desc()).all()
    return render_template(
        'admissions.html', students=students, stages=STAGES,
        stage_colors=STAGE_COLORS, stage_filter=stage_filter,
        search=search, year_filter=year_filter, academic_years=ACADEMIC_YEARS,
        stage_hex=STAGE_HEX, stage_soft=STAGE_SOFT,
    )


@app.route('/admissions/add', methods=['GET', 'POST'])
@admin_required
def add_admission():
    if request.method == 'POST':
        student = Student(
            child_name=request.form['child_name'],
            date_of_birth=request.form.get('date_of_birth', ''),
            gender=request.form.get('gender', ''),
            class_applying=request.form['class_applying'],
            academic_year=request.form.get('academic_year', ''),
            previous_school=request.form.get('previous_school', ''),
            address=request.form.get('address', ''),
            parent_name=request.form['parent_name'],
            parent_email=request.form.get('parent_email', ''),
            parent_phone=request.form.get('parent_phone', ''),
            second_parent_name=request.form.get('second_parent_name', ''),
            second_parent_phone=request.form.get('second_parent_phone', ''),
            notes=request.form.get('notes', ''),
            enquiry_date=date.today().isoformat(),
            stage='Enquiry',
        )
        db.session.add(student)
        db.session.flush()
        db.session.add(StageHistory(student_id=student.id, stage='Enquiry'))
        seed_checklist(student, 'Enquiry')
        db.session.commit()
        flash(f'{student.child_name} added successfully.', 'success')
        return redirect(url_for('student_detail', student_id=student.id))
    return render_template('add_admission.html', academic_years=ACADEMIC_YEARS, classes_list=CLASSES_LIST)


@app.route('/admissions/<int:student_id>')
@admin_required
def student_detail(student_id):
    student = db.get_or_404(Student, student_id)
    seed_checklist(student, student.stage)
    checklist_items = ChecklistItem.query.filter_by(
        student_id=student.id, stage=student.stage
    ).all()
    stage_histories = StageHistory.query.filter_by(
        student_id=student.id
    ).order_by(StageHistory.changed_at).all()
    activity_notes = ActivityNote.query.filter_by(
        student_id=student.id
    ).order_by(ActivityNote.created_at.desc()).all()
    stage_index = ACTIVE_STAGES.index(student.stage) if student.stage in ACTIVE_STAGES else -1
    done_count = sum(1 for i in checklist_items if i.completed)
    assessment = AssessmentDetail.query.filter_by(student_id=student_id).first()
    assessment_scores = {s.subject: s for s in AssessmentScore.query.filter_by(student_id=student_id).all()}
    return render_template(
        'student.html', student=student, stages=STAGES,
        stage_colors=STAGE_COLORS, checklist_items=checklist_items,
        active_stages=ACTIVE_STAGES, stage_histories=stage_histories,
        activity_notes=activity_notes, stage_index=stage_index,
        done_count=done_count, stage_hex=STAGE_HEX, stage_soft=STAGE_SOFT,
        assessment=assessment, assessment_scores=assessment_scores,
        assessment_subjects=ASSESSMENT_SUBJECTS, classes_list=CLASSES_LIST,
    )


@app.route('/admissions/<int:student_id>/stage', methods=['POST'])
@admin_required
def update_stage(student_id):
    student = db.get_or_404(Student, student_id)
    new_stage = request.form['stage']
    if new_stage in STAGES and new_stage != student.stage:
        student.stage = new_stage
        db.session.add(StageHistory(student_id=student.id, stage=new_stage))
        db.session.commit()
        seed_checklist(student, new_stage)

        # Auto-create uniform record when student is enrolled
        if new_stage == 'Welcome Pack / Enrolled':
            existing = UniformStudent.query.filter_by(student_id=student.id).first()
            if not existing:
                us = UniformStudent(
                    student_id=student.id,
                    student_name=student.child_name,
                    class_name=student.class_applying,
                )
                db.session.add(us)
                db.session.commit()

        flash(f'Stage updated to "{new_stage}".', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/admissions/<int:student_id>/checklist/<int:item_id>/toggle', methods=['POST'])
@admin_required
def toggle_checklist(student_id, item_id):
    item = db.get_or_404(ChecklistItem, item_id)
    if item.student_id != student_id:
        return jsonify({'error': 'not found'}), 404
    item.completed = not item.completed
    item.completed_at = datetime.utcnow() if item.completed else None
    db.session.commit()
    return jsonify({'completed': item.completed})


@app.route('/admissions/<int:student_id>/notes/add', methods=['POST'])
@admin_required
def add_note(student_id):
    student = db.get_or_404(Student, student_id)
    note_text = request.form.get('note', '').strip()
    if note_text:
        db.session.add(ActivityNote(student_id=student.id, note=note_text))
        db.session.commit()
        flash('Note added.', 'success')
    return redirect(url_for('student_detail', student_id=student_id) + '#activity-log')


@app.route('/admissions/<int:student_id>/edit', methods=['POST'])
@admin_required
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)
    student.child_name = request.form['child_name']
    student.date_of_birth = request.form.get('date_of_birth', '')
    student.gender = request.form.get('gender', '')
    student.class_applying = request.form['class_applying']
    student.academic_year = request.form.get('academic_year', '')
    student.previous_school = request.form.get('previous_school', '')
    student.address = request.form.get('address', '')
    student.parent_name = request.form['parent_name']
    student.parent_email = request.form.get('parent_email', '')
    student.parent_phone = request.form.get('parent_phone', '')
    student.second_parent_name = request.form.get('second_parent_name', '')
    student.second_parent_phone = request.form.get('second_parent_phone', '')
    student.notes = request.form.get('notes', '')
    db.session.commit()
    flash('Record updated.', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/admissions/<int:student_id>/assessment', methods=['POST'])
@admin_required
def save_assessment(student_id):
    student = db.get_or_404(Student, student_id)
    detail = AssessmentDetail.query.filter_by(student_id=student_id).first()
    if not detail:
        detail = AssessmentDetail(student_id=student_id)
        db.session.add(detail)
    detail.assessment_date = request.form.get('assessment_date', '').strip()
    detail.assessment_time = request.form.get('assessment_time', '').strip()
    detail.assessment_number = request.form.get('assessment_number', '').strip()

    for subject in ASSESSMENT_SUBJECTS:
        key = subject.lower().replace(' ', '_')
        score_val = request.form.get(f'score_{key}', '').strip()
        result_val = request.form.get(f'result_{key}', '')

        score_rec = AssessmentScore.query.filter_by(
            student_id=student_id, subject=subject
        ).first()
        if not score_rec:
            score_rec = AssessmentScore(student_id=student_id, subject=subject)
            db.session.add(score_rec)
        score_rec.score = score_val or None
        score_rec.passed = True if result_val == 'pass' else (False if result_val == 'fail' else None)

    db.session.commit()
    flash('Assessment details saved.', 'success')
    return redirect(url_for('student_detail', student_id=student_id))


@app.route('/admissions/<int:student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    name = student.child_name
    db.session.delete(student)
    db.session.commit()
    flash(f'{name} has been removed.', 'warning')
    return redirect(url_for('admissions'))


@app.route('/admissions/<int:student_id>/print')
@admin_required
def print_student(student_id):
    student = db.get_or_404(Student, student_id)
    stage_histories = StageHistory.query.filter_by(
        student_id=student.id
    ).order_by(StageHistory.changed_at).all()
    all_checklist = {}
    for stage in ACTIVE_STAGES:
        items = ChecklistItem.query.filter_by(student_id=student.id, stage=stage).all()
        if items:
            all_checklist[stage] = items
    activity_notes = ActivityNote.query.filter_by(
        student_id=student.id
    ).order_by(ActivityNote.created_at).all()
    return render_template(
        'print_student.html', student=student,
        stage_histories=stage_histories, all_checklist=all_checklist,
        activity_notes=activity_notes, stage_colors=STAGE_COLORS,
        now=datetime.utcnow().strftime('%d %b %Y'),
    )


# ═══════════════════════════════════════════════════════════
#  UNIFORM ROUTES  (all require uniform_required)
# ═══════════════════════════════════════════════════════════

def _normalize_class(name):
    name = name.strip()
    for cls in CLASSES_LIST:
        if cls.lower() == name.lower():
            return cls
    return name.title()


@app.route('/uniform/')
@uniform_required
def uniform_dashboard():
    accepted = UniformStudent.query.filter_by(accepted=True).order_by(
        UniformStudent.student_name
    ).all()

    # Group by normalized class name, preserving CLASSES_LIST order
    raw = {}
    for s in accepted:
        key = _normalize_class(s.class_name)
        raw.setdefault(key, []).append(s)

    classes = {}
    for cls in CLASSES_LIST:
        if cls in raw:
            classes[cls] = raw[cls]
    for cls in sorted(raw):        # any unlisted classes go at end
        if cls not in classes:
            classes[cls] = raw[cls]

    items_by_class = {cls: get_uniform_items(cls) for cls in classes}
    pending_count = UniformStudent.query.filter_by(accepted=False).count()
    return render_template(
        'uniform_dashboard.html',
        classes=classes, pending_count=pending_count,
        items_by_class=items_by_class, classes_list=CLASSES_LIST,
    )


@app.route('/uniform/student/<int:uid>/edit', methods=['POST'])
@uniform_required
def uniform_edit_student(uid):
    us = db.get_or_404(UniformStudent, uid)
    new_name = request.form.get('student_name', '').strip()
    new_class = request.form.get('class_name', '').strip()
    if new_name:
        us.student_name = new_name
    if new_class:
        us.class_name = new_class
    db.session.commit()
    flash('Student updated.', 'success')
    return redirect(url_for('uniform_dashboard'))


@app.route('/uniform/student/<int:uid>/delete', methods=['POST'])
@uniform_required
def uniform_delete_student(uid):
    us = db.get_or_404(UniformStudent, uid)
    name = us.student_name
    db.session.delete(us)
    db.session.commit()
    flash(f'{name} removed from uniform list.', 'success')
    return redirect(url_for('uniform_dashboard'))


@app.route('/uniform/class/delete', methods=['POST'])
@uniform_required
def uniform_delete_class():
    class_name = request.form.get('class_name', '').strip()
    if class_name:
        students = UniformStudent.query.filter(
            db.func.lower(UniformStudent.class_name) == class_name.lower()
        ).all()
        count = len(students)
        for s in students:
            db.session.delete(s)
        db.session.commit()
        flash(f'Removed {count} student{"s" if count != 1 else ""} from {class_name}.', 'warning')
    return redirect(url_for('uniform_dashboard'))


@app.route('/uniform/pending')
@uniform_required
def uniform_pending():
    pending = UniformStudent.query.filter_by(accepted=False).order_by(
        UniformStudent.created_at.desc()
    ).all()
    return render_template('uniform_pending.html', pending=pending)


@app.route('/uniform/accept/<int:uid>', methods=['POST'])
@uniform_required
def uniform_accept(uid):
    us = db.get_or_404(UniformStudent, uid)
    us.accepted = True
    us.accepted_at = datetime.utcnow()
    for item_name in get_uniform_items(us.class_name):
        db.session.add(UniformCollectionItem(
            uniform_student_id=us.id, name=item_name
        ))
    db.session.commit()
    flash(f'{us.student_name} has been added to {us.class_name}.', 'success')
    return redirect(url_for('uniform_pending'))


@app.route('/uniform/item/<int:item_id>/toggle', methods=['POST'])
@uniform_required
def uniform_toggle_item(item_id):
    item = db.get_or_404(UniformCollectionItem, item_id)
    item.collected = not item.collected
    item.collected_at = datetime.utcnow() if item.collected else None

    us = item.uniform_student
    all_done = all(i.collected for i in us.items)
    us.is_new = not all_done

    db.session.commit()
    return jsonify({'collected': item.collected, 'all_done': all_done})


@app.route('/uniform/student/add', methods=['POST'])
@uniform_required
def uniform_add_student():
    name = request.form.get('student_name', '').strip()
    class_name = request.form.get('class_name', '').strip()
    if not name or not class_name:
        flash('Name and class are required.', 'danger')
        return redirect(url_for('uniform_dashboard'))
    class_name = _normalize_class(class_name)
    us = UniformStudent(
        student_id=None,
        student_name=name,
        class_name=class_name,
        accepted=True,
        accepted_at=datetime.utcnow(),
        is_new=False,
    )
    db.session.add(us)
    db.session.flush()
    for item_name in get_uniform_items(class_name):
        db.session.add(UniformCollectionItem(
            uniform_student_id=us.id, name=item_name, collected=False
        ))
    db.session.commit()
    flash(f'{name} added to {class_name}.', 'success')
    return redirect(url_for('uniform_dashboard'))


@app.route('/uniform/manage', methods=['GET'])
@uniform_required
def uniform_manage():
    templates_by_class = {}
    for cls in CLASSES_LIST:
        templates_by_class[cls] = UniformItemTemplate.query.filter_by(
            class_name=cls).order_by(UniformItemTemplate.position).all()
    return render_template('uniform_manage.html',
                           templates_by_class=templates_by_class,
                           classes_list=CLASSES_LIST)


@app.route('/uniform/items/add', methods=['POST'])
@uniform_required
def uniform_add_item():
    name = request.form.get('item_name', '').strip()
    class_name = request.form.get('class_name', '').strip()
    if not name or not class_name:
        flash('Item name and class are required.', 'danger')
        return redirect(url_for('uniform_manage'))
    existing_tpl = UniformItemTemplate.query.filter_by(name=name, class_name=class_name).first()
    if existing_tpl:
        flash(f'"{name}" already exists for {class_name}.', 'warning')
        return redirect(url_for('uniform_manage'))
    max_pos = db.session.query(db.func.max(UniformItemTemplate.position)).filter_by(class_name=class_name).scalar() or 0
    db.session.add(UniformItemTemplate(name=name, position=max_pos + 1, class_name=class_name))
    students_in_class = UniformStudent.query.filter(
        db.func.lower(UniformStudent.class_name) == class_name.lower(),
        UniformStudent.accepted == True,
    ).all()
    for us in students_in_class:
        if not UniformCollectionItem.query.filter_by(uniform_student_id=us.id, name=name).first():
            db.session.add(UniformCollectionItem(uniform_student_id=us.id, name=name, collected=False))
    db.session.commit()
    flash(f'"{name}" added to {class_name}.', 'success')
    return redirect(url_for('uniform_manage'))


@app.route('/uniform/items/<int:tpl_id>/delete', methods=['POST'])
@uniform_required
def uniform_delete_item(tpl_id):
    tpl = db.get_or_404(UniformItemTemplate, tpl_id)
    name = tpl.name
    class_name = tpl.class_name
    students_in_class = UniformStudent.query.filter(
        db.func.lower(UniformStudent.class_name) == (class_name or '').lower(),
        UniformStudent.accepted == True,
    ).all()
    for us in students_in_class:
        UniformCollectionItem.query.filter_by(uniform_student_id=us.id, name=name).delete()
    db.session.delete(tpl)
    db.session.commit()
    flash(f'"{name}" removed from {class_name}.', 'warning')
    return redirect(url_for('uniform_manage'))


if __name__ == '__main__':
    app.run(debug=True)
