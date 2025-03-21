from pydantic import BaseModel

class SkillExtractionRequest(BaseModel):
    about_text: str
    
class LinkedInScrapeRequest(BaseModel):
    linkedin_url: str
    
class ExtractionResponseModel(BaseModel):
    name: str
    about: str
    linkedin_url: str
    extracted_skills: list
    
class QuizQuestion(BaseModel):
    question: str
    options: list
    correct_answer: str
    explanation: str
    skill: str
    
class QuizRequest(BaseModel):
    questions: list[QuizQuestion]
    
class GenerateQuizRequest(BaseModel):
    skills: list[str]
    num_questions: int = 10