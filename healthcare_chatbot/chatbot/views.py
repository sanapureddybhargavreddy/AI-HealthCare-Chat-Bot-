from django.shortcuts import render
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import PyPDF2
from docx import Document
import os

# Configure the Google Generative AI SDK
genai.configure(api_key="AIzaSyBwPtP1tbPkh6WBx6R4f0oli9uuQw5B9QE")

# Initialize the Gemini model with healthcare-specific instructions
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="You are a healthcare assistant chatbot. Provide accurate, helpful responses to health-related questions. Always include a disclaimer: 'This is not medical advice. Consult a doctor for professional guidance.' For medical reports, summarize the key findings in a concise manner."
)

def get_healthcare_suggestion(user_input):
    """Optional rule-based suggestion to complement AI responses."""
    user_input = user_input.lower()
    if "fever" in user_input:
        return "You might have a fever. Rest and stay hydrated."
    elif "headache" in user_input:
        return "A headache could be due to stress or dehydration."
    return None

@csrf_exempt
def chatbot_home(request):
    """Render the chatbot interface and initialize session."""
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
    return render(request, 'chat.html', {'chat_history': request.session['chat_history']})

@csrf_exempt
def get_response(request):
    """Handle user input and return AI-generated response using Gemini."""
    if request.method == 'POST':
        try:
            # Get user input
            user_input = request.POST.get('message', '').strip()
            if not user_input:
                return JsonResponse({'reply': 'Please enter a message.', 'error': True})

            # Optional: Add rule-based suggestion
            suggestion = get_healthcare_suggestion(user_input)

            # Generate response using Google Gemini API
            response = model.generate_content(
                user_input,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,  # Limit response length
                    temperature=0.7,        # Control creativity
                )
            )
            ai_reply = response.text.strip()

            # Combine suggestion (if any) with AI response
            if suggestion:
                ai_reply = f"{suggestion} {ai_reply}"

            # Update session chat history
            chat_history = request.session.get('chat_history', [])
            chat_history.append({'user': user_input, 'bot': ai_reply})
            request.session['chat_history'] = chat_history[-10:]  # Keep last 10 messages
            request.session.modified = True

            return JsonResponse({'reply': ai_reply, 'error': False})
        except genai.types.GenerationError as e:
            return JsonResponse({'reply': f"Error generating response: {str(e)}", 'error': True})
        except Exception as e:
            return JsonResponse({'reply': f"An unexpected error occurred: {str(e)}", 'error': True})
    return JsonResponse({'reply': 'Invalid request method.', 'error': True})

@csrf_exempt
def clear_history(request):
    """Clear chat history from session."""
    if 'chat_history' in request.session:
        del request.session['chat_history']
    return JsonResponse({'status': 'History cleared'})

@csrf_exempt
def upload_file(request):
    """Handle file upload and summarize medical reports."""
    if request.method == 'POST':
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'reply': 'No file uploaded.', 'error': True})

            file = request.FILES['file']
            file_extension = os.path.splitext(file.name)[1].lower()

            # Read the file content based on its type
            content = ""
            if file_extension == '.pdf':
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            elif file_extension in ['.doc', '.docx']:
                doc = Document(file)
                for para in doc.paragraphs:
                    content += para.text + "\n"
            elif file_extension == '.txt':
                content = file.read().decode('utf-8')
            else:
                return JsonResponse({'reply': 'Unsupported file format. Please upload a PDF, Word, or text file.', 'error': True})

            if not content.strip():
                return JsonResponse({'reply': 'The uploaded file is empty.', 'error': True})

            # Summarize the content using Gemini API
            prompt = f"Summarize the following medical report:\n\n{content}"
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=200,  # Limit summary length
                    temperature=0.5,        # Less creativity for summaries
                )
            )
            summary = response.text.strip()

            # Update chat history
            chat_history = request.session.get('chat_history', [])
            chat_history.append({'user': f"Uploaded file: {file.name}", 'bot': summary})
            request.session['chat_history'] = chat_history[-10:]  # Keep last 10 messages
            request.session.modified = True

            return JsonResponse({'summary': summary, 'error': False})
        except Exception as e:
            return JsonResponse({'reply': f"Error processing file: {str(e)}", 'error': True})
    return JsonResponse({'reply': 'Invalid request method.', 'error': True})