## ♣️♦️**Badam Satti — Real-time Multiplayer Card Game** 🃏♥️♠️

### 📚 About

## 🍁**Badam Satti** ✨⚡:

A fast⚡, real-time ⌛ web version of the classic "Sevens" 7️⃣❤️ card game 🃏— build sequences up and down from the 7s and race 🏃‍♂️ to empty your hand ✋ first 🥇.

<hr>

### 🏓Table of Contents
- 🎬 Live Demo
- ✨ Features
- 📘 Game Rules (Quick)
- 🛠️ Tech Stack
- 🚀 Getting Started
- ✅ Prerequisites
- 📦 Installation
- 🔐 Environment Variables
- 🗄️ Database Setup
- ▶️ Run (Dev) 
- 🐳 Run with Docker

<hr>

### 🚀 Live Demo

<div align="center">
<a href="https://akshayparihardev.pythonanywhere.com/" target="_blank">
<img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQxSmMBE-TioetWiNZiUDuBCxppXz6yDJyUeQ&s" alt="PythonAnywhere App" style="width: 100%; max-width: 450px; height: auto; display: block; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: auto;">
</a>
<br>
<p><strong>Click Above 👆 to Open the Live Web App</strong></p>
</div>

<hr>

### ✨ Features

⚡ Real-time Multiplayer: Play in private or public rooms.

🔄 Connection-safe: Reconnect and keep your state.

⏱️ Turn-based Logic: Valid move checks and turn enforcement.

🚪 Room Management: Create/join rooms; seat handling.

💬 Chat: In-room messaging (if implemented).

💾 Persistent State: DB/Cache-backed state.

📱 Responsive UI: Works great on desktop and mobile.

<hr>

### Game Rules (Quick) 📘

- 🎯 Objective: Be the first to play all your cards.
- 🃏 Setup: Standard 52-card deck. 7 of Hearts (Badam Satti) starts the center.
- ▶️ Gameplay:
    - Build sequences per suit on the table.
    - From 7: go down (6,5,4,3,2,A) and up (8,9,10,J,Q,K).
    - On your turn, play an adjacent same-suit card (e.g., Hearts 6 or Hearts 8 if 7❤️ is on table).
    - If you can’t play, you pass (or draw—based on house rules).

- 🏆 Win: First to empty your hand. Optional scoring by remaining cards.

<hr>

### 🛠️ Tech Stack

- Frontend: 🧩 Django Templates - ⚡ HTMX - 🌐 Vanilla JS
- Backend: 🐍 Python - 🧩 Django - 🔗 Django Channels 
- Realtime: 🔌🧠 HTTP Polling (ASGI)
- Data: 📁🗄️ SQLdbLite3
- Deploy: 🚀 pythonAnywhere , 💥Ngrok (Local Tunneling)

<hr>

### 🚀 Getting Started 
#### - Prerequisites ✅

- 🐍 Python 3.10+
- 🧩 Django
- 🔀 Git & 🐱 GitHub
- 🔗 Ngrok (Local Tunneling)

<hr>

### 📦 Installation
Follow these steps to get the project up and running on your local machine.

1. **Clone the repo** 📥
   ```bash 
   https://github.com/akshayparihardev/BadamSatti.git
   ```
2. **Move into the project directory** 📁
   ```bash
   cd BadamSatti
   ```
3. **Install dependencies** ⚙️  
   _(It's recommended to use a virtual environment)_  
   ```bash
   pip install -r requirements.txt
   ```

<hr>

### 🔐💡 Environment Variables
#### 📂 Create a .env file in project root:
- DEBUG = true
- SECRET_KEY = change-this-to-a-strong-secret
- ALLOWED_HOSTS = localhost,127.0.0.1

### ▶️ Run (Dev)
#### Option A : 🔗 In Your Local Environment using Ngrok
1. **🏹 Make Migrations** 
```bash
python manage.py migrate
```
2. **🏃‍♂️‍➡️ Run Server**
```bash
python manage.py runserver
```
3. **⚡ Ngrok Link to open (In other terminal keeping previous one alive)**
```bash
ngrok http 8000
```

#### Option B : 🐋 Using Docker
1. **🏗️ Build your application environment (Project Blueprint🍁)**
```bash
docker-compose up --build
```
2. **🖼️ Run Database Migrations**
```bash
docker-compose exec web python manage.py migrate  
```
#### 💥 View Your Application on:
    http://localhost

<hr>

### 📄 License
⚖️ MIT License.

<hr>

### 🍁✨ Credits & Contributions

<p>
<a href="https://github.com/akshayparihardev" target="_blank" title="Akshay Parihar" style="margin-right: 15px;">
<img src="https://github.com/akshayparihardev.png" width="60" height="60" style="border-radius:50%; box-shadow:0 4px 12px rgba(0,0,0,0.15);" alt="Akshay Parihar">
</a>
<a href="https://github.com/Kartikeya-Ambare" target="_blank" title="Kartikeya Ambare" style="margin-right: 15px;">
<img src="https://github.com/Kartikeya-Ambare.png" width="60" height="60" style="border-radius:50%; box-shadow:0 4px 12px rgba(0,0,0,0.15);" alt="Kartikeya Ambare">
</a>
<a href="https://github.com/Adhishree21" target="_blank" title="Adhishree" style="margin-right: 15px;">
<img src="https://github.com/Adhishree21.png" width="60" height="60" style="border-radius:50%; box-shadow:0 4px 12px rgba(0,0,0,0.15);" alt="Adhishree">
</a>
<a href="https://github.com/Janhavi1214" target="_blank" title="Janhavi" style="margin-right: 15px;">
<img src="https://github.com/Janhavi1214" width="60" height="60" style="border-radius:50%; box-shadow:0 4px 12px rgba(0,0,0,0.15);" alt="Janhavi">
</p>
