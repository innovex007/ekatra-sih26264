"""Fictional content for the synthetic dataset. No real institutions or people."""

# city, district, state, region, pincode
CITIES = [
    ("Tirupati", "Tirupati", "Andhra Pradesh", "South", "517502"), ("Hyderabad", "Hyderabad", "Telangana", "South", "500001"),
    ("Warangal", "Warangal", "Telangana", "South", "506002"), ("Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", "South", "530001"),
    ("Vijayawada", "Krishna", "Andhra Pradesh", "South", "520001"), ("Guntur", "Guntur", "Andhra Pradesh", "South", "522001"),
    ("Bengaluru", "Bengaluru Urban", "Karnataka", "South", "560001"), ("Mysuru", "Mysuru", "Karnataka", "South", "570001"),
    ("Mangaluru", "Dakshina Kannada", "Karnataka", "South", "575001"), ("Hubballi", "Dharwad", "Karnataka", "South", "580020"),
    ("Chennai", "Chennai", "Tamil Nadu", "South", "600001"), ("Coimbatore", "Coimbatore", "Tamil Nadu", "South", "641001"),
    ("Madurai", "Madurai", "Tamil Nadu", "South", "625001"), ("Tiruchirappalli", "Tiruchirappalli", "Tamil Nadu", "South", "620001"),
    ("Kochi", "Ernakulam", "Kerala", "South", "682001"), ("Thiruvananthapuram", "Thiruvananthapuram", "Kerala", "South", "695001"),
    ("Kozhikode", "Kozhikode", "Kerala", "South", "673001"), ("Mumbai", "Mumbai", "Maharashtra", "West", "400001"),
    ("Pune", "Pune", "Maharashtra", "West", "411001"), ("Nagpur", "Nagpur", "Maharashtra", "West", "440001"),
    ("Nashik", "Nashik", "Maharashtra", "West", "422001"), ("Ahmedabad", "Ahmedabad", "Gujarat", "West", "380001"),
    ("Surat", "Surat", "Gujarat", "West", "395001"), ("Vadodara", "Vadodara", "Gujarat", "West", "390001"),
    ("Rajkot", "Rajkot", "Gujarat", "West", "360001"), ("Panaji", "North Goa", "Goa", "West", "403001"),
    ("Delhi", "New Delhi", "Delhi", "North", "110001"), ("Gurugram", "Gurugram", "Haryana", "North", "122001"),
    ("Chandigarh", "Chandigarh", "Chandigarh", "North", "160017"), ("Ludhiana", "Ludhiana", "Punjab", "North", "141001"),
    ("Jaipur", "Jaipur", "Rajasthan", "North", "302001"), ("Jodhpur", "Jodhpur", "Rajasthan", "North", "342001"),
    ("Dehradun", "Dehradun", "Uttarakhand", "North", "248001"), ("Lucknow", "Lucknow", "Uttar Pradesh", "Central", "226001"),
    ("Kanpur", "Kanpur Nagar", "Uttar Pradesh", "Central", "208001"), ("Varanasi", "Varanasi", "Uttar Pradesh", "Central", "221001"),
    ("Bhopal", "Bhopal", "Madhya Pradesh", "Central", "462001"), ("Indore", "Indore", "Madhya Pradesh", "Central", "452001"),
    ("Raipur", "Raipur", "Chhattisgarh", "Central", "492001"), ("Patna", "Patna", "Bihar", "East", "800001"),
    ("Ranchi", "Ranchi", "Jharkhand", "East", "834001"), ("Bhubaneswar", "Khordha", "Odisha", "East", "751001"),
    ("Kolkata", "Kolkata", "West Bengal", "East", "700001"), ("Durgapur", "Paschim Bardhaman", "West Bengal", "East", "713201"),
    ("Guwahati", "Kamrup Metropolitan", "Assam", "North-East", "781001"), ("Shillong", "East Khasi Hills", "Meghalaya", "North-East", "793001"),
    ("Imphal", "Imphal West", "Manipur", "North-East", "795001"),
]

NAME_WORDS = ["Venkatadri", "Kaveri", "Godavari", "Narmada", "Himalaya", "Vindhya", "Aravalli", "Sahyadri", "Nilgiri", "Ganga",
              "Yamuna", "Brahmaputra", "Krishna", "Saraswati", "Lakshmi", "Annapurna", "Shakti", "Vidya", "Jyoti", "Prerana",
              "Pragati", "Tejas", "Vikram", "Bharat", "Navjyoti", "Udaya", "Chandra", "Surya", "Indra", "Varuna", "Kailash",
              "Meru", "Hemadri", "Tungabhadra", "Sagar", "Kamal", "Deepak", "Arunodaya", "Shivalik", "Gomati", "Malabar",
              "Konkan", "Satpura", "Rudra", "Ashoka", "Pushpa", "Mandakini", "Triveni", "Ratnagiri", "Mahendra"]
PREFIXES = ["Shri", "Shri", "Sri", "Maharaja", "Acharya", "Sant", ""]
SUFFIXES = [("Institute of Technology", "Engineering College"), ("College of Engineering", "Technical Institute"),
            ("Institute of Management", "School of Management"), ("Engineering College", "Polytechnic College"),
            ("Polytechnic", "Technical Institute"), ("Institute of Technology and Management", "Engineering College"),
            ("Institute of Pharmacy", "College of Pharmacy"), ("Institute of Science and Technology", "Engineering College")]
INST_TYPES = {"Management": "Management", "Polytechnic": "Polytechnic", "Pharmacy": "Pharmacy"}

OFFICER_NAMES = ["A. Rao", "S. Iyer", "M. Khan", "P. Nair", "R. Sharma", "K. Banerjee", "D. Patil", "L. Menon", "V. Reddy",
                 "N. Gupta", "T. Das", "H. Singh", "J. Thomas", "G. Pillai", "B. Mishra", "C. Joshi", "F. Qureshi", "U. Kulkarni"]

SOURCES = ["CPGRAMS", "email", "letter", "walk-in", "VIP reference", "court", "PQ", "RTI"]
SOURCE_W = [38, 20, 12, 8, 6, 6, 4, 6]
CATEGORY_W = {"Infrastructure": 20, "Faculty": 16, "Fees & refund": 18, "Ragging": 6, "Norms violation": 20, "Admission": 12, "Other": 8}

TEMPLATES = {
    "Infrastructure": [
        "Classrooms have leaking roofs and broken benches; the campus drainage floods during rains.",
        "No functioning generator or power backup exists, so computer sessions stop during outages.",
        "Campus lacks a proper playground and sports ground; students have no recreation space.",
        "Washrooms are unclean with no running water, especially in the girls block.",
        "Wi-Fi and internet connectivity are absent in the main building despite fees collected for it.",
        "Approach road and parking area are damaged, and the bus service for students is irregular.",
        "Canteen operates in unhygienic conditions and cooking is done near the workshop shed.",
        "Auditorium and seminar hall are locked and used as storage while students lack seating."],
    "Faculty": [
        "Teachers are paid below the declared salary and appointment letters were never issued.",
        "Professors without required PhD qualification are shown as senior staff in records.",
        "Many subjects have no teacher for months and substitute lecturers take irregular classes.",
        "Head of department is absent for long periods and attendance registers are signed in advance.",
        "Faculty members were terminated abruptly without notice period or dues settled.",
        "Visiting lecturers are listed as permanent faculty during the inspection visit.",
        "Teaching staff are forced to do clerical work instead of lectures and labs.",
        "Experience certificates for lecturers are fake according to former employees."],
    "Fees & refund": [
        "Management refuses refund of tuition fee after student withdrew admission before classes began.",
        "Extra development fee demanded beyond the fee structure approved by the state committee.",
        "Original marksheets are retained until pending dues are paid, though the course is complete.",
        "Scholarship money received from government is not credited to the student account.",
        "Exam fee collected twice and no receipt has been given despite repeated requests.",
        "Transport fee charged although no bus facility exists for the student's route.",
        "Caution deposit not returned even after two years from course completion.",
        "Penalty for late payment is charged at an unreasonable rate, much above notified fees."],
    "Ragging": [
        "Senior students harass first-year juniors at night inside the hostel corridor.",
        "A student was forced to perform humiliating acts by seniors; the anti-ragging squad did nothing.",
        "Threats and abusive messages circulated on a social media group targeting new admissions.",
        "Anti-ragging committee has not been formed and the helpline number is not displayed.",
        "Freshers were made to stand for hours and money was extorted by a group of seniors.",
        "Physical assault during the welcome party left a student injured and the case hidden.",
        "Complaints to the warden about bullying are ignored and the victim is pressured to withdraw.",
        "Ragging incidents reported in the bus and canteen while security staff stay silent."],
    "Norms violation": [
        "Intake of students exceeds the sanctioned seats approved by AICTE for the course.",
        "Institute runs an unapproved programme and advertises it as AICTE approved.",
        "Mandatory disclosure on the website is outdated and shows wrong approval status.",
        "Land documents are in a different trust name, violating the approval conditions.",
        "Teacher student ratio is far below prescribed norms but reports show full compliance.",
        "Building plan approval from the municipal authority is missing for the new block.",
        "Admissions were made through management quota beyond the allowed percentage.",
        "Annual audit reports and accounts have not been submitted to the regulator."],
    "Admission": [
        "Merit list was altered and a lower ranked candidate was given the seat.",
        "Counselling fees were taken but the admission was cancelled without any reason.",
        "Seat promised under reserved category was denied despite valid certificate.",
        "Lateral entry admissions were refused although the candidate had a valid diploma.",
        "Admission test conducted by the institute lacked transparency and results were not published.",
        "Agent collected money for guaranteed seat and the college denies any role.",
        "Migration certificate and transfer documents delayed, blocking admission elsewhere.",
        "Wrong cut-off marks were displayed to avoid admitting eligible applicants."],
    "Other": [
        "Placement cell claims hundred percent placement but students received no offers.",
        "Student identity cards and library cards were not issued for the entire year.",
        "Principal is rude and misbehaves with parents who ask about results.",
        "Results are delayed by many months and revaluation requests go unanswered.",
        "Hostel warden restricts students from leaving campus even for urgent medical needs.",
        "Cultural fest sponsorship money collected from students has not been accounted for.",
        "Internship letters were refused and students lost the chance to apply abroad.",
        "Grievance cell exists only on paper and complaints are never acknowledged."],
}
TAILS = ["Reported by a parent from block {b}.", "Around {n} students are affected.", "Written complaint was submitted in {m}.",
         "Matter raised earlier with the management without response.", "Photographs and a signed petition are enclosed.",
         "The issue is continuing since the {sem} semester.", "Student union of the {dept} department has also written to the principal.",
         "Local newspaper coverage appeared on {d} {m}.", "Complainant requests an inspection by AICTE officers.",
         "Ward councillor has forwarded the complaint with remarks.", "Complaint number {ref} was registered on the state portal.",
         "The principal has refused to meet the parents.", "Alumni association supports the complaint.", "Similar problem was faced by the previous batch of {dept} students."]
DEPTS = ["Civil", "Mechanical", "Computer", "Electrical", "Electronics", "Chemical"]
SEMS = ["odd", "even", "first", "second", "final"]
MONTHS = ["May", "June", "July", "August", "September", "October"]

# (category, text from the complainant, text from the enforcing Bureau)
CONFLICT_TOPICS = [
    ("Norms violation", "Laboratory equipment is not available as per AICTE norms; students have no working computer lab or physics lab equipment.",
     "Show-cause issued for deficient laboratory equipment against AICTE norms; computer lab and physics lab equipment found missing."),
    ("Faculty", "Faculty shortage in mechanical and civil departments; qualified teachers have not been appointed and classes are not conducted.",
     "Show-cause for faculty shortage against norms in mechanical and civil departments; qualified teachers not appointed."),
    ("Infrastructure", "Hostel has no clean drinking water, mess hygiene is poor and rooms are overcrowded.",
     "Inspection found hostel drinking water unsafe, mess hygiene poor and rooms overcrowded; show-cause issued."),
    ("Infrastructure", "Building lacks fire safety clearance and emergency exits are blocked in the classroom block.",
     "Show-cause issued as fire safety clearance is missing and emergency exits blocked in the classroom building."),
    ("Norms violation", "Library has outdated books, no journal subscription and no digital library access as required by norms.",
     "Show-cause: library books outdated, journal subscription and digital library access missing against norms."),
    ("Fees & refund", "College refuses to refund fees after admission cancellation and withholds original certificates.",
     "Show-cause issued for withholding original certificates and not refunding fees after admission cancellation."),
]
RELATED_TOPICS = [
    ("Fees & refund", "Hostel fee charged is higher than approved and hostel mess facilities are poor.",
     "Hostel fees collected exceed the approved fee structure and hostel mess is inadequate."),
    ("Infrastructure", "Classrooms are overcrowded and benches broken, with no proper ventilation in the labs.",
     "Labs lack ventilation and classrooms have broken benches and overcrowding."),
    ("Faculty", "Teachers are not paid regular salary and appointment letters were not issued.",
     "Salary of teachers is delayed for months and no appointment letters are given."),
    ("Admission", "Seat promised in management quota was denied after fees were taken.",
     "Management quota admission refused after counselling fees were collected."),
]
INFO_TOPICS = [
    ("Norms violation", CONFLICT_TOPICS[0][1], "Fees & refund", "Caution deposit not returned even after two years from course completion."),
    ("Faculty", CONFLICT_TOPICS[1][1], "Admission", "Merit list was altered and a lower ranked candidate was given the seat."),
    ("Infrastructure", CONFLICT_TOPICS[2][1], "Fees & refund", "Exam fee collected twice and no receipt has been given despite repeated requests."),
    ("Norms violation", CONFLICT_TOPICS[4][1], "Ragging", "Senior students harass first-year juniors at night inside the hostel corridor."),
]
