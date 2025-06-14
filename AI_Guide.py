import streamlit as st
import google.generativeai as genai
import PyPDF2
import speech_recognition as sr
import pyttsx3
import time
import threading
import pandas as pd
import base64
import requests

# Set up Google Generative AI API
API_KEY = "AIzaSyAdyhngHuKeKVEnRotnlY_unC1iFJgX344"
genai.configure(api_key=API_KEY)

# Use the latest Gemini model
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Initialize text-to-speech engine
engine = None
speech_in_progress = False
speech_lock = threading.Lock()

# Function to add a light background image and ensure text visibility
def add_bg_from_url():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("https://images.unsplash.com/photo-1551434678-e076c223a692");
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
            background-color: rgba(255, 255, 255, 0.7);
            background-blend-mode: lighten;
        }}
        .stApp > header {{
            background-color: rgba(0,0,0,0);
        }}
        .main .block-container {{
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            margin: 1.5rem;
        }}
        h1, h2, h3 {{
            color: #1E3A8A;
            font-weight: 700;
            text-shadow: 1px 1px 3px rgba(255, 255, 255, 0.8);
        }}
        p, label, .stMarkdown {{
            color: #333333;
            font-weight: 600;
        }}
        .stSidebar .block-container {{
            background-color: rgba(255, 255, 255, 0.95);
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            border-radius: 12px;
        }}
        .st-emotion-cache-16txtl3 {{
            padding: 1.5rem;
        }}
        .stButton > button {{
            font-weight: 600;
            border: 2px solid #1E3A8A;
            background-color: #E8F0FE;
            color: #1E3A8A;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }}
        .stButton > button:hover {{
            background-color: #1E3A8A;
            color: white;
            border-color: #1E3A8A;
        }}
        .dataframe {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .st-bk {{
            font-weight: 600;
            color: #333333;
        }}
        .section-card {{
            background-color: rgba(255, 255, 255, 0.98);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def initialize_engine():
    global engine
    try:
        if engine is None:
            engine = pyttsx3.init()
    except Exception as e:
        print(f"Failed to initialize text-to-speech: {str(e)}")

def speak(text):
    global engine, speech_in_progress
    stop_speech()
    try:
        initialize_engine()
        if engine is not None:
            def speak_text():
                global speech_in_progress
                with speech_lock:
                    speech_in_progress = True
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"Text-to-speech error: {str(e)}")
                finally:
                    with speech_lock:
                        speech_in_progress = False
            threading.Thread(target=speak_text).start()
            return True
    except Exception as e:
        print(f"Text-to-speech error: {str(e)}")
        with speech_lock:
            speech_in_progress = False
    return False

def stop_speech():
    global engine, speech_in_progress
    try:
        if engine is not None and speech_in_progress:
            engine.stop()
    except Exception as e:
        print(f"Error stopping speech: {str(e)}")
    finally:
        with speech_lock:
            speech_in_progress = False

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            st.write(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            st.error("Sorry, I could not understand what you said.")
            return None
        except sr.RequestError:
            st.error("Sorry, there was an issue with the speech recognition service.")
            return None

def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_career_guidance(user_input):
    prompt = f"Provide career guidance based on the following user input: {user_input}. Suggest suitable career paths, skills to learn, and industries to explore."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating career guidance: {str(e)}"

def analyze_resume(resume_text):
    prompt = f"Analyze the following resume and provide feedback on structure, missing skills, and suggestions for improvement. Also, assign a rating from 1 to 10 based on the overall quality of the resume:\n{resume_text}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error analyzing resume: {str(e)}"

def get_learning_path(skills):
    prompt = f"Suggest a personalized learning path to acquire the following skills: {skills}. Include courses, certifications, and platforms like Coursera, Udemy, and LinkedIn Learning."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating learning path: {str(e)}"

# Function to get best YouTube channels based on user skills
def get_best_youtube_channels(skills):
    prompt = f"""Based on the following skills: {skills}, recommend 5 of the best YouTube channels for free learning resources. For each channel, provide:
    1. The channel name
    2. A clickable YouTube channel link (e.g., https://www.youtube.com/@channelname)
    3. A brief description of what the channel offers related to the skills
    Format the response as a list with each channel on a new line, using this structure:
    - **Channel Name**: [Link](URL) - Description"""
    try:
        response = model.generate_content(prompt)
        channels_text = response.text.strip()
        # Parse the response into a list of dictionaries
        channels = []
        for line in channels_text.split('\n'):
            if line.strip().startswith('- **'):
                try:
                    name_part = line.split('**: ')[1].split(' - ')[0]
                    name = name_part.split(']')[0].strip('[')
                    url = name_part.split('(')[1].strip(')')
                    description = line.split(' - ')[1]
                    channels.append({
                        "name": name,
                        "link": url,
                        "description": description
                    })
                except IndexError:
                    continue  # Skip malformed lines
        return channels
    except Exception as e:
        return f"Error fetching YouTube channels: {str(e)}"

def get_job_market_insights():
    try:
        prompt = """Generate current job market insights including:
        1. Top 5 trending roles in the tech industry
        2. Top 5 emerging skills that are in high demand
        3. Salary trends for at least 5 popular tech roles
        Present the information in a structured format with clear section headings and detailed explanations."""
        response = model.generate_content(prompt)
        return {"ai_generated": True, "insights": response.text}
    except Exception as e:
        print(f"Error generating job market insights: {str(e)}")
        return {
            "ai_generated": False,
            "trending_roles": [
                {"role": "Data Scientist", "growth": "28%", "description": "Analyzing complex data to help businesses make decisions"},
                {"role": "AI Engineer", "growth": "32%", "description": "Developing AI systems and machine learning models"},
                {"role": "Cloud Architect", "growth": "25%", "description": "Designing and implementing cloud infrastructure"},
                {"role": "DevOps Engineer", "growth": "22%", "description": "Bridging development and operations"},
                {"role": "Cybersecurity Specialist", "growth": "30%", "description": "Protecting systems from cyber threats"}
            ],
            "emerging_skills": [
                {"skill": "Generative AI", "demand": "Very High", "adoption": "Growing rapidly across industries"},
                {"skill": "DevOps", "demand": "High", "adoption": "Standard in modern development environments"},
                {"skill": "Cybersecurity", "demand": "Very High", "adoption": "Critical for all organizations"},
                {"skill": "Cloud Computing", "demand": "High", "adoption": "Widespread across all sectors"},
                {"skill": "Data Analytics", "demand": "High", "adoption": "Essential for data-driven decision making"}
            ],
            "salary_trends": [
                {"role": "Data Scientist", "entry_level": "$90,000", "mid_level": "$120,000", "senior_level": "$150,000+"},
                {"role": "AI Engineer", "entry_level": "$95,000", "mid_level": "$130,000", "senior_level": "$165,000+"},
                {"role": "Cloud Architect", "entry_level": "$100,000", "mid_level": "$135,000", "senior_level": "$170,000+"},
                {"role": "DevOps Engineer", "entry_level": "$85,000", "mid_level": "$115,000", "senior_level": "$145,000+"},
                {"role": "Cybersecurity Specialist", "entry_level": "$90,000", "mid_level": "$125,000", "senior_level": "$160,000+"}
            ]
        }

def get_networking_suggestions(industry):
    prompt = f"Suggest professional networking strategies and mentors for someone interested in {industry}. Include LinkedIn tips and networking events."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating networking suggestions: {str(e)}"

def generate_interview_questions(job_role, num_questions, interview_style="Mixed", difficulty="Medium"):
    prompt = f"""Generate {num_questions} unique and role-specific interview questions for a {job_role} position. 
    The interview style should be {interview_style} and the difficulty level should be {difficulty}.
    Include a mix of behavioral, technical, and situation-based questions relevant to this role.
    Format each question clearly, one per line, with no numbering or prefixes."""
    try:
        response = model.generate_content(prompt)
        questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
        if len(questions) > num_questions:
            questions = questions[:num_questions]
        elif len(questions) < num_questions:
            general_questions = [
                "Tell me about yourself.",
                "What are your strengths and weaknesses?",
                "Why do you want this job?",
                "Where do you see yourself in 5 years?",
                "How do you handle pressure or stressful situations?",
                "What is your greatest professional achievement?"
            ]
            needed = num_questions - len(questions)
            questions.extend(general_questions[:needed])
        return questions
    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return get_default_questions(num_questions)

def get_default_questions(num_questions):
    default_questions = [
        "Tell me about yourself.",
        "What are your strengths and weaknesses?",
        "Why do you want this job?",
        "Describe a challenging situation you faced at work and how you handled it.",
        "Where do you see yourself in 5 years?",
        "How do you handle pressure or stressful situations?",
        "What is your greatest professional achievement?",
        "How do you prioritize your work?",
        "What are your salary expectations?",
        "Do you have any questions for us?"
    ]
    return default_questions[:num_questions]

if "page" not in st.session_state:
    st.session_state.page = "main"
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "responses" not in st.session_state:
    st.session_state.responses = []
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "recorded_answer" not in st.session_state:
    st.session_state.recorded_answer = ""
if "job_role" not in st.session_state:
    st.session_state.job_role = ""
if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = ""
if "last_question_read" not in st.session_state:
    st.session_state.last_question_read = -1

def start_new_interview(job_role, num_questions, interview_style="Mixed", difficulty="Medium"):
    with st.spinner("Generating interview questions for your role..."):
        questions = generate_interview_questions(job_role, num_questions, interview_style, difficulty)
    st.session_state.page = "interview"
    st.session_state.interview_started = True
    st.session_state.questions = questions
    st.session_state.current_question_index = 0
    st.session_state.responses = []
    st.session_state.job_role = job_role
    st.session_state.start_time = time.time()
    st.session_state.recorded_answer = ""
    st.session_state.evaluation_result = ""
    st.session_state.last_question_read = -1

def evaluate_interview():
    job_role = st.session_state.job_role
    questions = st.session_state.questions
    responses = st.session_state.responses
    evaluation_prompt = f"""Evaluate the following interview responses for the role of {job_role} and provide detailed feedback:

Interview Questions and Responses:
"""
    for q, r in zip(questions, responses):
        evaluation_prompt += f"Question: {q}\nResponse: {r}\n\n"
    evaluation_prompt += """
Please provide:
1. A detailed assessment of strengths demonstrated in the responses
2. Specific areas for improvement with actionable advice
3. Overall impression and how well the candidate's responses align with the role requirements
4. A final score out of 10 with reasoning for the score
5. 2-3 follow-up questions you would ask this candidate in a real interview
"""
    try:
        evaluation = model.generate_content(evaluation_prompt)
        st.session_state.evaluation_result = evaluation.text
    except Exception as e:
        st.session_state.evaluation_result = f"Error evaluating interview: {str(e)}"

def next_question(response=None):
    stop_speech()
    if response is not None:
        st.session_state.responses.append(response)
    st.session_state.current_question_index += 1
    st.session_state.start_time = time.time()
    st.session_state.recorded_answer = ""
    if st.session_state.current_question_index >= len(st.session_state.questions):
        st.session_state.page = "evaluation"

add_bg_from_url()

st.title("AI Career Counselor and Resume Analyzer")
st.write("Welcome to your AI-powered career guidance system!")

st.sidebar.markdown("""
<div style="text-align: center;">
    <h2>Navigation</h2>
</div>
""", unsafe_allow_html=True)

options = [
    "Career Guidance", "Resume Analysis", "Learning Path Recommendations",
    "Mock Interview", "Job Market Insights", "Networking Suggestions"
]
option = st.sidebar.radio("Choose an option:", options)

if option == "Career Guidance":
    st.header("AI Career Guidance Chatbot")
    user_input = st.text_area("Tell us about your skills, interests, and career goals:")
    if st.button("Get Career Guidance"):
        if user_input:
            with st.spinner("Generating career guidance..."):
                guidance = get_career_guidance(user_input)
                st.success("Here's your personalized career guidance:")
                st.write(guidance)
        else:
            st.warning("Please provide some input about your skills and interests.")

elif option == "Resume Analysis":
    st.header("AI Resume Analyzer")
    uploaded_file = st.file_uploader("Upload your resume (PDF only):", type="pdf")
    if uploaded_file:
        st.write("Resume uploaded successfully!")
        resume_text = extract_text_from_pdf(uploaded_file)
        if st.button("Analyze Resume"):
            with st.spinner("Analyzing your resume..."):
                analysis = analyze_resume(resume_text)
                st.success("Here's your resume analysis:")
                st.write(analysis)

elif option == "Learning Path Recommendations":
    st.header("Personalized Learning Path")
    skills = st.text_area("Enter the skills you want to learn or improve (separate multiple skills with commas):")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get Learning Path"):
            if skills:
                with st.spinner("Generating learning path..."):
                    learning_path = get_learning_path(skills)
                    st.success("Here's your personalized learning path:")
                    st.write(learning_path)
            else:
                st.warning("Please enter the skills you want to learn.")
    with col2:
        if st.button("Get Free Learning Resources"):
            if skills:
                with st.spinner("Fetching free learning resources..."):
                    channels = get_best_youtube_channels(skills)
                    if isinstance(channels, str):  # Error case
                        st.error(channels)
                    else:
                        st.success(f"Here are the best YouTube channels for learning {skills}:")
                        for channel in channels:
                            st.markdown(
                                f"""
                                <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                                    <div>
                                        <a href="{channel['link']}" target="_blank" style="font-size: 1.1rem; color: #1E3A8A; text-decoration: none;">{channel['name']}</a>
                                        <p style="font-size: 0.9rem; color: #666;">{channel['description']}</p>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
            else:
                st.warning("Please enter the skills you want to learn.")

elif option == "Mock Interview":
    st.header("AI-Powered Mock Interview")
    if st.session_state.page == "main":
        job_role = st.text_input("Enter the job role you're preparing for:")
        num_questions = st.slider("Select the number of questions for the interview:", min_value=1, max_value=10, value=5)
        interview_style = st.selectbox("Select interview style:", ["Standard", "Behavioral", "Technical", "Situation-based (STAR)", "Mixed"])
        difficulty = st.select_slider("Select difficulty level:", options=["Easy", "Medium", "Hard", "Expert"])
        if job_role:
            if st.button("Start Mock Interview"):
                with st.spinner("Preparing your personalized interview questions..."):
                    start_new_interview(job_role, num_questions, interview_style, difficulty)
                st.rerun()
        else:
            st.warning("Please enter the job role you're preparing for.")
    elif st.session_state.page == "interview":
        current_idx = st.session_state.current_question_index
        if current_idx < len(st.session_state.questions):
            current_question = st.session_state.questions[current_idx]
            st.subheader(f"Question {current_idx + 1} of {len(st.session_state.questions)}")
            st.markdown(f"""
            <div style="background-color: #f0f7ff; padding: 15px; border-radius: 5px; border-left: 5px solid #1E88E5;">
                <p style="font-size: 16px;">{current_question}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.last_question_read < current_idx:
                if speak(current_question):
                    st.session_state.last_question_read = current_idx
                else:
                    print("Failed to read question aloud")
                    st.session_state.last_question_read = current_idx
            elapsed_time = time.time() - st.session_state.start_time
            remaining_time = max(60 - int(elapsed_time), 0)
            st.progress(remaining_time / 60)
            st.markdown(f"""
            <div style="text-align: center;">
                <p>Time remaining: <b>{remaining_time}</b> seconds</p>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.recorded_answer:
                st.markdown("""
                <div style="background-color: #f0fff0; padding: 10px; border-radius: 5px; border-left: 5px solid #4CAF50;">
                    <h4>Your answer:</h4>
                """, unsafe_allow_html=True)
                st.write(st.session_state.recorded_answer)
                st.markdown("</div>", unsafe_allow_html=True)
                if st.button("Continue to Next Question"):
                    next_question(st.session_state.recorded_answer)
                    st.rerun()
            else:
                text_answer = st.text_area("Type your answer here (or use voice recording below):", height=100)
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Submit Answer"):
                        if text_answer.strip():
                            st.session_state.recorded_answer = text_answer
                            st.rerun()
                        else:
                            st.error("Please type an answer before submitting.")
                with col2:
                    if st.button("Record Voice Answer"):
                        stop_speech()
                        answer = listen()
                        if answer:
                            st.session_state.recorded_answer = answer
                            st.rerun()
                        else:
                            st.error("No answer detected. Please try again.")
                with col3:
                    if st.button("Skip Question"):
                        next_question("(Skipped)")
                        st.rerun()
            if remaining_time <= 0 and not st.session_state.recorded_answer:
                st.warning("Time's up! Moving to the next question.")
                next_question("(Time expired)")
                st.rerun()
        else:
            st.session_state.page = "evaluation"
            st.rerun()
    elif st.session_state.page == "evaluation":
        st.success("Mock interview completed!")
        st.subheader("Your Responses:")
        for i, (q, r) in enumerate(zip(st.session_state.questions, st.session_state.responses)):
            st.markdown(f"""
            <div style="margin-bottom: 15px;">
                <div style="background-color: #f0f7ff; padding: 10px; border-radius: 5px; border-left: 5px solid #1E88E5;">
                    <p><b>Q{i + 1}:</b> {q}</p>
                </div>
                <div style="background-color: #f0fff0; padding: 10px; border-radius: 5px; border-left: 5px solid #4CAF50; margin-top: 5px;">
                    <p><b>A:</b> {r}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        if not st.session_state.evaluation_result:
            with st.spinner("Evaluating your interview performance..."):
                evaluate_interview()
                st.rerun()
        else:
            st.subheader("Interview Evaluation")
            st.markdown(f"""
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; border: 1px solid #ddd;">
                {st.session_state.evaluation_result}
            </div>
            """, unsafe_allow_html=True)
            if st.button("Download Evaluation Report"):
                st.info("This feature is coming soon! You'll be able to download your evaluation as a PDF.")
        if st.button("Start New Interview"):
            stop_speech()
            st.session_state.page = "main"
            st.session_state.interview_started = False
            st.rerun()

elif option == "Job Market Insights":
    st.header("Real-Time Job Market Insights")
    st.subheader("Filter Options")
    col1, col2 = st.columns(2)
    with col1:
        industry = st.selectbox("Industry", ["All Industries", "Technology", "Healthcare", "Finance", "Education", "Manufacturing"])
    with col2:
        region = st.selectbox("Region", ["Global", "North America", "Europe", "Asia", "Australia", "South America"])
    if st.button("Get Insights"):
        with st.spinner("Fetching current job market insights..."):
            insights = get_job_market_insights()
            if insights.get("ai_generated", False):
                st.success("Here are the latest job market insights:")
                st.markdown(insights["insights"])
            else:
                st.success(f"Job Market Insights for {industry} ({region})")
                st.subheader("🔥 Trending Roles")
                roles_df = pd.DataFrame(insights["trending_roles"])
                st.dataframe(roles_df, hide_index=True)
                st.write("#### Top In-Demand Positions:")
                cols = st.columns(len(insights["trending_roles"]))
                for i, role in enumerate(insights["trending_roles"]):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                            <h5>{role['role']}</h5>
                            <p>Growth: {role['growth']}</p>
                            <p><small>{role['description']}</small></p>
                        </div>
                        """, unsafe_allow_html=True)
                st.subheader("⚡ Emerging Skills")
                skills_df = pd.DataFrame(insights["emerging_skills"])
                st.dataframe(skills_df, hide_index=True)
                st.subheader("💰 Salary Trends")
                salary_df = pd.DataFrame(insights["salary_trends"])
                st.dataframe(salary_df, hide_index=True)
                st.write("#### Salary Comparison by Experience Level:")
                chart_data = {
                    "Role": [],
                    "Salary": [],
                    "Experience": []
                }
                for role in insights["salary_trends"]:
                    chart_data["Role"].append(role["role"])
                    chart_data["Salary"].append(int(role["entry_level"].replace("$", "").replace(",", "").replace("+", "")))
                    chart_data["Experience"].append("Entry Level")
                    chart_data["Role"].append(role["role"])
                    chart_data["Salary"].append(int(role["mid_level"].replace("$", "").replace(",", "").replace("+", "")))
                    chart_data["Experience"].append("Mid Level")
                    chart_data["Role"].append(role["role"])
                    chart_data["Salary"].append(int(role["senior_level"].replace("$", "").replace(",", "").replace("+", "")))
                    chart_data["Experience"].append("Senior Level")
                chart_df = pd.DataFrame(chart_data)
                st.bar_chart(chart_df, x="Role", y="Salary", color="Experience")
                st.subheader("📊 Market Analysis")
                st.write("""
                Based on the current job market trends:
                - Demand for AI and machine learning specialists continues to grow rapidly across industries
                - Cybersecurity skills are becoming essential in all technology roles
                - Remote work opportunities have increased salary competitiveness globally
                - Companies are prioritizing candidates with both technical and soft skills
                - Continuous learning and adaptation to new technologies remain crucial for career growth
                """)

elif option == "Networking Suggestions":
    st.header("Professional Networking Suggestions")
    industry = st.text_input("Enter your industry or field of interest:")
    col1, col2 = st.columns(2)
    with col1:
        career_stage = st.selectbox("Career Stage", ["Entry Level", "Mid-Career", "Senior Professional", "Executive"])
    with col2:
        networking_goal = st.selectbox("Networking Goal", ["Job Search", "Career Advancement", "Industry Insights", "Mentorship", "General"])
    if st.button("Get Networking Suggestions"):
        if industry:
            with st.spinner("Generating networking suggestions..."):
                suggestions = get_networking_suggestions(industry)
                st.success(f"Here are your networking suggestions for {industry}:")
                st.write(suggestions)
        else:
            st.warning("Please enter your industry or field of interest.")
