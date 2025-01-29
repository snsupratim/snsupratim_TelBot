from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pickle
import random
from dotenv import load_dotenv
import os
from flask import Flask, render_template  # Import Flask for the HTTP server
from pymongo import MongoClient  # Import MongoClient for MongoDB

# Load environment variables
load_dotenv()

# Bot Token and Username
TOKEN: Final = os.getenv('TELEGRAM_BOT_TOKEN')
BOT_USERNAME: Final = os.getenv('TELEGRAM_BOT_USERNAME')
MONGO_URI: Final = os.getenv('MONGO_URI')  # Get MongoDB URI from environment

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['telegram_bot']  # Database name
conversations_collection = db['conversations']  # Collection name for storing conversations

# Load the saved model and vectorizer
with open('snsupratim.pkl', 'rb') as model_file:
    vectorizer, clf, intents = pickle.load(model_file)

# Function to generate a chatbot response
def chatbot(input_text):
    input_text = vectorizer.transform([input_text])
    tag = clf.predict(input_text)[0]
    for intent in intents:
        if intent['tag'] == tag:
            response = random.choice(intent['responses'])
            return response
    return "I'm not sure how to respond to that."

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm Supratim Nag.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I'm snsupratim! Ask me something.")

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Custom command..")

# Handle messages using the ML chatbot
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User({update.message.chat.id}) in {message_type}: "{text}"')

    # Store conversation in MongoDB
    conversation_data = {
        'user_id': update.message.chat.id,
        'username': update.message.from_user.username,
        'message': text,
        'timestamp': update.message.date  # Store message timestamp
    }

    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = chatbot(new_text)
        else:
            return
    else:
        response: str = chatbot(text)

    print('Bot:', response)
    await update.message.reply_text(response)
    
    # Insert into MongoDB after generating a response
    conversations_collection.insert_one(conversation_data)  # Insert into MongoDB

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

# Flask app to bind a port and provide a dashboard
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    # Fetch unique user IDs from MongoDB
    unique_users = conversations_collection.distinct('user_id')  # Get unique user IDs
    return render_template('home.html', users=unique_users)  # Pass users to the home template

@flask_app.route("/user/<int:user_id>")
def user_dashboard(user_id):
    # Fetch conversations for the specific user
    conversations = list(conversations_collection.find({'user_id': user_id}))  # Get conversations for this user
    for conversation in conversations:
        conversation['_id'] = str(conversation['_id'])  # Convert ObjectId to string for JSON serialization
    return render_template('user_dashboard.html', interactions=conversations, user_id=user_id)

@flask_app.route("/dashboard")
def dashboard():
    # Fetch conversations from MongoDB (this route can be removed if not needed)
    conversations = list(conversations_collection.find())  # Get all conversations from MongoDB
    for conversation in conversations:
        conversation['_id'] = str(conversation['_id'])  # Convert ObjectId to string for JSON serialization
    return render_template('dashboard.html', interactions=conversations)

if __name__ == '__main__':
    print('Starting Bot...')

    # Telegram Bot Setup
    telegram_app = Application.builder().token(TOKEN).build()

    # Commands and Messages Handlers Setup
    telegram_app.add_handler(CommandHandler('start', start_command))
    telegram_app.add_handler(CommandHandler('help', help_command))
    telegram_app.add_handler(CommandHandler('custom', custom_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handling setup
    telegram_app.add_error_handler(error)

    # Start Flask Server in a separate thread or process if needed
    port = int(os.getenv("PORT", 5000))  # Get PORT from environment variable
    
    print(f"Running Flask on port: {port}")

    import threading

    def run_flask():
        flask_app.run(host='0.0.0.0', port=port)  # Start Flask server

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    telegram_app.run_polling(poll_interval=3)  # Run Telegram bot polling

