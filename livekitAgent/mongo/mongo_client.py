from pymongo import MongoClient
from bson.objectid import ObjectId
import logging
import os
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Connect to MongoDB with authentication
client = MongoClient(os.getenv("MONGO_CONNECTION_URL"))

# Select database and collection
db = client["livekit"]
collection = db["resume"]

# Predefined ObjectId
doc_id = ObjectId("686b60d2a6601148142a968b")

# Insert test document only if it doesn't exist
if not collection.find_one({"_id": doc_id}):
    collection.insert_one({
        "_id": doc_id,
        "resume": """John Smith - Software Developer

Contact Information:
Email: john.smith@email.com
Phone: +1-555-0123
Address: 123 Main St, New York, NY 10001

Professional Summary:
Experienced software developer with 5+ years in full-stack development. Proven track record of delivering scalable web applications and leading development teams.

Skills:
• Programming Languages: JavaScript, Python, Java, C++
• Web Technologies: React, Node.js, HTML5, CSS3, RESTful APIs
• Databases: MongoDB, MySQL, PostgreSQL
• Tools & Technologies: Git, Docker, AWS, Jenkins, Agile/Scrum
• Soft Skills: Team Leadership, Problem Solving, Communication

Work Experience:

Senior Software Developer | Tech Solutions Inc | 2021 - Present
• Developed and maintained web applications using React and Node.js
• Led a team of 4 junior developers and conducted regular code reviews
• Improved application performance by 40% through optimization techniques
• Collaborated with product managers to define technical requirements

Full Stack Developer | StartupXYZ | 2019 - 2021
• Built responsive web applications from scratch using modern frameworks
• Implemented RESTful APIs and designed database schemas
• Reduced page load times by 35% through code optimization
• Worked in an agile environment with rapid deployment cycles

Education:
Bachelor of Science in Computer Science
State University | Graduated: 2019
GPA: 3.8/4.0

Certifications:
• AWS Certified Developer - Associate (2022)
• MongoDB Certified Developer (2021)
• Scrum Master Certification (2020)"""
    })

# Fetch candidate data by ObjectId
def getCandidateDBData(id: str):
    try:
        return collection.find_one({"_id": ObjectId(id)})
    except Exception as e:
        print(f"Error: {e}")
        return None

# Example usage
if __name__ == "__main__":
    candidate = getCandidateDBData("686b60d2a6601148142a968b")
    if candidate:
        print("Resume:\n", candidate.get("resume"))
    else:
        print("Candidate not found.")
