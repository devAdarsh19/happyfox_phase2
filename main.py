from mistralai import Mistral
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import spacy
import os
from utils import schemas
from utils import utils
import time

# nlp = spacy.load("en_core_web_sm")

# Skill keywords
# skill_keywords = [
#     "Python", "Java", "JavaScript", "C++", "SQL", "Machine Learning",
#     "Deep Learning", "Neural Networks", "Data Science", "AI", "Django",
#     "Flask", "React", "TensorFlow", "PyTorch", "AWS", "Cloud Computing",
#     "DevOps", "Data Structures", "Algorithms", "Web Development"
# ]

load_dotenv("C:\\Users\\ADMIN\\Desktop\\api_key.env")
api_key_mistral = os.getenv("MISTRALAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust if deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/trending_tech_suggestions")
def trending_tech_suggestions(skill: str):
    client = Mistral(api_key=api_key_mistral)

    model = 'mistral-large-latest'
    prompt = f"Given the skills below, generate a response with related trending skills \n\n{skill}"

    completion = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an AI that provides trending tech suggestions without inlcuding any unnecessary statmenents in your response. Your responses are single-line responses, seperated by commas"  
            },
            {
                "role":"user",
                "content": prompt
            }
        ]
    )
    
    return {"skills": completion.choices[0].message.content}

# @app.post("/extract_skills/")
# def extract_skills(request: schemas.SkillExtractionRequest):
#     about_text = request.about_text.lower()
#     extracted_skills = [skill for skill in skill_keywords if skill.lower() in about_text]
    
#     doc = nlp(request.about_text)
#     for token in doc.ents:
#         if token.label_ in ["ORG", "PRODUCT"]:
#             extracted_skills.append(token.text)
    
#     return {"skills": list(set(extracted_skills))}

# API endpoint for linkedin skill extraction
@app.post("/scrape_linkedin/", response_model=schemas.ExtractionResponseModel)
def scrape_extract_linkedin():
    linkedin_url = "https://www.linkedin.com/in/aayush-kumar-6b5191263"
    user_details = utils.scrape_linkedin_profile(linkedin_url)
    return {
        "name": user_details["name"],
        "about": user_details["about"],
        "linkedin_url": user_details["linkedin_url"],
        "extracted_skills": user_details["skills"]
    }
    
# # API endpoint for quizzes  
# @app.post("/generate_quiz/")
# def quiz_run(extracted_skills: list, num_questions: int):
#     questions = utils.generate_quiz_questions(extracted_skills, num_questions)
#     if questions:
#         utils.run_quiz(questions)
#     else:
#         raise HTTPException(status_code=404, detail="Questions not found!")

@app.post("/generate_quiz/")
def generate_quiz(request: schemas.GenerateQuizRequest):
    questions = []
    questions_per_skill = max(1, request.num_questions // len(request.skills))
    
    for skill in request.skills:
        for _ in range(questions_per_skill):
            if len(questions) >= request.num_questions:
                break
            
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
                        headers={"Authorization": f"Bearer {api_key_mistral}"},
                        json={
                            "model": 'mistral-large-latest',
                            "messages": [{"role": "user", "content": prompt_text}],
                            "max_tokens": 300
                        },
                        timeout=15
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        lines = content.split("\n")

                        question, options, correct_answer, explanation = None, [], None, None
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
                                "skill": skill
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
    return {"questions": questions}

@app.post("/generate_and_run_quiz/")
def generate_and_run_quiz(request: schemas.GenerateQuizRequest):
    generated_quiz = generate_quiz(request)
    return run_quiz(schemas.QuizRequest(questions=generated_quiz["questions"]))

@app.post("/run_quiz/")
def run_quiz(request: schemas.QuizRequest):
    global mistakes_per_skill  
    score = 0
    mistakes_per_skill = {}
    
    for q in request.questions:
        user_answer = q.correct_answer  
        if user_answer == q.correct_answer:
            score += 1  
        else:
            skill = q.skill  
            mistakes_per_skill[skill] = mistakes_per_skill.get(skill, 0) + 1  
    
    result = {
        "score": score,
        "total_questions": len(request.questions),
        "mistakes_per_skill": mistakes_per_skill,
        "recommendations": [f"Revise more on {skill}" for skill in mistakes_per_skill.keys()]
    }
    
    return result





