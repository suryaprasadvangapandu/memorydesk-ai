# 🎙️ MemoryDesk AI — 60-Second Hackathon Demo Script
**HackwithHyderabad 3.0 Presentation Guide**  
*Target Duration: 60 - 75 seconds*

---

### [0:00 - 0:12] Act 1: The Problem (Hook the Judges)
> **Speaker:**  
> *"Judges, every one of us has experienced the frustration of technical support bots. You spend 10 minutes explaining your OS, your Python version, and your previous bug... and then next week when the bug happens again, the bot has complete amnesia and asks you the exact same questions all over again."*
>
> *(Action: Display the Landing Page or Before vs After Modal showing the red 'Without Memory' box).*

---

### [0:12 - 0:25] Act 2: Introducing MemoryDesk AI & Hindsight
> **Speaker:**  
> *"Meet **MemoryDesk AI** — Customer Support That Never Forgets. Powered by **Hindsight persistent memory**, our AI agent maintains isolated customer memory banks, learns from every single interaction, and recalls relevant facts before answering."*
>
> *(Action: Switch to the Dashboard at `http://localhost:8000/dashboard.html` with customer **Rahul Sharma** selected).*

---

### [0:25 - 0:42] Act 3: First Interaction (Learning & Retaining)
> **Speaker:**  
> *"In our first conversation, Rahul tells the agent:*  
> **'My name is Rahul. I use Windows 11 and Python 3.12. I am getting a Django database connection error.'**  
> *Notice what happens: The agent helps Rahul troubleshoot, but behind the scenes, Hindsight's `retain()` engine extracts his OS, his stack, and his preference into his persistent memory bank."*
>
> *(Action: Click the quick chip `1. First Interaction (Setup)` or show the chat bubble with the green badge `✓ Memory Retained in Hindsight`).*

---

### [0:42 - 0:58] Act 4: The Proof (The Recurring Issue)
> **Speaker:**  
> *"Now, days later, Rahul returns in a brand new session and simply types:*  
> **'The same database problem happened again.'**  
> *Watch the response: MemoryDesk doesn't ask who he is or what OS he runs. It immediately states:*  
> **'Hello Rahul! I remember you are on Windows 11 Pro with Python 3.12, Django 5.0, and previously resolved a PostgreSQL port 5432 connection issue. Let's check `Get-Service postgresql*` first.'**  
> *Zero repetition. Instant personalized resolution."*
>
> *(Action: Click `2. The Recall Test ("Same issue again")` and point to the prompt response and the badge `🧠 5 Hindsight memories recalled`).*

---

### [0:58 - 1:15] Act 5: The Hindsight Inspector & Conclusion
> **Speaker:**  
> *"Look at the right panel: **What MemoryDesk Remembers**.  
> Here is the live structured memory profile and our **Learning Timeline**, showing exactly how the agent acquired Rahul's identity, OS, stack, past errors, and preferences over time.  
> With Hindsight, customer support teams eliminate 40% of repetitive data gathering and deliver delightful, compound customer intelligence.  
> Thank you! We are ready for your questions."*
>
> *(Action: Point to the 'What MemoryDesk Remembers' entity card and Chronological Timeline).*

---

### 💡 Pro Tips for Presenting
- Keep the `http://localhost:8000/dashboard.html` tab open in your browser before starting.
- You can use the **⚡ Run Demo Scenario** button in the top navbar if you want the automated sequence to run with a single click.
- If judges ask about Hindsight integration, show them `backend/services/hindsight_service.py` with the official `hindsight_client.Hindsight` retain and recall calls.
