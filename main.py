from flask import Flask, request, jsonify
import openai
import smtplib
from email.message import EmailMessage
import json

app = Flask(__name__)
# Replace with your OpenAI API key
openai.api_key = ""
app.static_folder = 'static'

def convert_history_to_string(history):
    conversation = ""
    for message in history:
        conversation += message["role"] + ": " + message["content"] + "\n"
    return conversation




# Email configuration
email_sender = "gautamgxtv@gmail.com"
email_password = ""
email_receiver = "gautam@codergautam.dev"

# Questions for the assessment
questions = ["What's your name?", "Tell me about yourself.", "Why should we hire you?", "What is Python?", "What are the benefits of using Python?"]

def getProperties():
  global questions
  base = {
      "strengths": {
          "type": "string",
          "description": "This is not a question asked, it is based on you (the AI) to decide. What are 3 strengths of this candidate based on the conversation? (required)"
      },
      "weaknesses": {
          "type": "string",
          "description": "This is not a question asked, it is based on you (the AI) to decide. What are 3 weaknesses of this candidate based on the conversation? (required)"
      }
  }

  baseRequired = ["strengths", "weaknesses"]
  id=1
  for question in questions:
      stripped_question = "q"+str(id)
      id+=1;
      base[stripped_question] = {
          "type": "string",
          "description": f"Answer for the question: {question}"
      }
      baseRequired.append(stripped_question)
  
  return [base, baseRequired]
  
def transform_results(results):
    global questions
    newr = []
    print(results)
    for i, question in enumerate(questions):
        key = f"q{i+1}"
        if key in results:
            answer = results[key].strip() if results[key].strip() else 'Not Found'
        else:
            answer = 'Not Found'
        newr.append({"question": question, "answer": answer})
    resultstext = "\n".join([f"{item['question']}  Answer: {item['answer']}" for item in newr])
    return resultstext



@app.route('/set_questions', methods=['POST'])
def set_questions():
    global questions
    questions = request.json['questions']
    return jsonify({"message": "Questions updated successfully"}), 200

@app.route('/talk', methods=['POST'])
def talk():
    # Retrieve the conversation history from the request body
    conversation_history = request.get_json()
    conversation_history.insert(0, {
      "role": "system",
      "content": "You are an job assessment AI bot. Start by introducing yourself and ask questions one by one. Engage in conversation with the applicant, and ask the following questions: "+", ".join(questions)+"\n You are the AI Bot, do not simulate applicant messages. Ask questions one by one as they answer. Do not steer away from the questions, you must only ask these questions and keep moving (one response per question). Your responses are friendly (motivate them after each question), very concise and to-the-point. NEVER EVER explain the answer or comment on the users' responses, you must stay in your role as a question ASKER not answerer. When all questions are asked, call the end function immediately without saying anything."
    })

    # Check if the conversation history has the required format
    if not (isinstance(conversation_history, list) and all("role" in msg and "content" in msg for msg in conversation_history)):
        return "Invalid conversation history format", 400

    # Call GPT-4 to get the AI response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=conversation_history,
        max_tokens=200,
        temperature=0,
         functions=[
        {
          "name": "end",
          "description": "End the chat. Only do this once all answers have been received.",
          "parameters": {
                "type": "object",
                "properties": {
                  
                },
                "required": [],
            },
        }
    ],
    )
    
    # Extract the AI's message from the response
    message = (response["choices"][0]["message"])
    if "function_call" in message:
        if message["function_call"]["name"] == "end":
          print(getProperties())
          convostring = convert_history_to_string(conversation_history)
          newresponse = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
          {"role": "system", "content": "Analyze the given conversation history and try to find answers to the following questions: "+", ".join(questions)+"\n. Also find 3 strengths and weaknesses of this applicant. If the question is not found, say 'Not Found'. You must only put an answer if it is found. ONLY use the user's responses to find this."},
          {"role": "user", "content": convostring}
        ],
        max_tokens=500,
        temperature=0,
         functions=[
        {
          "name": "submit",
          "description": "Submit the found answers, weaknesses, and strengths of this candidate. There must be at least 3 strengths and weaknesses formatted as a string with newlines.",
          "parameters": {
                "type": "object",
                "properties": getProperties()[0],
                "required": getProperties()[1],
            },
        }
    ],
            function_call={"name": "submit"}
    )
          conversation_history.append({
            "role": "assistant",
            "content": "Thank you. Your answers have been recorded.",
          
          })
          newresults = json.loads(newresponse["choices"][0]["message"]["function_call"]["arguments"]),
          conversation_history.append({
            "results":newresults[0],
            "questions": questions,
          })
          print(transform_results(newresults[0]))
          send_email(transform_results(newresults[0]))
          return jsonify(conversation_history)
          
          
        
    ai_message = response["choices"][0]["message"]["content"]

  

    # Append the AI's message to the conversation history
    conversation_history.append({"role": "assistant", "content": ai_message})

    # Return the updated conversation history as JSON
    return jsonify(conversation_history)


@app.route('/get_questions', methods=['GET'])
def get_questions():
    return jsonify({"questions": questions})



def send_email(data):
    msg = EmailMessage()
    msg.set_content(f"Assessment completed. Score: {data}")

    msg["Subject"] = "Assessment Results"
    msg["From"] = email_sender
    msg["To"] = email_receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_sender, email_password)
        server.send_message(msg)

    print("Email sent successfully")

# send file admin.html when going to /admin
@app.route('/admin')
def admin():
  return app.send_static_file('admin.html')

@app.route('/')
def index():
  return app.send_static_file('index.html')


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')