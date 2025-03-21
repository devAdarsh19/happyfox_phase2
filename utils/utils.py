import time
import spacy
import re
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
# from ..main import api_key_mistral

nlp = spacy.load("en_core_web_sm")

# LinkedIn Credentials
LINKEDIN_EMAIL = "aayushkumar93407@gmail.com"
LINKEDIN_PASSWORD = "Linkedin@2205"

MISTRAL_API_KEY = "aKFEMuDwJOvtphHDDOrh2qbfRP7jEA1L"

# Define skill keywords
skill_keywords = [
    "Python", "Java", "JavaScript", "C++", "SQL", "MongoDB", "PostgreSQL", "Machine Learning",
    "Deep Learning", "Neural Networks", "Data Science", "AI", "Django", "Flask", "React", "React Native", "Node.js",
    "TensorFlow", "PyTorch", "API", "AWS", "Cloud Computing", "DevOps", "Competitive Programming","Data Structures",
    "Algorithms", "Web Development", "Software Development", "Computer Vision", "Natural Language Processing",
    "Data Analysis", "Business Intelligence", "Power BI", "Tableau", "Big Data", "Hadoop", "Spark", "ETL", "CI/CD",
    "Kubernetes", "Docker", "Git", "Linux", "Unix", "Shell Scripting", "Automation", "Agile", "Scrum", "Kanban", 
    "Problem Solving","HTML", "CSS", "Bootstrap", "SASS", "LESS", "jQuery", "Angular", "Vue.js", "TypeScript",
    "Svelte", "Web Design", "UI/UX","REST", "GraphQL", "Microservices", "Serverless", "Blockchain", "Cryptocurrency",
    "Solidity", "Ethereum", "DeFi", "NFT","Cybersecurity", "Ethical Hacking", "Penetration Testing", "OWASP",
    "Firewall", "VPN", "Security Audits", "Compliance", "ISO 27001","Risk Management", "Fraud Detection",
    "Identity & Access Management", "SIEM", "Splunk", "Networking", "TCP/IP", "DNS", "HTTP", "SSL","Wireless Networks",
    "Network Security", "Cisco", "Juniper", "CompTIA", "CCNA", "CCNP", "CCIE", "CEH", "CISSP", "CISM","CISA",
]

mistakes_per_skill = {}  # Initialize mistake tracking for quizzes

# Exclude these from the extracted skills
exclude_list = ["AuxPlutes Tech", "EBTS Organization"]

# Extracting skills from plain text over here -> Happens after scraping
def extract_skills(about_text):
    """Extracts skills from the About section using keyword matching & NLP, excluding unwanted entities."""
    extracted_skills = []
    lower_text = about_text.lower()

    # Extract based on keyword matching
    for skill in skill_keywords:
        if skill.lower() in lower_text:
            extracted_skills.append(skill)

    # Extract named entities using NLP
    doc = nlp(about_text)
    for token in doc.ents:
        if token.label_ in ["ORG", "PRODUCT"]:
            extracted_skills.append(token.text)

    # Remove excluded items
    extracted_skills = [skill for skill in extracted_skills if skill not in exclude_list]

    return list(set(extracted_skills))

# Logging into LinkedIn over here -> Used in scraping linkedin
def login_linkedin(driver):
    """Logs into LinkedIn"""
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    # Enter email and password
    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD + Keys.RETURN)

    time.sleep(10)  # Allow manual CAPTCHA completion
    
# Scrapes LinkedIn profile over here and returns plain text
def scrape_linkedin_profile(linkedin_url):
    """Scrapes LinkedIn profile for Name and About section"""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    login_linkedin(driver)
    driver.get(linkedin_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # Extract Name
    name_section = soup.find("h1")
    name = name_section.text.strip() if name_section else "No Name Found"

    # Extract About Section
    about_section = soup.find("div", {"class": "display-flex ph5 pv3"})
    about_text = about_section.text.strip() if about_section else "No About section found"

    # Extract skills from About section
    extracted_skills = extract_skills(about_text)

    return {
        "name": name,
        "about": about_text,
        "linkedin_url": linkedin_url,
        "skills": extracted_skills
    }
    
# Generating quiz questions over here
def generate_quiz_questions(skills, num_questions=10):
    questions = []
    print("\n⏳ Generating quiz questions...")

    MODEL_NAME = "mistral-large-latest"  
    questions_per_skill = max(1, num_questions // len(skills))  # Distribute questions evenly

    for skill in skills:
        for _ in range(questions_per_skill):
            if len(questions) >= num_questions:
                break  # Stop if we reach the desired number

            prompt_text = (
                f"Generate a hard multiple-choice question on {skill}. "
                "Provide a question, 4 answer choices (A, B, C, D), "
                "the correct answer, and a brief explanation.\n\n"
                "Format:\n"
                "Question: <question>\n"
                "A) <option 1>\n"
                "B) <option 2>\n"
                "C) <option 3>\n"
                "D) <option 4>\n"
                "Correct Answer: <correct option>\n"
                "Explanation: <why it's correct>"
            )

            retry_count = 0
            while retry_count < 3:
                try:
                    response = requests.post(
                        "https://api.mistral.ai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
                        json={
                            "model": MODEL_NAME,
                            "messages": [{"role": "user", "content": prompt_text}],
                            "max_tokens": 300
                        },
                        timeout=15
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"].strip()

                        # Extract values safely
                        question = None
                        options = []
                        correct_answer = None
                        explanation = None

                        lines = content.split("\n")
                        for line in lines:
                            line = line.strip()
                            if line.startswith("Question:"):
                                question = line.replace("Question:", "").strip()
                            elif line.startswith(("A)", "B)", "C)", "D)")):
                                options.append(line[3:].strip())
                            elif line.startswith("Correct Answer:"):
                                correct_answer = line.replace("Correct Answer:", "").strip()
                            elif line.startswith("Explanation:"):
                                explanation = line.replace("Explanation:", "").strip()

                        if question and len(options) == 4 and correct_answer and explanation:
                            questions.append({
                                "question": question,
                                "options": options,
                                "correct_answer": correct_answer.split(")")[0].strip(),
                                "explanation": explanation,
                                "skill": skill  # Store skill name for mistake tracking
                            })
                        break  

                    elif response.status_code == 429:
                        time.sleep(5 + retry_count * 5)
                        retry_count += 1  

                    else:
                        break  

                except requests.exceptions.RequestException:
                    break  

            time.sleep(2)  

    return questions
    
# Running the quiz here (analysis, test score and stuff)
def run_quiz(questions):
    global mistakes_per_skill  
    score = 0

    print("\n📌 Welcome to the AI-Generated Quiz!\n")

    for i, q in enumerate(questions, 1):
        print(f"\n🔹 Question {i}: {q['question']}")
        print(f"A) {q['options'][0]}")
        print(f"B) {q['options'][1]}")
        print(f"C) {q['options'][2]}")
        print(f"D) {q['options'][3]}")

        user_answer = input("\n👉 Enter your answer (A, B, C, or D): ").strip().upper()

        if user_answer == q["correct_answer"]:
            print("🎉 Hurray! It's the correct answer! ✅")
            score += 1  
        else:
            print(f"❌ Wrong! The correct answer is {q['correct_answer']}")

            # ✅ Track mistakes per skill
            skill = q["skill"]  
            mistakes_per_skill[skill] = mistakes_per_skill.get(skill, 0) + 1 
            
    return {"response": "Answer"}

        # Show explanation for all cases
    #     print(f"💡 Explanation: {q['explanation']}\n")

    # print("\n🎯 Quiz Complete!")
    # print(f"🏆 Your Score: {score} / {len(questions)}")
    
    # # 📊 Display Weak Skills
    # if mistakes_per_skill:
    #     print("\n📊 **Skills You Struggled With:**")
    #     for skill, count in mistakes_per_skill.items():
    #         print(f"🔸 {skill}: {count} mistakes")

    #     print("\n📚 **Recommended Study Areas:**")
    #     for skill in mistakes_per_skill.keys():
    #         print(f"✅ Revise more on {skill} to improve your performance.")

    # else:
    #     print("\n🎉 Well done! No weak areas detected!")