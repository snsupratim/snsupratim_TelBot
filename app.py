from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import pickle
import random
from dotenv import load_dotenv
import os
from flask import Flask  # Import Flask for the HTTP server

# Load environment variables
load_dotenv()

# Bot Token and Username
TOKEN: Final = os.getenv('TELEGRAM_BOT_TOKEN')
BOT_USERNAME: Final = os.getenv('TELEGRAM_BOT_USERNAME')

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

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

# Flask app to bind a port
app = Flask(__name__)

@app.route("/")
def home():
    return "Telegram bot is running!"

if __name__ == '__main__':
    print('Starting Bot...')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Errors
    app.add_error_handler(error)

    # Poll the bot
    print('Polling...')
    app.run_polling(poll_interval=3)

    # Start the Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
